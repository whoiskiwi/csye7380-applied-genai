"""Call-taker notes for each incident, written once by an LLM and cached.

The numbers (victims, location, severity) come from the seeded generator; the LLM only turns them into the
short free-text note a human call-taker would type into the CAD. A note is accepted only if it states the
reported number of people and the block address; otherwise it is regenerated, and after three failures a
template is used. Notes are shown in the visualization; no agent decision reads them.

Usage:
    uv run python -m ers.data.call_text --all --seeds 0-2            # Ollama (ERS_OLLAMA_BASE_URL, ERS_MODEL_FAST)
    uv run python -m ers.data.call_text --all --seeds 0-2 --template # no model
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

from ers.config import ROOT, assumptions, load_yaml
from ers.data.generate import MVP_SCENARIOS, _seeds, build_scenario
from ers.env.entities import Incident

OUT_DIR = ROOT / "data" / "generated" / "call_texts"
ZONES = [["Southwest", "South", "Southeast"], ["West", "Downtown", "East"], ["Northwest", "North", "Northeast"]]
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
                "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
                "twenty", "twenty-one", "twenty-two", "twenty-three", "twenty-four", "twenty-five", "twenty-six"]
TYPE_WORDS = {"cardiac_arrest": "a person collapsed and not breathing normally", "stroke": "possible stroke",
              "chest_pain": "chest pain", "fall": "a fall", "breathing": "difficulty breathing",
              "other": "a medical complaint", "entrapment": "a multi-vehicle crash on the highway",
              "poisoning": "suspected food poisoning at a group dinner",
              "fire": "a building fire"}
SEVERITY_WORDS = {"red": "seriously hurt", "yellow": "hurt but talking", "green": "walking"}

PROMPT = """You are a 911 call-taker typing the free-text note of a computer-aided dispatch record.
Write one to three short sentences in plain English, in the voice of a dispatch note, using only these facts:
- Address: {address}
- What the caller reports: {what}
- Number of people involved, as the caller reports it: {n}
- How they are, as the caller reports it: {severity}
{extra}Start with the address. State the number of people as the digit {n}. Do not add any other facts, labels or numbers.

Example of the style (different facts): "Block 7-3, Southwest. Caller reports a cyclist hit by a car, 2 people
involved: 1 seriously hurt, 1 walking. Caller is on scene and staying on the line."
"""


def address(inc: Incident) -> str:
    size, n = assumptions()["map"]["size_km"], assumptions()["map"]["zone_grid"]
    x, y = inc.location
    zx, zy = min(int(x / size * n), n - 1), min(int(y / size * n), n - 1)
    return f"Block {int(x)}-{int(y)}, {ZONES[zy][zx]}"


def facts(inc: Incident) -> dict:
    sev = ", ".join(f"{v} {SEVERITY_WORDS[k]}" for k, v in inc.reported_colors.items() if k in SEVERITY_WORDS)
    extra = ""
    if inc.needs_rescue:
        extra = "- Some people are trapped and need to be cut out\n"
    if any(p.is_child for p in inc.patients):
        extra += "- A child is involved\n"
    return {"address": address(inc), "what": TYPE_WORDS.get(inc.type, inc.type.replace("_", " ")),
            "n": inc.reported_victims, "severity": sev or "unknown", "extra": extra}


def template(f: dict) -> str:
    s = f"{f['address']}: caller reports {f['what']}, {f['n']} {'person' if f['n'] == 1 else 'people'} involved"
    s += f" ({f['severity']})."
    if "trapped" in f["extra"]:
        s += " Some people are trapped."
    if "child" in f["extra"]:
        s += " A child is involved."
    return s


def check(text: str, f: dict) -> bool:
    """The note must state the reported head count and the address, and mention trapping when there is any."""
    n = f["n"]
    says_n = re.search(rf"(?<![\d-]){n}(?![\d-])", text) is not None or \
        (n < len(NUMBER_WORDS) and re.search(rf"\b{NUMBER_WORDS[n]}\b", text, re.I) is not None)
    has_addr = f["address"].split(",")[0].lower() in text.lower()
    trapped_ok = "trapped" not in f["extra"] or re.search(r"trap|pinned|stuck", text, re.I) is not None
    leaked = re.search(r"digit|address:|number of people|caller reports it", text, re.I) is not None
    return bool(says_n and has_addr and trapped_ok and not leaked)


def _client():
    from openai import OpenAI
    cfg = load_yaml("models.yaml")
    base = os.environ.get("ERS_OLLAMA_BASE_URL", cfg["ollama_base_url"])
    model = os.environ.get("ERS_MODEL_FAST", cfg["tiers"]["fast"]["ollama"])
    return OpenAI(base_url=base, api_key="ollama", timeout=120), model


def write_note(f: dict, client, model) -> tuple[str, str, int]:
    """Returns (text, source, attempts). Attempt 1 is deterministic; retries vary the sampling seed."""
    if client is not None:
        for attempt in range(1, 4):
            try:
                r = client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": PROMPT.format(**f)}],
                    temperature=0 if attempt == 1 else 0.7, seed=attempt, max_tokens=120)
                text = " ".join((r.choices[0].message.content or "").split())
                if check(text, f):
                    return text, "llm", attempt
            except Exception as e:                       # model down or timed out: fall back below
                print(f"    {type(e).__name__}: {e}")
                break
    return template(f), "template", 0


def generate(name: str, seed: int, use_llm: bool = True) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}_seed{seed}.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    client, model = _client() if use_llm else (None, "template")
    out = {}
    for inc in build_scenario(name, seed).incidents:
        f = facts(inc)
        key = hashlib.sha256(json.dumps(f, sort_keys=True).encode()).hexdigest()[:12]
        old = cache.get(inc.id)
        if old and old["facts_hash"] == key and (old["source"] == "llm" or not use_llm):
            out[inc.id] = old
            continue
        text, source, attempts = write_note(f, client, model)
        out[inc.id] = {"text": text, "source": source, "model": model if source == "llm" else "",
                       "attempts": attempts, "facts_hash": key}
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    n_llm = sum(v["source"] == "llm" for v in out.values())
    print(f"{path.relative_to(ROOT)}: {n_llm}/{len(out)} written by the model, the rest by template")
    return out


def load(name: str, seed: int) -> dict[str, str]:
    """incident id -> note; empty if the notes were never generated."""
    path = OUT_DIR / f"{name}_seed{seed}.json"
    return {k: v["text"] for k, v in json.loads(path.read_text()).items()} if path.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--template", action="store_true", help="skip the model and use the template for every note")
    args = ap.parse_args()
    for name in (MVP_SCENARIOS if args.all else [args.scenario]):
        for seed in _seeds(args.seeds):
            generate(name, seed, use_llm=not args.template)


if __name__ == "__main__":
    main()
