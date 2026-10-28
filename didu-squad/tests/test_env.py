import hashlib
import json

import numpy as np
import pytest

from ers.env.actions import AssignUnits, CommitTransport
from ers.env.entities import Ambulance, Color, Incident, Patient, PatientStatus, RescueTeam, Vitals
from ers.env.geo import Geo
from ers.env.simulator import Scenario, Simulation
from ers.env.staff import HospitalBoard
from ers.env.triage import start_triage, vitals_for
from ers.eval.metrics import compute_metrics
from ers.policies.b0_nearest import NearestPolicy
from ers.policies.b1_rules import RulePolicy


# ---------------- triage ----------------
@pytest.mark.parametrize("color", [Color.RED, Color.YELLOW, Color.GREEN, Color.BLACK])
def test_vitals_round_trip(color):
    rng = np.random.default_rng(0)
    for _ in range(50):
        assert start_triage(vitals_for(color, rng)) == color


# ---------------- geo ----------------
def test_travel_times_match_hospital_profile():
    g = Geo()
    downtown = (12.0, 15.0)
    assert 15 <= g.travel_time(downtown, (26.0, 13.0)) <= 20   # H1 ~16-20 min over the bridge
    assert 9 <= g.travel_time(downtown, (6.0, 19.0)) <= 12     # H2 ~10-12 min
    assert 5 <= g.travel_time(downtown, (15.0, 13.0)) <= 7     # H3 ~6 min


def test_rush_hour_is_slower_and_bridge_closure_blocks():
    a, b = (12.0, 15.0), (26.0, 13.0)
    assert Geo("rush").travel_time(a, b) > Geo().travel_time(a, b)
    assert Geo(bridge_closed=True).travel_time(a, b) >= 10**6


# ---------------- hospital board ----------------
def _patient(pid, color, category="adult_trauma", age=40):
    rng = np.random.default_rng(1)
    p = Patient(pid, "I1", age, category, vitals_for(color, rng), False, color)
    p.true_color = color
    return p


def test_capability_and_staff_limits():
    board = HospitalBoard()
    red = _patient("P1", Color.RED)
    assert board.can_admit("H2", red, Color.RED, 0) == (False, "CAPABILITY_MISSING")
    # H1 has 2 trauma surgeons + 2 emergency physicians -> four adult-trauma reds, the fifth is refused for staff
    for i in range(4):
        p = _patient(f"R{i}", Color.RED)
        assert board.can_admit("H1", p, Color.RED, 0)[0]
        board.admit("H1", p, Color.RED, 0)
    assert board.can_admit("H1", _patient("R9", Color.RED), Color.RED, 0) == (False, "NO_STAFF")


def test_release_restores_capacity():
    board = HospitalBoard()
    before = board.intake_limits("H3", 0)
    p = _patient("P1", Color.YELLOW)
    board.admit("H3", p, Color.YELLOW, 0)
    board.release("H3", p, Color.YELLOW)
    assert board.intake_limits("H3", 0) == before


def test_pool_staff_arrive_after_delay():
    board = HospitalBoard()
    n0 = board.nurse_spare("H3", 0)
    sid = board.pool_available("nurse")[0].id
    board.assign_pool(sid, "H3", 0)
    assert board.nurse_spare("H3", 10) == n0
    assert board.nurse_spare("H3", 31) == n0 + 1


# ---------------- end-to-end ----------------
def make_scenario(seed=0):
    rng = np.random.default_rng(seed)
    incidents = []
    colors = [Color.RED, Color.RED, Color.YELLOW, Color.YELLOW, Color.GREEN, Color.GREEN, Color.BLACK]
    patients = [Patient(f"P{k}", "I1", 40, "adult_trauma", vitals_for(c, rng), k == 0, c)
                for k, c in enumerate(colors)]
    incidents.append(Incident("I1", 0, (12.0, 15.0), "crash", patients, 7, "D",
                              reported_colors={"red": 2, "yellow": 2, "green": 2, "black": 1}, needs_rescue=True))
    p = Patient("P9", "I2", 70, "cardiac", vitals_for(Color.RED, rng), False, Color.RED)
    incidents.append(Incident("I2", 5, (14.0, 10.0), "cardiac_arrest", [p], 1, "E", reported_colors={"red": 1}))
    ambs = [Ambulance(f"A{i}", (10.0 + i, 14.0), als=i < 3) for i in range(5)]
    teams = [RescueTeam("T1", (11.0, 16.0), ["rescue"])]
    return Scenario("unit", seed, incidents, ambs, teams)


@pytest.mark.parametrize("policy_cls", [NearestPolicy, RulePolicy])
def test_end_to_end_everyone_transported_without_violations(policy_cls):
    sim = Simulation(make_scenario(), policy_cls()).run()
    m = compute_metrics(sim)
    assert m["not_transported"] == 0
    assert m["cad_rejections"] == 0
    assert m["deceased_on_scene"] == 1
    for p in sim.patients.values():
        assert p.status in (PatientStatus.IN_TREATMENT, PatientStatus.DISCHARGED, PatientStatus.DECEASED)


def test_invariants_never_violated():
    sim = Simulation(make_scenario(), RulePolicy())
    sim.run()
    for h in sim.board.hospitals.values():
        assert 0 <= h.beds_used <= h.er_beds
    for s in sim.board.staff:
        assert s.load >= -1e-9


def test_same_seed_same_log():
    def digest():
        sim = Simulation(make_scenario(3), RulePolicy()).run()
        return hashlib.sha256("\n".join(json.dumps(r, sort_keys=True, default=str) for r in sim.logs).encode()).hexdigest()
    assert digest() == digest()


# ---------------- CAD rules ----------------
class Scripted:
    name = "scripted"

    def __init__(self, plan):
        self.plan = plan

    def decide(self, sim):
        return self.plan.pop(sim.t, [])


def test_cad_blocks_double_booking_and_wrong_hospital():
    sc = make_scenario()
    plan = {0: [AssignUnits("I1", ["A0"]), AssignUnits("I1", ["A0"])]}
    sim = Simulation(sc, Scripted(plan))
    sim.t = 0
    for a in plan.pop(0):
        sim.cad.apply(a)
    results = [r for r in sim.logs if r["type"] == "action"]
    assert results[0]["ok"] and not results[1]["ok"] and results[1]["reason"] == "UNIT_BUSY"
    # transport to a hospital without capability is refused
    amb = sim.ambulances["A0"]
    sim._ambulance_arrives(amb, sim.incidents["I1"])
    red = next(p for p in sim.incidents["I1"].patients if p.true_color == Color.RED and p.status == PatientStatus.READY)
    res = sim.cad.apply(CommitTransport("A0", [red.id], "H2"))
    assert not res.ok and res.reason == "CAPABILITY_MISSING"
    res = sim.cad.apply(CommitTransport("A0", [red.id], "H1"))
    assert res.ok


def test_redirect_cancels_old_trip_and_needs_empty_ambulance():
    from ers.env.actions import ReassignUnit
    sim = Simulation(make_scenario(), Scripted({}))
    sim.t = 5
    assert sim.cad.apply(AssignUnits("I1", ["A4"])).ok
    sim.t = 7                                          # halfway: redirect to the cardiac arrest
    res = sim.cad.apply(ReassignUnit("A4", "I2"))
    assert res.ok and sim.ambulances["A4"].incident_id == "I2"
    # run the event queue forward: the old arrival at I1 must be ignored
    import heapq
    while sim.events:
        t, _, fn = heapq.heappop(sim.events)
        sim.t = t
        fn()
    arrivals = [r for r in sim.logs if r["type"] == "unit_on_scene" and r["unit"] == "A4"]
    assert [r["incident_id"] for r in arrivals] == ["I2"]
    # an idle ambulance cannot be "redirected"
    assert sim.cad.apply(ReassignUnit("A0", "I1")).reason == "UNIT_BUSY"


def test_only_surplus_ambulances_can_be_redirected():
    from ers.env.entities import UnitStatus
    from ers.policies.ma import MultiAgentPolicy
    sim = Simulation(make_scenario(), Scripted({}))
    pol = MultiAgentPolicy(backend="mock")
    sim.t = 5
    assert sim.cad.apply(AssignUnits("I2", ["A3"])).ok              # I2 needs one trip: A3 is not spare
    assert pol._waiting_units(sim) == []
    assert sim.cad.apply(AssignUnits("I2", ["A4"])).ok              # a second empty ambulance is surplus
    assert [w["amb"].id for w in pol._waiting_units(sim)] in (["A3"], ["A4"])
    amb = sim.ambulances["A1"]                                       # waiting on scene for the trapped patient
    amb.status, amb.incident_id = UnitStatus.ON_SCENE, "I1"
    assert "A1" not in [w["amb"].id for w in pol._waiting_units(sim)]
