# Results (mvp)

3 scenarios × 3 seeds; every method runs on the same generated instances. MA and MA-NoNeg use the same local model and prompts; the only difference is negotiation.

## Mean per scenario

**Served in window (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.456 | 0.737 | 0.456 | 0.737 |
| S3 banquet food poisoning | 0.823 | 0.875 | 0.833 | 0.802 |
| S5 two major incidents at once | 0.491 | 0.605 | 0.588 | 0.579 |

**Red patients in window (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.262 | 0.345 | 0.167 | 0.310 |
| S3 banquet food poisoning | 0.486 | 0.580 | 0.573 | 0.467 |
| S5 two major incidents at once | 0.098 | 0.142 | 0.152 | 0.116 |

**Unserved critical incidents**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 4.667 | 4.333 | 5.333 | 4.333 |
| S3 banquet food poisoning | 4.000 | 4.000 | 4.667 | 5.333 |
| S5 two major incidents at once | 10.000 | 10.000 | 6.667 | 7.333 |

**Capability match (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.421 | 0.702 | 0.421 | 0.825 |
| S3 banquet food poisoning | 0.875 | 0.948 | 0.917 | 0.885 |
| S5 two major incidents at once | 0.754 | 0.825 | 0.763 | 0.930 |

**Mean response time (min)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 26.223 | 32.583 | 28.443 | 35.087 |
| S3 banquet food poisoning | 67.590 | 71.590 | 80.203 | 75.280 |
| S5 two major incidents at once | 178.807 | 165.640 | 113.750 | 111.497 |

**Cardiac arrest / stroke response (min)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 27.300 | 32.850 | 27.483 | 33.083 |
| S3 banquet food poisoning | 71.610 | 40.527 | 48.527 | 75.667 |
| S5 two major incidents at once | 191.423 | 116.090 | 61.490 | 41.467 |

**Ambulance utilisation**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.844 | 0.851 | 0.793 | 0.851 |
| S3 banquet food poisoning | 0.897 | 0.907 | 0.914 | 0.899 |
| S5 two major incidents at once | 0.933 | 0.946 | 0.928 | 0.914 |

## Paired difference: MA − MA-NoNeg

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA_mean | MA-NoNeg_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 9 | 0.706 | 0.626 | 0.080 | -0.020 | 0.189 | 0.312 | A |
| all | red_in_window_rate | 9 | 0.297 | 0.297 | -0.000 | -0.105 | 0.106 | 0.945 | B |
| all | unserved_critical_incidents | 9 | 5.667 | 5.556 | 0.111 | -0.667 | 1.000 | 0.906 | B |
| all | capability_match_rate | 9 | 0.880 | 0.700 | 0.180 | 0.061 | 0.299 | 0.035 | A |
| all | response_time_mean | 9 | 73.954 | 74.132 | -0.178 | -9.871 | 9.346 | 1.000 | A |
| all | time_critical_response_mean | 9 | 50.072 | 45.833 | 4.239 | -10.245 | 18.195 | 0.496 | B |
| all | ambulance_utilisation | 9 | 0.888 | 0.879 | 0.010 | -0.026 | 0.046 | 0.570 |  |
| S1 freeway pileup | served_rate | 3 | 0.737 | 0.456 | 0.281 | 0.263 | 0.316 |  | A |
| S1 freeway pileup | red_in_window_rate | 3 | 0.310 | 0.167 | 0.143 | 0.000 | 0.286 |  | A |
| S1 freeway pileup | unserved_critical_incidents | 3 | 4.333 | 5.333 | -1.000 | -2.000 | 0.000 |  | A |
| S1 freeway pileup | capability_match_rate | 3 | 0.825 | 0.421 | 0.403 | 0.368 | 0.474 |  | A |
| S1 freeway pileup | response_time_mean | 3 | 35.087 | 28.443 | 6.643 | 5.090 | 8.340 |  | B |
| S1 freeway pileup | time_critical_response_mean | 3 | 33.083 | 27.483 | 5.600 | -5.200 | 14.000 |  | B |
| S1 freeway pileup | ambulance_utilisation | 3 | 0.851 | 0.793 | 0.058 | 0.004 | 0.090 |  |  |
| S3 banquet food poisoning | served_rate | 3 | 0.802 | 0.833 | -0.031 | -0.062 | 0.000 |  | B |
| S3 banquet food poisoning | red_in_window_rate | 3 | 0.467 | 0.573 | -0.107 | -0.236 | 0.083 |  | B |
| S3 banquet food poisoning | unserved_critical_incidents | 3 | 5.333 | 4.667 | 0.667 | -1.000 | 2.000 |  | B |
| S3 banquet food poisoning | capability_match_rate | 3 | 0.885 | 0.917 | -0.031 | -0.094 | 0.031 |  | B |
| S3 banquet food poisoning | response_time_mean | 3 | 75.280 | 80.203 | -4.923 | -14.920 | 8.230 |  | A |
| S3 banquet food poisoning | time_critical_response_mean | 3 | 75.667 | 48.527 | 27.140 | 15.750 | 33.000 |  | B |
| S3 banquet food poisoning | ambulance_utilisation | 3 | 0.899 | 0.914 | -0.015 | -0.052 | 0.007 |  |  |
| S5 two major incidents at once | served_rate | 3 | 0.579 | 0.588 | -0.009 | -0.105 | 0.158 |  | B |
| S5 two major incidents at once | red_in_window_rate | 3 | 0.116 | 0.152 | -0.037 | -0.135 | 0.121 |  | B |
| S5 two major incidents at once | unserved_critical_incidents | 3 | 7.333 | 6.667 | 0.667 | 0.000 | 2.000 |  | B |
| S5 two major incidents at once | capability_match_rate | 3 | 0.930 | 0.763 | 0.167 | 0.132 | 0.184 |  | A |
| S5 two major incidents at once | response_time_mean | 3 | 111.497 | 113.750 | -2.253 | -27.000 | 27.910 |  | A |
| S5 two major incidents at once | time_critical_response_mean | 3 | 41.467 | 61.490 | -20.023 | -40.400 | -7.000 |  | A |
| S5 two major incidents at once | ambulance_utilisation | 3 | 0.914 | 0.928 | -0.014 | -0.083 | 0.056 |  |  |

## Paired difference: MA − B1

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA_mean | B1_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 9 | 0.706 | 0.739 | -0.033 | -0.076 | 0.014 | 0.266 | B |
| all | red_in_window_rate | 9 | 0.297 | 0.356 | -0.059 | -0.121 | -0.002 | 0.109 | B |
| all | unserved_critical_incidents | 9 | 5.667 | 6.111 | -0.444 | -1.667 | 0.667 | 0.727 | A |
| all | capability_match_rate | 9 | 0.880 | 0.825 | 0.055 | -0.009 | 0.114 | 0.164 | A |
| all | response_time_mean | 9 | 73.954 | 89.938 | -15.983 | -44.119 | 4.606 | 0.359 | A |
| all | time_critical_response_mean | 9 | 50.072 | 63.156 | -13.083 | -52.998 | 21.563 | 1.000 | A |
| all | ambulance_utilisation | 9 | 0.888 | 0.901 | -0.013 | -0.054 | 0.024 | 0.820 |  |
| S1 freeway pileup | served_rate | 3 | 0.737 | 0.737 | 0.000 | -0.053 | 0.053 |  | = |
| S1 freeway pileup | red_in_window_rate | 3 | 0.310 | 0.345 | -0.036 | -0.143 | 0.036 |  | B |
| S1 freeway pileup | unserved_critical_incidents | 3 | 4.333 | 4.333 | 0.000 | -1.000 | 1.000 |  | = |
| S1 freeway pileup | capability_match_rate | 3 | 0.825 | 0.702 | 0.123 | 0.053 | 0.211 |  | A |
| S1 freeway pileup | response_time_mean | 3 | 35.087 | 32.583 | 2.503 | -0.580 | 6.920 |  | B |
| S1 freeway pileup | time_critical_response_mean | 3 | 33.083 | 32.850 | 0.233 | -8.800 | 10.750 |  | B |
| S1 freeway pileup | ambulance_utilisation | 3 | 0.851 | 0.851 | 0.000 | -0.130 | 0.080 |  |  |
| S3 banquet food poisoning | served_rate | 3 | 0.802 | 0.875 | -0.073 | -0.125 | -0.031 |  | B |
| S3 banquet food poisoning | red_in_window_rate | 3 | 0.467 | 0.580 | -0.113 | -0.250 | -0.044 |  | B |
| S3 banquet food poisoning | unserved_critical_incidents | 3 | 5.333 | 4.000 | 1.333 | 1.000 | 2.000 |  | B |
| S3 banquet food poisoning | capability_match_rate | 3 | 0.885 | 0.948 | -0.062 | -0.125 | -0.031 |  | B |
| S3 banquet food poisoning | response_time_mean | 3 | 75.280 | 71.590 | 3.690 | -7.390 | 22.690 |  | B |
| S3 banquet food poisoning | time_critical_response_mean | 3 | 75.667 | 40.527 | 35.140 | 16.000 | 70.670 |  | B |
| S3 banquet food poisoning | ambulance_utilisation | 3 | 0.899 | 0.907 | -0.007 | -0.032 | 0.009 |  |  |
| S5 two major incidents at once | served_rate | 3 | 0.579 | 0.605 | -0.026 | -0.105 | 0.105 |  | B |
| S5 two major incidents at once | red_in_window_rate | 3 | 0.116 | 0.142 | -0.027 | -0.097 | 0.081 |  | B |
| S5 two major incidents at once | unserved_critical_incidents | 3 | 7.333 | 10.000 | -2.667 | -4.000 | -1.000 |  | A |
| S5 two major incidents at once | capability_match_rate | 3 | 0.930 | 0.825 | 0.105 | 0.079 | 0.132 |  | A |
| S5 two major incidents at once | response_time_mean | 3 | 111.497 | 165.640 | -54.143 | -118.840 | -5.340 |  | A |
| S5 two major incidents at once | time_critical_response_mean | 3 | 41.467 | 116.090 | -74.623 | -133.670 | 1.000 |  | A |
| S5 two major incidents at once | ambulance_utilisation | 3 | 0.914 | 0.946 | -0.033 | -0.066 | 0.009 |  |  |

## Paired difference: MA-NoNeg − B1

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA-NoNeg_mean | B1_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 9 | 0.626 | 0.739 | -0.113 | -0.200 | -0.037 | 0.039 | B |
| all | red_in_window_rate | 9 | 0.297 | 0.356 | -0.058 | -0.149 | 0.032 | 0.297 | B |
| all | unserved_critical_incidents | 9 | 5.556 | 6.111 | -0.556 | -2.111 | 0.889 | 0.859 | A |
| all | capability_match_rate | 9 | 0.700 | 0.825 | -0.124 | -0.205 | -0.055 | 0.008 | B |
| all | response_time_mean | 9 | 74.132 | 89.938 | -15.806 | -39.982 | 3.735 | 0.652 | A |
| all | time_critical_response_mean | 9 | 45.833 | 63.156 | -17.322 | -48.006 | 6.517 | 0.359 | A |
| all | ambulance_utilisation | 9 | 0.879 | 0.901 | -0.023 | -0.057 | 0.007 | 0.359 |  |
| S1 freeway pileup | served_rate | 3 | 0.456 | 0.737 | -0.281 | -0.316 | -0.263 |  | B |
| S1 freeway pileup | red_in_window_rate | 3 | 0.167 | 0.345 | -0.179 | -0.286 | 0.000 |  | B |
| S1 freeway pileup | unserved_critical_incidents | 3 | 5.333 | 4.333 | 1.000 | 0.000 | 2.000 |  | B |
| S1 freeway pileup | capability_match_rate | 3 | 0.421 | 0.702 | -0.281 | -0.316 | -0.263 |  | B |
| S1 freeway pileup | response_time_mean | 3 | 28.443 | 32.583 | -4.140 | -5.670 | -1.420 |  | A |
| S1 freeway pileup | time_critical_response_mean | 3 | 27.483 | 32.850 | -5.367 | -15.250 | 2.750 |  | A |
| S1 freeway pileup | ambulance_utilisation | 3 | 0.793 | 0.851 | -0.057 | -0.134 | 0.001 |  |  |
| S3 banquet food poisoning | served_rate | 3 | 0.833 | 0.875 | -0.042 | -0.094 | 0.031 |  | B |
| S3 banquet food poisoning | red_in_window_rate | 3 | 0.573 | 0.580 | -0.007 | -0.129 | 0.192 |  | B |
| S3 banquet food poisoning | unserved_critical_incidents | 3 | 4.667 | 4.000 | 0.667 | -1.000 | 2.000 |  | B |
| S3 banquet food poisoning | capability_match_rate | 3 | 0.917 | 0.948 | -0.031 | -0.062 | 0.000 |  | B |
| S3 banquet food poisoning | response_time_mean | 3 | 80.203 | 71.590 | 8.613 | 3.850 | 14.460 |  | B |
| S3 banquet food poisoning | time_critical_response_mean | 3 | 48.527 | 40.527 | 8.000 | -17.000 | 38.000 |  | B |
| S3 banquet food poisoning | ambulance_utilisation | 3 | 0.914 | 0.907 | 0.008 | -0.032 | 0.053 |  |  |
| S5 two major incidents at once | served_rate | 3 | 0.588 | 0.605 | -0.018 | -0.053 | 0.026 |  | B |
| S5 two major incidents at once | red_in_window_rate | 3 | 0.152 | 0.142 | 0.010 | -0.040 | 0.070 |  | A |
| S5 two major incidents at once | unserved_critical_incidents | 3 | 6.667 | 10.000 | -3.333 | -5.000 | -1.000 |  | A |
| S5 two major incidents at once | capability_match_rate | 3 | 0.763 | 0.825 | -0.061 | -0.105 | -0.026 |  | B |
| S5 two major incidents at once | response_time_mean | 3 | 113.750 | 165.640 | -51.890 | -91.840 | 2.330 |  | A |
| S5 two major incidents at once | time_critical_response_mean | 3 | 61.490 | 116.090 | -54.600 | -121.000 | 8.000 |  | A |
| S5 two major incidents at once | ambulance_utilisation | 3 | 0.928 | 0.946 | -0.018 | -0.047 | 0.017 |  |  |

## LLM usage per run (mean)

| policy | llm_calls | llm_failures | fallbacks | partial_fills | fallback_rate | tokens_in | tokens_out | agent_escalations | mean_rounds | messages | wall_seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MA | 206.444 | 0.222 | 0.222 | 3.000 | 0.001 | 152889.778 | 21533.778 | 15.000 | 2.140 | 281.333 | 340.344 |
| MA-NoNeg | 124.444 | 0.333 | 0.333 | 3.111 | 0.003 | 92148.111 | 14230.333 | 0.000 | 1.000 | 173.889 | 226.733 |

## Transport decisions vs references

`changed_by_negotiation` = final destination differs from Dispatch's first proposal.

| policy | decisions | same_as_rule | same_as_nearest | changed_by_negotiation |
|---|---|---|---|---|
| MA | 209 | 0.632 | 0.550 | 0.517 |
| MA-NoNeg | 207 | 0.700 | 0.768 | 0.464 |
