# Submission text (draft)

> Paste the part below the line into the Canvas text box. Fill in the items marked ⟨…⟩
> (names, repository link) before submitting.

---

**Multi-Agent Emergency Response Coordination** — ⟨team / names⟩

Repository: ⟨link⟩ (start with `README.md`; design in `docs/emergency_response_plan_v2.md`,
assumptions in `docs/assumptions.md`, experiment log in `docs/experiment_log.md`, results in `docs/results.md`)

**What we built.** A synthetic emergency-response environment (incidents with victims, severity and
time windows; 3 hospitals with ER beds, doctors and nurses with skills and workload limits;
6 ambulances; 3 rescue teams; a regional reserve staff pool) run by a discrete-event simulator, and
seven agents built with the OpenAI Agents SDK (5 agent types):

- **Incident Assessment** ranks all active incidents from the call-taker's noisy records, pre-alerts
  the hospital side and escalates mass-casualty incidents.
- **Dispatch** assigns ambulances and rescue teams and proposes a destination for every load
  (speed first).
- **Hospital Coordination** accepts, rejects or counters each proposed admission (specialty and
  capacity first) and negotiates the shared staff pool among the hospitals.
- **Three Hospital agents** report how many red / yellow / green patients they will still accept and
  request staff.
- **Resource Allocation** (incident commander) rules on contested units, escalations and transport
  disagreements, and may redirect surplus ambulances.

Agents exchange structured messages (sender, recipient, message type, incident id, proposed action,
plus reason code, round and thread). They only propose; a rule-checking CAD layer executes valid
actions. When Dispatch and Hospital Coordination disagree they negotiate for up to three rounds of
counter-proposals before the commander rules.

**Does negotiation help?** We compare four methods on identical generated instances
(3 scenarios × 5 seeds): B0 nearest hospital, B1 field-triage rules, MA-NoNeg (the same agents,
models and prompts with negotiation removed) and MA (full negotiation). MA vs MA-NoNeg isolates the
value of negotiation. Over 15 paired instances, both agent methods beat the rule
reference B1 on specialty match (+0.09 to +0.11, 95 % CI above zero, p = 0.005) and, when two major
incidents happen at once, reach calls about an hour faster and leave two fewer critical incidents
unserved; they trail B1 slightly on patients served in window (MA 0.731, MA-NoNeg 0.743, B1 0.765).
MA vs MA-NoNeg is within noise on served in window (−0.012, CI [−0.039, +0.016]); the only
indicative gain is a 5-minute faster response to cardiac arrest and stroke calls (CI [−10.9, −0.2],
p = 0.059). The logs show why multi-round negotiation adds little here: it only chooses the hospital,
and for most red patients no specialty hospital is reachable inside their window by the time an
ambulance has loaded them, while when one is, both variants already choose it (45/48 and 46/46).
The bottleneck is ambulances, not hospital choice.

**Iteration.** A first run showed negotiation clearly helping in the freeway pile-up (served 0.737 vs
0.456) but not in the food-poisoning scenario. Reading the decision logs showed why: an unchecked model output let an
"accept" silently change the hospital, green patients were labelled as needing the distant trauma
center, prompts let the coordinator counter between equally good hospitals, and the commander could
redirect ambulances that were waiting for trapped (most injured) patients. We fixed these for both
MA and MA-NoNeg and re-ran with more seeds. On the same seeds the fixes lifted MA-NoNeg (S1 0.456 → 0.719)
but not MA (0.737 → 0.684), so most of the round-1 gap had come from the bugs rather than from
negotiation;
`docs/experiment_log.md` gives the evidence and the changes.

**Visualization.** `streamlit run app/streamlit_app.py` replays any run minute by minute: incident
map with severity and assigned units, resource dashboard (ambulances, rescue teams, beds, doctors,
nurses), agent activity panel with messages and pending requests, negotiation history with every
thread and decision record, performance indicators over time, and a method-comparison page.

**Data and reproducibility.** Incident numbers are generated with fixed seeds from documented
assumptions; the call-taker notes are written once by the LLM and cached. Models are free
open-source models (qwen2.5:14b and 3b via Ollama on the Northeastern Explorer GPU cluster); every
model response is cached, so `cache_mode: replay` reproduces the results exactly without a GPU.
