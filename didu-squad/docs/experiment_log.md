# Experiment log

What each experiment run showed, what we found in the logs, and what we changed. Every number below
comes from the run's own files (`summary.csv`, `events.jsonl`, `decisions.jsonl`, `snapshots.jsonl`);
full tables: round 1 in [`results_round1.md`](results_round1.md), round 2 in [`results.md`](results.md).

Setup common to both rounds: 3 scenarios (S1 freeway pile-up, S3 banquet food poisoning, S5 both
at once), 4 methods (B0, B1, MA-NoNeg, MA) on the same generated instances, 6 ambulances, 3 rescue
teams, 3 hospitals. Models: qwen2.5:14b for Hospital Coordination and the commander, qwen2.5:3b for
the other agents, served by Ollama 0.6.8 on one Tesla V100 32 GB (Northeastern Explorer cluster),
temperature 0, every response cached.

## Round 1 (`configs/exp_mvp.yaml`, seeds 0–2)

### Results

Share of patients served in their window (mean of 3 seeds):

| Scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pile-up | 0.456 | 0.737 | 0.456 | **0.737** |
| S3 banquet food poisoning | 0.823 | **0.875** | 0.833 | 0.802 |
| S5 both at once | 0.491 | **0.605** | 0.588 | 0.579 |

MA − MA-NoNeg over the 9 (scenario, seed) pairs, 95 % bootstrap CI, Wilcoxon p:

| Metric | Difference | 95 % CI | p |
|---|---|---|---|
| Capability match (share sent to a specialty-matched hospital) | **+0.180** | [+0.061, +0.299] | 0.035 |
| Served in window | +0.080 | [−0.020, +0.189] | 0.31 |
| Red patients in window | 0.000 | [−0.105, +0.106] | 0.95 |

By scenario, negotiation helped clearly in S1 (served 0.737 vs 0.456 on all three seeds) and not in
S3 (0.802 vs 0.833) or S5 (0.579 vs 0.588). MA matched the rule reference B1 on S1 but stayed below
it on S3. The agents made 206 model calls per MA run; only 0.1 % ended in a rule fallback, so the
results are the agents' own decisions.

### Diagnosis

We went through the logs of the runs where MA did worse than MA-NoNeg.

1. **ACCEPT used to change the hospital.** Hospital Coordination sometimes answered ACCEPT but
   named another hospital, and the code used that hospital. Example (S3 seed 1, minute 11): Dispatch
   proposed H3 (13 min, specialty match) for a yellow food-poisoning patient; the answer was "ACCEPT
   H1" (28 min, also a match). The load went to the farther hospital without any negotiation.
2. **Green loads were labelled "not a match" at hospitals that serve them.** A green patient counts
   as served at any hospital that can treat them, but the option labels used the full specialty
   matrix, so Hospital Coordination moved walking-wounded to the distant trauma center H1. In S3,
   B1 sent 54 of 72 trips to the nearby H3 (mean trip 11.0 min); MA-NoNeg 36 (14.2 min); MA 35
   (14.7 min). Longer trips mean ambulances return later and the next callers wait longer.
3. **Many needless counter-proposals.** In S5, Hospital Coordination countered 165 times and
   accepted 32 times; the most common reason was LOAD_BALANCE, i.e. moving a load to another
   hospital of the same suitability. Some counters even named the proposed hospital. 97 of 209 MA
   transport decisions (46 %) reached the 3-round limit and went to the commander.
4. **Commander transport rulings were often not the best option.** 31 of the 97 rulings did not pick
   the nearest hospital among those with the best suitability, e.g. a non-matched hospital 24 min
   away over a matched one 13 min away.
5. **Redirects took ambulances away from trapped patients.** An ambulance waiting on scene for
   extrication counted as "free" for the commander's redirect. Trapped patients are usually the most
   injured, so when they were freed no ambulance was left. In S1 every redirect moved an ambulance
   away from the pile-up; red patients leaving the pile-up within 60 minutes: MA 1.0 per run,
   B1 and MA-NoNeg 2.0. A test written for the fix also showed that with two empty ambulances and
   one trip needed, both were counted as surplus.
6. **Net effect on red patients.** Time from the first unit on scene to a red patient's departure:
   S3 MA 20 min vs 11 min (B1 and MA-NoNeg); S5 MA 82 min vs 44 min (B1) and 61 min (MA-NoNeg).

Checked and not a problem: hospital agents reported their real capacity (no hidden beds); sending
two ambulances to a one-patient call was as rare in MA (7) as in MA-NoNeg (8); all methods sent the
same number of ambulances to the major incidents in the first 30 minutes.

Items 1, 2 and 5 were bugs in our code (an unchecked model output, a label inconsistent with the
outcome model, an over-broad "free unit" rule). Items 3 and 4 were prompt rules that a small model
could read two ways ("the best option" when two options are equally good).

## Changes for round 2

Applied to MA and MA-NoNeg alike, so the ablation stays fair.

| Change | Where |
|---|---|
| ACCEPT always means the proposed hospital. Naming another one is treated as a counter-proposal in MA (Dispatch must agree) and as accepting the proposal in MA-NoNeg; a counter naming the proposed hospital is an accept | `policies/ma.py` `_admission_round` |
| Green-only loads: every hospital that can treat them is labelled `match` | `policies/ma.py` `_options` |
| Hospital options are listed nearest first | `policies/ma.py` `_options` |
| Hospital Coordination prompt v3: accept unless an option with room is strictly better; another hospital of the same suitability is not a reason to counter | `agents/prompts/hospital_coordination.md` |
| Dispatch prompt v3: speed first, propose the first (nearest) option that can take the load; the red-patient exception is unchanged. Dispatch keeps its speed-first role on purpose: the conflict with Hospital Coordination's specialty-first role is what negotiation resolves | `agents/prompts/dispatch_transport.md` |
| Commander prompt v4: best suitability, then shortest ETA; only surplus ambulances can be redirected | `agents/prompts/resource_allocation.md` |
| Only surplus ambulances can be redirected: an incident keeps as many empty ambulances as it still needs trips (the closest ones) | `policies/ma.py` `_waiting_units`, test `test_only_surplus_ambulances_can_be_redirected` |
| Role-rule checks: when Hospital Coordination, Dispatch (replies to counters) or the commander (transport rulings) break a rule of their own prompt, they are told which rule and answer once more; the second answer is used either way and each case is logged | `agents/runtime.py` (`soft`), `policies/ma.py` |
| 5 seeds instead of 3 | `configs/exp_mvp_v2.yaml` |

Check before the cluster run (laptop, qwen2.5:3b for every agent, S3 seed 1, MA only, not a
reported result): the pipeline ran without errors; 2 of 24 transport decisions went to the commander
(round 1: about half); mean negotiation rounds 1.36 (round 1: 2.14). The role-rule check fired 11
times and the 3b model repeated the same answer every time, so whether the retry helps the 14b
agents is measured in round 2.

## Round 2 (`configs/exp_mvp_v2.yaml`, seeds 0–4)

Cluster job 11435525, 60 runs, about 2 hours of model time on one V100 (some answers were reused from
the cache of an earlier, cancelled attempt). Full tables in [`results.md`](results.md).

### Results

Share of patients served in their window (mean of 5 seeds):

| Scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pile-up | 0.463 | **0.768** | 0.758 | 0.726 |
| S3 banquet food poisoning | 0.838 | **0.906** | 0.881 | 0.888 |
| S5 both at once | 0.505 | **0.621** | 0.589 | 0.579 |

MA − MA-NoNeg over the 15 (scenario, seed) pairs, 95 % bootstrap CI, Wilcoxon p:

| Metric | Difference | 95 % CI | p |
|---|---|---|---|
| Served in window | −0.012 | [−0.039, +0.016] | 0.51 |
| Red patients in window | −0.029 | [−0.110, +0.051] | 0.31 |
| Capability match | −0.020 | [−0.039, −0.001] | 0.11 |
| Cardiac arrest / stroke response time (min) | **−5.1** | [−10.9, −0.2] | 0.059 |

The agents (MA and MA-NoNeg alike) against the rule reference B1:

| Metric | MA-NoNeg − B1 | MA − B1 |
|---|---|---|
| Capability match | **+0.113** [+0.059, +0.170], p = 0.005 | **+0.093** [+0.044, +0.145], p = 0.005 |
| Served in window | −0.022 [−0.041, −0.004] | −0.034 [−0.063, −0.008] |
| Red patients in window | −0.056 [−0.087, −0.027] | −0.085 [−0.161, −0.008] |
| S5 mean response time (min) | **−63.5** [−92.2, −34.7] | **−64.4** [−91.0, −30.3] |
| S5 unserved critical incidents | **−2.0** [−3.2, −0.8] | **−2.0** [−3.2, −0.8] |

Model behaviour: 170 calls per MA run, fallback rate 0.6 %. Mean negotiation rounds 1.12 (round 1:
2.14); 4.3 escalations to the commander per run (round 1: 15.0); no redirects (round 1: 0.9 per run). The role-rule
check fired 254 times for Hospital Coordination and 84 times for Dispatch in MA; the second answer
corrected about 75 % of them.

### What the round-2 results say

1. **The fixes helped MA-NoNeg, not MA.** On the same seeds 0–2 (B0 and B1 give identical numbers in
   both rounds, so the instances are the same), served in window went from 0.626 to 0.721 for
   MA-NoNeg (S1 0.456 → 0.719) but from 0.706 to 0.699 for MA (S1 0.737 → 0.684, red patients in
   window 0.310 → 0.185). The round-1 gap between MA and MA-NoNeg came mostly from those bugs, which
   hurt the single-round decision more than the three-round one, not from negotiation itself. Why MA
   lost red patients in S1 is item 7.
2. **Negotiation no longer changes the outcome.** MA and MA-NoNeg are within noise on every outcome
   metric except time-critical response (MA 5 min faster, p = 0.059). That difference is in the time
   to reach cardiac arrest and stroke calls, which negotiation does not decide directly; we have not
   traced its cause and treat it as indicative only.
3. **Why there is little left for negotiation to win.** Negotiation in this design only chooses the
   hospital for each load. For red patients we checked, at the moment of each decision, whether any
   hospital was both specialty-matched and reachable inside the patient's window. That was true for
   only 10 of 34 red loads in S1, 28 of 46 in S3 and 10 of 89 in S5 (MA runs; MA-NoNeg similar). When
   such a hospital existed, MA chose it in 45 of 48 cases and MA-NoNeg in 46 of 46. The remaining red
   patients are lost before transport: in S5 a red patient waits on average 62 min for the first
   unit and 83 min more until an ambulance leaves the scene (B1: 96 and 51). That is a shortage of
   ambulances, which hospital negotiation cannot change.
4. **A single round is already good.** With the role-rule checks, Hospital Coordination's
   accept/reject is mostly right, and MA-NoNeg's rule for a rejected load (nearest hospital that can
   take it) is itself sensible. MA changed Dispatch's proposal in 30 % of decisions (MA-NoNeg 17 %),
   mostly between hospitals with the same outcome. Two S1 counters moved a red load from the matched
   H3 to a later, non-matched hospital because H3 reported no red bed left; that is a capacity
   decision, not a negotiation error.
5. **The commander now has little to do.** Only surplus ambulances can be redirected, and in these
   scenarios there were never any, so redirects stayed at 0. The resource-level negotiation is never
   exercised.
6. **What the agents gain over the rules.** Both agent methods send more patients to a
   specialty-matched hospital (+0.09 to +0.11 vs B1) and, when two major incidents happen at once
   (S5), reach calls about an hour faster on average and leave two fewer critical incidents
   unserved, because Incident Assessment ranks all open calls together instead of first come first
   served. They lose to B1 on red patients in window because they more often choose a matched
   hospital that is farther away.

7. **MA got worse in S1 because the redirect fix removed a useful decision.** In round 1 the
   commander redirected an ambulance at minute 28–29 from the pile-up to a cardiac-arrest call in
   seed 0 (once) and seed 1 (twice); seed 2 had no redirect. Per red patient on seeds 0–2, MA served
   7 in round 1 and 4 in round 2. The losses are exactly those cardiac-arrest calls: they left the
   scene at minutes 51, 47 and 44 in round 1 and at 94, 93 and 108 in round 2 (MA-NoNeg in round 2:
   the same late times). The seed without a redirect improved (0.684 → 0.789). The ambulances that
   were redirected were waiting for trapped trauma patients who could not be served in window
   anyway: no trauma center was reachable in time, so they count as late or not matched in both
   rounds. Our round-1 diagnosis (item 5) judged the redirects by how fast red patients left the
   pile-up, not by whether anyone was served; by outcome the redirects helped. The "surplus only"
   rule is too strict: it never lets the commander weigh a long extrication against a cardiac
   arrest elsewhere, which is the trade-off a real commander makes.
8. **Model quality limits the designed conflict.** Dispatch (qwen2.5:3b) proposed the hospital its
   own rule asks for (nearest option that can take the load; for red patients the nearest
   in-window specialty match) in only 40 % of 359 MA decisions (MA-NoNeg 38 %). In 74 of the
   deviations it already proposed a farther, better-matched hospital, i.e. it did Hospital
   Coordination's job, and in 27 it proposed a hospital that could not take the load. Its first
   proposal is not covered by the role-rule check. The speed-versus-specialty conflict that
   negotiation is meant to resolve therefore often never arises. Hospital Coordination and the
   commander (qwen2.5:14b) do better: 75 % of their rule violations were corrected on the retry and
   when a matched in-window hospital existed it was chosen in 45 of 48 red loads.

Conclusion for the report: communication and coordination between the agents give measurable gains
over the rule baselines on specialty match and on response times under overload. The extra value of
multi-round negotiation is not significant in these scenarios, and the analysis above shows why:
the decision it controls (which hospital) has little room for improvement once single-round answers
are checked against the role rules.
