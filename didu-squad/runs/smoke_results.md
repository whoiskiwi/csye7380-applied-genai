# Results (smoke)

3 scenarios × 2 seeds; every method runs on the same generated instances. MA and MA-NoNeg use the same local model and prompts; the only difference is negotiation.

## Mean per scenario

**Served in window (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.447 | 0.737 | 0.474 | 0.711 |
| S3 banquet food poisoning | 0.828 | 0.844 | 0.844 | 0.844 |
| S5 two major incidents at once | 0.526 | 0.658 | 0.500 | 0.579 |

**Red patients in window (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.321 | 0.375 | 0.375 | 0.312 |
| S3 banquet food poisoning | 0.479 | 0.495 | 0.495 | 0.523 |
| S5 two major incidents at once | 0.146 | 0.166 | 0.134 | 0.141 |

**Unserved critical incidents**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 4.500 | 4.500 | 4.500 | 5.000 |
| S3 banquet food poisoning | 4.500 | 5.000 | 5.000 | 5.000 |
| S5 two major incidents at once | 9.500 | 9.500 | 8.500 | 9.000 |

**Capability match (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.395 | 0.711 | 0.421 | 0.789 |
| S3 banquet food poisoning | 0.891 | 0.938 | 0.938 | 0.969 |
| S5 two major incidents at once | 0.737 | 0.816 | 0.763 | 0.882 |

**Mean response time (min)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 27.250 | 33.500 | 26.960 | 35.210 |
| S3 banquet food poisoning | 69.345 | 71.655 | 71.885 | 73.620 |
| S5 two major incidents at once | 176.585 | 144.500 | 170.580 | 162.375 |

**Cardiac arrest / stroke response (min)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 29.325 | 37.150 | 24.425 | 32.250 |
| S3 banquet food poisoning | 76.250 | 32.625 | 33.250 | 34.250 |
| S5 two major incidents at once | 204.300 | 83.300 | 84.900 | 84.100 |

**Ambulance utilisation**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.873 | 0.843 | 0.868 | 0.839 |
| S3 banquet food poisoning | 0.889 | 0.910 | 0.908 | 0.915 |
| S5 two major incidents at once | 0.951 | 0.961 | 0.914 | 0.946 |

## Paired difference: MA − MA-NoNeg

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA_mean | MA-NoNeg_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 6 | 0.711 | 0.606 | 0.105 | 0.026 | 0.184 | 0.125 | A |
| all | red_in_window_rate | 6 | 0.326 | 0.335 | -0.009 | -0.061 | 0.039 | 1.000 | B |
| all | unserved_critical_incidents | 6 | 6.333 | 6.000 | 0.333 | 0.000 | 0.667 | 0.500 | B |
| all | capability_match_rate | 6 | 0.880 | 0.707 | 0.173 | 0.065 | 0.291 | 0.031 | A |
| all | response_time_mean | 6 | 90.402 | 89.808 | 0.593 | -8.433 | 6.982 | 0.438 | B |
| all | time_critical_response_mean | 6 | 50.200 | 47.525 | 2.675 | -2.267 | 6.933 | 0.438 | B |
| all | ambulance_utilisation | 6 | 0.900 | 0.897 | 0.004 | -0.037 | 0.032 | 0.562 |  |
| S1 freeway pileup | served_rate | 2 | 0.711 | 0.474 | 0.237 | 0.211 | 0.263 |  | A |
| S1 freeway pileup | red_in_window_rate | 2 | 0.312 | 0.375 | -0.062 | -0.125 | 0.000 |  | B |
| S1 freeway pileup | unserved_critical_incidents | 2 | 5.000 | 4.500 | 0.500 | 0.000 | 1.000 |  | B |
| S1 freeway pileup | capability_match_rate | 2 | 0.789 | 0.421 | 0.368 | 0.316 | 0.421 |  | A |
| S1 freeway pileup | response_time_mean | 2 | 35.210 | 26.960 | 8.250 | 5.000 | 11.500 |  | B |
| S1 freeway pileup | time_critical_response_mean | 2 | 32.250 | 24.425 | 7.825 | 5.250 | 10.400 |  | B |
| S1 freeway pileup | ambulance_utilisation | 2 | 0.839 | 0.868 | -0.029 | -0.090 | 0.032 |  |  |
| S3 banquet food poisoning | served_rate | 2 | 0.844 | 0.844 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | red_in_window_rate | 2 | 0.523 | 0.495 | 0.028 | 0.000 | 0.056 |  | A |
| S3 banquet food poisoning | unserved_critical_incidents | 2 | 5.000 | 5.000 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | capability_match_rate | 2 | 0.969 | 0.938 | 0.031 | 0.031 | 0.031 |  | A |
| S3 banquet food poisoning | response_time_mean | 2 | 73.620 | 71.885 | 1.735 | 1.470 | 2.000 |  | B |
| S3 banquet food poisoning | time_critical_response_mean | 2 | 34.250 | 33.250 | 1.000 | 0.000 | 2.000 |  | B |
| S3 banquet food poisoning | ambulance_utilisation | 2 | 0.915 | 0.908 | 0.007 | -0.001 | 0.015 |  |  |
| S5 two major incidents at once | served_rate | 2 | 0.579 | 0.500 | 0.079 | 0.053 | 0.105 |  | A |
| S5 two major incidents at once | red_in_window_rate | 2 | 0.141 | 0.134 | 0.007 | -0.048 | 0.062 |  | A |
| S5 two major incidents at once | unserved_critical_incidents | 2 | 9.000 | 8.500 | 0.500 | 0.000 | 1.000 |  | B |
| S5 two major incidents at once | capability_match_rate | 2 | 0.882 | 0.763 | 0.118 | 0.105 | 0.132 |  | A |
| S5 two major incidents at once | response_time_mean | 2 | 162.375 | 170.580 | -8.205 | -20.330 | 3.920 |  | A |
| S5 two major incidents at once | time_critical_response_mean | 2 | 84.100 | 84.900 | -0.800 | -8.000 | 6.400 |  | A |
| S5 two major incidents at once | ambulance_utilisation | 2 | 0.946 | 0.914 | 0.033 | 0.018 | 0.048 |  |  |

## Paired difference: MA − B1

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA_mean | B1_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 6 | 0.711 | 0.746 | -0.035 | -0.070 | -0.009 | 0.250 | B |
| all | red_in_window_rate | 6 | 0.326 | 0.345 | -0.020 | -0.067 | 0.020 | 0.625 | B |
| all | unserved_critical_incidents | 6 | 6.333 | 6.333 | 0.000 | -0.500 | 0.500 | 1.000 | = |
| all | capability_match_rate | 6 | 0.880 | 0.821 | 0.059 | 0.038 | 0.080 | 0.031 | A |
| all | response_time_mean | 6 | 90.402 | 83.218 | 7.183 | 1.026 | 14.087 | 0.156 | B |
| all | time_critical_response_mean | 6 | 50.200 | 51.025 | -0.825 | -4.200 | 1.450 | 0.812 | A |
| all | ambulance_utilisation | 6 | 0.900 | 0.905 | -0.004 | -0.049 | 0.039 | 0.688 |  |
| S1 freeway pileup | served_rate | 2 | 0.711 | 0.737 | -0.026 | -0.053 | 0.000 |  | B |
| S1 freeway pileup | red_in_window_rate | 2 | 0.312 | 0.375 | -0.062 | -0.125 | 0.000 |  | B |
| S1 freeway pileup | unserved_critical_incidents | 2 | 5.000 | 4.500 | 0.500 | 0.000 | 1.000 |  | B |
| S1 freeway pileup | capability_match_rate | 2 | 0.789 | 0.711 | 0.079 | 0.053 | 0.105 |  | A |
| S1 freeway pileup | response_time_mean | 2 | 35.210 | 33.500 | 1.710 | -3.080 | 6.500 |  | B |
| S1 freeway pileup | time_critical_response_mean | 2 | 32.250 | 37.150 | -4.900 | -9.000 | -0.800 |  | A |
| S1 freeway pileup | ambulance_utilisation | 2 | 0.839 | 0.843 | -0.004 | -0.095 | 0.087 |  |  |
| S3 banquet food poisoning | served_rate | 2 | 0.844 | 0.844 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | red_in_window_rate | 2 | 0.523 | 0.495 | 0.028 | 0.000 | 0.056 |  | A |
| S3 banquet food poisoning | unserved_critical_incidents | 2 | 5.000 | 5.000 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | capability_match_rate | 2 | 0.969 | 0.938 | 0.031 | 0.031 | 0.031 |  | A |
| S3 banquet food poisoning | response_time_mean | 2 | 73.620 | 71.655 | 1.965 | 1.770 | 2.160 |  | B |
| S3 banquet food poisoning | time_critical_response_mean | 2 | 34.250 | 32.625 | 1.625 | 1.000 | 2.250 |  | B |
| S3 banquet food poisoning | ambulance_utilisation | 2 | 0.915 | 0.910 | 0.005 | -0.002 | 0.012 |  |  |
| S5 two major incidents at once | served_rate | 2 | 0.579 | 0.658 | -0.079 | -0.105 | -0.053 |  | B |
| S5 two major incidents at once | red_in_window_rate | 2 | 0.141 | 0.166 | -0.025 | -0.027 | -0.022 |  | B |
| S5 two major incidents at once | unserved_critical_incidents | 2 | 9.000 | 9.500 | -0.500 | -1.000 | 0.000 |  | A |
| S5 two major incidents at once | capability_match_rate | 2 | 0.882 | 0.816 | 0.066 | 0.053 | 0.079 |  | A |
| S5 two major incidents at once | response_time_mean | 2 | 162.375 | 144.500 | 17.875 | 13.330 | 22.420 |  | B |
| S5 two major incidents at once | time_critical_response_mean | 2 | 84.100 | 83.300 | 0.800 | 0.000 | 1.600 |  | B |
| S5 two major incidents at once | ambulance_utilisation | 2 | 0.946 | 0.961 | -0.014 | -0.016 | -0.012 |  |  |

## Paired difference: MA-NoNeg − B1

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA-NoNeg_mean | B1_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 6 | 0.606 | 0.746 | -0.140 | -0.228 | -0.053 | 0.125 | B |
| all | red_in_window_rate | 6 | 0.335 | 0.345 | -0.011 | -0.073 | 0.052 | 1.000 | B |
| all | unserved_critical_incidents | 6 | 6.000 | 6.333 | -0.333 | -1.167 | 0.333 | 0.750 | A |
| all | capability_match_rate | 6 | 0.707 | 0.821 | -0.114 | -0.228 | -0.018 | 0.125 | B |
| all | response_time_mean | 6 | 89.808 | 83.218 | 6.590 | -3.964 | 19.124 | 0.562 | B |
| all | time_critical_response_mean | 6 | 47.525 | 51.025 | -3.500 | -9.575 | 2.442 | 0.562 | A |
| all | ambulance_utilisation | 6 | 0.897 | 0.905 | -0.008 | -0.033 | 0.021 | 0.312 |  |
| S1 freeway pileup | served_rate | 2 | 0.474 | 0.737 | -0.263 | -0.316 | -0.211 |  | B |
| S1 freeway pileup | red_in_window_rate | 2 | 0.375 | 0.375 | 0.000 | -0.125 | 0.125 |  | = |
| S1 freeway pileup | unserved_critical_incidents | 2 | 4.500 | 4.500 | 0.000 | -1.000 | 1.000 |  | = |
| S1 freeway pileup | capability_match_rate | 2 | 0.421 | 0.711 | -0.289 | -0.368 | -0.211 |  | B |
| S1 freeway pileup | response_time_mean | 2 | 26.960 | 33.500 | -6.540 | -8.080 | -5.000 |  | A |
| S1 freeway pileup | time_critical_response_mean | 2 | 24.425 | 37.150 | -12.725 | -14.250 | -11.200 |  | A |
| S1 freeway pileup | ambulance_utilisation | 2 | 0.868 | 0.843 | 0.025 | -0.005 | 0.055 |  |  |
| S3 banquet food poisoning | served_rate | 2 | 0.844 | 0.844 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | red_in_window_rate | 2 | 0.495 | 0.495 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | unserved_critical_incidents | 2 | 5.000 | 5.000 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | capability_match_rate | 2 | 0.938 | 0.938 | 0.000 | 0.000 | 0.000 |  | = |
| S3 banquet food poisoning | response_time_mean | 2 | 71.885 | 71.655 | 0.230 | 0.160 | 0.300 |  | B |
| S3 banquet food poisoning | time_critical_response_mean | 2 | 33.250 | 32.625 | 0.625 | 0.250 | 1.000 |  | B |
| S3 banquet food poisoning | ambulance_utilisation | 2 | 0.908 | 0.910 | -0.002 | -0.003 | -0.001 |  |  |
| S5 two major incidents at once | served_rate | 2 | 0.500 | 0.658 | -0.158 | -0.158 | -0.158 |  | B |
| S5 two major incidents at once | red_in_window_rate | 2 | 0.134 | 0.166 | -0.032 | -0.089 | 0.025 |  | B |
| S5 two major incidents at once | unserved_critical_incidents | 2 | 8.500 | 9.500 | -1.000 | -2.000 | 0.000 |  | A |
| S5 two major incidents at once | capability_match_rate | 2 | 0.763 | 0.816 | -0.053 | -0.053 | -0.053 |  | B |
| S5 two major incidents at once | response_time_mean | 2 | 170.580 | 144.500 | 26.080 | 18.500 | 33.660 |  | B |
| S5 two major incidents at once | time_critical_response_mean | 2 | 84.900 | 83.300 | 1.600 | -4.800 | 8.000 |  | B |
| S5 two major incidents at once | ambulance_utilisation | 2 | 0.914 | 0.961 | -0.047 | -0.060 | -0.034 |  |  |

## LLM usage per run (mean)

| policy | llm_calls | llm_failures | fallbacks | partial_fills | fallback_rate | tokens_in | tokens_out | agent_escalations | mean_rounds | rule_retries | rule_violations_kept | accept_mismatch | redirects | messages | wall_seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MA | 162.167 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 18.333 | 1.237 | 5.500 | 5.500 | 0.000 | 0.000 | 212.833 | 0.567 |
| MA-NoNeg | 120.667 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 160.667 | 0.450 |

## Role-rule checks

An agent that breaks a rule of its own prompt is told which rule and answers once more; the second answer is used either way. `fixed_by_retry` = share of violations the second answer corrected.

| policy | agent | violations | fixed_by_retry |
|---|---|---|---|
| MA | Dispatch | 30 | 0.000 |
| MA | HospitalCoordination | 3 | 0.000 |
| MA-NoNeg | HospitalCoordination | 6 | 0.000 |

## Transport decisions vs references

`changed_by_negotiation` = final destination differs from Dispatch's first proposal.

| policy | decisions | same_as_rule | same_as_nearest | changed_by_negotiation |
|---|---|---|---|---|
| MA | 139 | 0.928 | 0.813 | 0.187 |
| MA-NoNeg | 139 | 0.914 | 1.000 | 0.000 |
