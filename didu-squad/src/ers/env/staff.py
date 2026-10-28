"""Hospital status board: beds, doctors, nurses, capability, and the regional staff pool.

Effective admission capacity = min(free beds, doctor spare, nurse spare), checked per patient.
"""
from __future__ import annotations

from ers.config import assumptions, hospitals_cfg
from ers.env.entities import Color, Hospital, Patient, Staff

YELLOW_DOCTOR_SKILLS = {"emergency", "trauma", "pediatric", "burn", "cardiology"}


class HospitalBoard:
    def __init__(self, overrides: dict | None = None):
        cfg = hospitals_cfg()
        a = assumptions()
        self.ids: list[str] = list(cfg["hospitals"].keys())
        self.capability: dict[str, list[int]] = cfg["capability"]
        self.red_skills: dict[str, list[str]] = cfg["red_doctor_skills"]
        self.doctor_load: dict[str, float] = a["staff_load"]["doctor"]
        self.nurse_load: dict[str, float] = a["staff_load"]["nurse"]
        self.pool_delay: int = a["staff_load"]["pool_arrival_delay_min"]
        overrides = overrides or {}

        self.hospitals: dict[str, Hospital] = {}
        self.staff: list[Staff] = []
        for hid, h in cfg["hospitals"].items():
            o = overrides.get(hid, {})
            self.hospitals[hid] = Hospital(hid, h["name"], tuple(h["location"]), o.get("er_beds", h["er_beds"]),
                                           beds_used=o.get("beds_used", 0), diversion=o.get("diversion", False))
            doctors = o.get("doctors", h["doctors"])
            for d in doctors:
                for _ in range(d["n"]):
                    self.staff.append(Staff(f"{hid}-D{self._count(hid, 'doctor') + 1}", "doctor", d["skill"], hid))
            for _ in range(o.get("nurses", h["nurses"])):
                self.staff.append(Staff(f"{hid}-N{self._count(hid, 'nurse') + 1}", "nurse", "nurse", hid))
            # pre-existing load from patients already in the ER before the scenario starts
            for s in self.staff:
                if s.hospital_id == hid:
                    s.load = o.get(f"{s.role}_load", 0.0)
        pool = cfg["staff_pool"]
        for d in pool["doctors"]:
            for i in range(d["n"]):
                self.staff.append(Staff(f"POOL-D{i + 1}", "doctor", d["skill"], None))
        for i in range(pool["nurses"]):
            self.staff.append(Staff(f"POOL-N{i + 1}", "nurse", "nurse", None))

    # ---------- queries ----------
    def _count(self, hid: str, role: str) -> int:
        return sum(1 for s in self.staff if s.hospital_id == hid and s.role == role)

    def members(self, hid: str | None, role: str) -> list[Staff]:
        return [s for s in self.staff if s.hospital_id == hid and s.role == role]

    def level(self, hid: str, category: str) -> int:
        return self.capability[category][self.ids.index(hid)]

    def nurse_spare(self, hid: str, t: int) -> float:
        return sum(s.spare(t) for s in self.members(hid, "nurse"))

    def _doctor_for(self, hid: str, p: Patient, color: Color, t: int) -> Staff | None:
        need = self.doctor_load[color.value]
        if need == 0:
            return None
        skills = set(self.red_skills[p.category]) if color == Color.RED else YELLOW_DOCTOR_SKILLS
        best = None
        for s in self.members(hid, "doctor"):
            if s.skill in skills and s.spare(t) >= need - 1e-9 and (best is None or s.spare(t) > best.spare(t)):
                best = s
        return best

    def can_admit(self, hid: str, p: Patient, color: Color, t: int) -> tuple[bool, str]:
        h = self.hospitals[hid]
        if self.level(hid, p.category) == 0:
            return False, "CAPABILITY_MISSING"
        if h.diversion:
            return False, "DIVERSION"
        if color in (Color.RED, Color.YELLOW) and h.beds_free <= 0:
            return False, "NO_BED"
        if self.doctor_load[color.value] > 0 and self._doctor_for(hid, p, color, t) is None:
            return False, "NO_STAFF"
        if self.nurse_spare(hid, t) < self.nurse_load[color.value] - 1e-9:
            return False, "NO_STAFF"
        return True, "OK"

    def intake_limits(self, hid: str, t: int) -> dict[str, int]:
        """How many more patients of each colour the hospital could take (each colour considered alone)."""
        h = self.hospitals[hid]
        docs = self.members(hid, "doctor")
        nurse = self.nurse_spare(hid, t)
        red_docs = sum(int(s.spare(t) // self.doctor_load["red"]) for s in docs if s.skill != "nurse")
        yellow_docs = sum(int(s.spare(t) / self.doctor_load["yellow"] + 1e-9) for s in docs
                          if s.skill in YELLOW_DOCTOR_SKILLS)
        return {
            "red": max(0, min(h.beds_free, red_docs, int(nurse / self.nurse_load["red"] + 1e-9))),
            "yellow": max(0, min(h.beds_free, yellow_docs, int(nurse / self.nurse_load["yellow"] + 1e-9))),
            "green": max(0, int(nurse / self.nurse_load["green"] + 1e-9)),
        }

    def pool_available(self, role: str) -> list[Staff]:
        return self.members(None, role)

    # ---------- mutations (called only by the CAD) ----------
    def admit(self, hid: str, p: Patient, color: Color, t: int) -> None:
        h = self.hospitals[hid]
        if color in (Color.RED, Color.YELLOW):
            h.beds_used += 1
        doc = self._doctor_for(hid, p, color, t)
        if doc is not None:
            doc.load += self.doctor_load[color.value]
            p.held_doctor_id = doc.id
        self._add_nurse_load(hid, self.nurse_load[color.value], t)
        h.patient_ids.append(p.id)

    def release(self, hid: str, p: Patient, color: Color) -> None:
        h = self.hospitals[hid]
        if color in (Color.RED, Color.YELLOW):
            h.beds_used -= 1
        if p.held_doctor_id:
            doc = next(s for s in self.staff if s.id == p.held_doctor_id)
            doc.load = max(0.0, doc.load - self.doctor_load[color.value])
            p.held_doctor_id = None
        self._add_nurse_load(hid, -self.nurse_load[color.value], 0)

    def _add_nurse_load(self, hid: str, amount: float, t: int) -> None:
        """Spread nurse load over on-duty nurses (most spare first when adding, most loaded first when freeing)."""
        nurses = self.members(hid, "nurse")
        if amount > 0:
            for s in sorted(nurses, key=lambda s: -s.spare(t)):
                take = min(amount, max(0.0, s.spare(t)))
                s.load += take
                amount -= take
                if amount <= 1e-9:
                    return
        else:
            amount = -amount
            for s in sorted(nurses, key=lambda s: -s.load):
                give = min(amount, s.load)
                s.load -= give
                amount -= give
                if amount <= 1e-9:
                    return

    def assign_pool(self, staff_id: str, hid: str, t: int) -> None:
        s = next(s for s in self.staff if s.id == staff_id)
        s.hospital_id = hid
        s.on_duty_from = t + self.pool_delay
