# Results (mvp_v2)

3 scenarios × 5 seeds; every method runs on the same generated instances. MA and MA-NoNeg use the same local model and prompts; the only difference is negotiation.

## Mean per scenario

**Served in window (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.463 | 0.768 | 0.758 | 0.726 |
| S3 banquet food poisoning | 0.838 | 0.906 | 0.881 | 0.888 |
| S5 two major incidents at once | 0.505 | 0.621 | 0.589 | 0.579 |

**Red patients in window (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.226 | 0.384 | 0.363 | 0.248 |
| S3 banquet food poisoning | 0.577 | 0.662 | 0.588 | 0.636 |
| S5 two major incidents at once | 0.106 | 0.190 | 0.119 | 0.099 |

**Unserved critical incidents**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 4.400 | 3.600 | 3.600 | 4.400 |
| S3 banquet food poisoning | 3.200 | 3.000 | 3.800 | 3.600 |
| S5 two major incidents at once | 9.600 | 9.000 | 7.000 | 7.000 |

**Capability match (share)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.421 | 0.684 | 0.916 | 0.874 |
| S3 banquet food poisoning | 0.856 | 0.931 | 0.944 | 0.938 |
| S5 two major incidents at once | 0.763 | 0.826 | 0.921 | 0.911 |

**Mean response time (min)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 27.216 | 33.482 | 43.416 | 43.316 |
| S3 banquet food poisoning | 63.108 | 65.954 | 77.848 | 76.168 |
| S5 two major incidents at once | 176.734 | 165.400 | 101.900 | 100.984 |

**Cardiac arrest / stroke response (min)**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 27.996 | 31.444 | 39.596 | 38.764 |
| S3 banquet food poisoning | 71.366 | 47.766 | 62.534 | 55.050 |
| S5 two major incidents at once | 195.654 | 90.804 | 47.560 | 40.600 |

**Ambulance utilisation**

| scenario | B0 | B1 | MA-NoNeg | MA |
|---|---|---|---|---|
| S1 freeway pileup | 0.852 | 0.864 | 0.856 | 0.845 |
| S3 banquet food poisoning | 0.882 | 0.902 | 0.907 | 0.883 |
| S5 two major incidents at once | 0.922 | 0.934 | 0.914 | 0.938 |

## Paired difference: MA − MA-NoNeg

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA_mean | MA-NoNeg_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 15 | 0.731 | 0.743 | -0.012 | -0.039 | 0.016 | 0.507 | B |
| all | red_in_window_rate | 15 | 0.328 | 0.356 | -0.029 | -0.110 | 0.051 | 0.308 | B |
| all | unserved_critical_incidents | 15 | 5.000 | 4.800 | 0.200 | -0.533 | 0.933 | 0.587 | B |
| all | capability_match_rate | 15 | 0.907 | 0.927 | -0.020 | -0.039 | -0.001 | 0.109 | B |
| all | response_time_mean | 15 | 73.489 | 74.388 | -0.899 | -4.495 | 3.034 | 0.470 | A |
| all | time_critical_response_mean | 15 | 44.805 | 49.897 | -5.092 | -10.916 | -0.231 | 0.059 | A |
| all | ambulance_utilisation | 15 | 0.888 | 0.892 | -0.004 | -0.020 | 0.013 | 0.720 |  |
| S1 freeway pileup | served_rate | 5 | 0.726 | 0.758 | -0.032 | -0.074 | 0.011 | 0.625 | B |
| S1 freeway pileup | red_in_window_rate | 5 | 0.248 | 0.363 | -0.115 | -0.265 | 0.029 | 0.250 | B |
| S1 freeway pileup | unserved_critical_incidents | 5 | 4.400 | 3.600 | 0.800 | -0.200 | 2.000 | 0.500 | B |
| S1 freeway pileup | capability_match_rate | 5 | 0.874 | 0.916 | -0.042 | -0.074 | -0.011 | 0.250 | B |
| S1 freeway pileup | response_time_mean | 5 | 43.316 | 43.416 | -0.100 | -0.932 | 0.766 | 1.000 | A |
| S1 freeway pileup | time_critical_response_mean | 5 | 38.764 | 39.596 | -0.832 | -3.600 | 1.168 | 0.750 | A |
| S1 freeway pileup | ambulance_utilisation | 5 | 0.845 | 0.856 | -0.011 | -0.035 | 0.013 | 0.812 |  |
| S3 banquet food poisoning | served_rate | 5 | 0.888 | 0.881 | 0.006 | -0.037 | 0.056 | 1.000 | A |
| S3 banquet food poisoning | red_in_window_rate | 5 | 0.636 | 0.588 | 0.048 | -0.064 | 0.200 | 0.875 | A |
| S3 banquet food poisoning | unserved_critical_incidents | 5 | 3.600 | 3.800 | -0.200 | -1.800 | 1.200 | 1.000 | A |
| S3 banquet food poisoning | capability_match_rate | 5 | 0.938 | 0.944 | -0.006 | -0.038 | 0.031 | 1.000 | B |
| S3 banquet food poisoning | response_time_mean | 5 | 76.168 | 77.848 | -1.680 | -8.264 | 7.566 | 0.625 | A |
| S3 banquet food poisoning | time_critical_response_mean | 5 | 55.050 | 62.534 | -7.484 | -21.850 | 4.666 | 0.438 | A |
| S3 banquet food poisoning | ambulance_utilisation | 5 | 0.883 | 0.907 | -0.024 | -0.045 | -0.009 | 0.062 |  |
| S5 two major incidents at once | served_rate | 5 | 0.579 | 0.589 | -0.011 | -0.053 | 0.037 | 0.625 | B |
| S5 two major incidents at once | red_in_window_rate | 5 | 0.099 | 0.119 | -0.020 | -0.064 | 0.023 | 0.375 | B |
| S5 two major incidents at once | unserved_critical_incidents | 5 | 7.000 | 7.000 | 0.000 | -1.000 | 0.800 | 1.000 | = |
| S5 two major incidents at once | capability_match_rate | 5 | 0.911 | 0.921 | -0.010 | -0.021 | 0.001 | 0.500 | B |
| S5 two major incidents at once | response_time_mean | 5 | 100.984 | 101.900 | -0.916 | -8.364 | 6.532 | 0.875 | A |
| S5 two major incidents at once | time_critical_response_mean | 5 | 40.600 | 47.560 | -6.960 | -15.360 | 0.000 | 0.500 | A |
| S5 two major incidents at once | ambulance_utilisation | 5 | 0.938 | 0.914 | 0.024 | 0.005 | 0.048 | 0.125 |  |

## Paired difference: MA − B1

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA_mean | B1_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 15 | 0.731 | 0.765 | -0.034 | -0.063 | -0.008 | 0.039 | B |
| all | red_in_window_rate | 15 | 0.328 | 0.412 | -0.085 | -0.161 | -0.008 | 0.055 | B |
| all | unserved_critical_incidents | 15 | 5.000 | 5.200 | -0.200 | -1.133 | 0.667 | 0.748 | A |
| all | capability_match_rate | 15 | 0.907 | 0.814 | 0.093 | 0.044 | 0.145 | 0.005 | A |
| all | response_time_mean | 15 | 73.489 | 88.279 | -14.789 | -36.579 | 4.340 | 0.934 | A |
| all | time_critical_response_mean | 15 | 44.805 | 56.671 | -11.867 | -36.145 | 6.714 | 0.955 | A |
| all | ambulance_utilisation | 15 | 0.888 | 0.900 | -0.011 | -0.029 | 0.008 | 0.330 |  |
| S1 freeway pileup | served_rate | 5 | 0.726 | 0.768 | -0.042 | -0.105 | 0.011 | 0.625 | B |
| S1 freeway pileup | red_in_window_rate | 5 | 0.248 | 0.384 | -0.136 | -0.290 | 0.029 | 0.250 | B |
| S1 freeway pileup | unserved_critical_incidents | 5 | 4.400 | 3.600 | 0.800 | -0.200 | 2.000 | 0.500 | B |
| S1 freeway pileup | capability_match_rate | 5 | 0.874 | 0.684 | 0.190 | 0.116 | 0.263 | 0.062 | A |
| S1 freeway pileup | response_time_mean | 5 | 43.316 | 33.482 | 9.834 | 6.114 | 13.736 | 0.062 | B |
| S1 freeway pileup | time_critical_response_mean | 5 | 38.764 | 31.444 | 7.320 | -0.280 | 13.540 | 0.188 | B |
| S1 freeway pileup | ambulance_utilisation | 5 | 0.845 | 0.864 | -0.019 | -0.043 | 0.012 | 0.438 |  |
| S3 banquet food poisoning | served_rate | 5 | 0.888 | 0.906 | -0.019 | -0.044 | 0.013 | 0.500 | B |
| S3 banquet food poisoning | red_in_window_rate | 5 | 0.636 | 0.662 | -0.027 | -0.140 | 0.096 | 1.000 | B |
| S3 banquet food poisoning | unserved_critical_incidents | 5 | 3.600 | 3.000 | 0.600 | -0.400 | 1.400 | 0.500 | B |
| S3 banquet food poisoning | capability_match_rate | 5 | 0.938 | 0.931 | 0.006 | -0.025 | 0.050 | 1.000 | A |
| S3 banquet food poisoning | response_time_mean | 5 | 76.168 | 65.954 | 10.214 | 1.754 | 18.520 | 0.188 | B |
| S3 banquet food poisoning | time_critical_response_mean | 5 | 55.050 | 47.766 | 7.284 | -8.400 | 22.260 | 0.500 | B |
| S3 banquet food poisoning | ambulance_utilisation | 5 | 0.883 | 0.902 | -0.019 | -0.044 | 0.010 | 0.312 |  |
| S5 two major incidents at once | served_rate | 5 | 0.579 | 0.621 | -0.042 | -0.084 | -0.005 | 0.188 | B |
| S5 two major incidents at once | red_in_window_rate | 5 | 0.099 | 0.190 | -0.091 | -0.178 | -0.029 | 0.062 | B |
| S5 two major incidents at once | unserved_critical_incidents | 5 | 7.000 | 9.000 | -2.000 | -3.200 | -0.800 | 0.125 | A |
| S5 two major incidents at once | capability_match_rate | 5 | 0.911 | 0.826 | 0.084 | 0.042 | 0.126 | 0.125 | A |
| S5 two major incidents at once | response_time_mean | 5 | 100.984 | 165.400 | -64.416 | -90.982 | -30.268 | 0.062 | A |
| S5 two major incidents at once | time_critical_response_mean | 5 | 40.600 | 90.804 | -50.204 | -95.922 | -5.550 | 0.312 | A |
| S5 two major incidents at once | ambulance_utilisation | 5 | 0.938 | 0.934 | 0.004 | -0.034 | 0.041 | 0.812 |  |

## Paired difference: MA-NoNeg − B1

Positive `diff_mean` means A is higher. 95 % CI by bootstrap over (scenario, seed) pairs; Wilcoxon signed-rank p-value (n is small, so treat it as indicative).

| group | metric | n | MA-NoNeg_mean | B1_mean | diff_mean | ci95_low | ci95_high | wilcoxon_p | better |
|---|---|---|---|---|---|---|---|---|---|
| all | served_rate | 15 | 0.743 | 0.765 | -0.022 | -0.041 | -0.004 | 0.044 | B |
| all | red_in_window_rate | 15 | 0.356 | 0.412 | -0.056 | -0.087 | -0.027 | 0.005 | B |
| all | unserved_critical_incidents | 15 | 4.800 | 5.200 | -0.400 | -1.200 | 0.268 | 0.262 | A |
| all | capability_match_rate | 15 | 0.927 | 0.814 | 0.113 | 0.059 | 0.170 | 0.005 | A |
| all | response_time_mean | 15 | 74.388 | 88.279 | -13.891 | -35.943 | 5.584 | 0.639 | A |
| all | time_critical_response_mean | 15 | 49.897 | 56.671 | -6.775 | -28.581 | 11.929 | 0.842 | A |
| all | ambulance_utilisation | 15 | 0.892 | 0.900 | -0.008 | -0.025 | 0.008 | 0.532 |  |
| S1 freeway pileup | served_rate | 5 | 0.758 | 0.768 | -0.011 | -0.032 | 0.000 | 1.000 | B |
| S1 freeway pileup | red_in_window_rate | 5 | 0.363 | 0.384 | -0.021 | -0.064 | 0.000 | 1.000 | B |
| S1 freeway pileup | unserved_critical_incidents | 5 | 3.600 | 3.600 | 0.000 | 0.000 | 0.000 |  | = |
| S1 freeway pileup | capability_match_rate | 5 | 0.916 | 0.684 | 0.232 | 0.168 | 0.284 | 0.062 | A |
| S1 freeway pileup | response_time_mean | 5 | 43.416 | 33.482 | 9.934 | 5.894 | 14.098 | 0.062 | B |
| S1 freeway pileup | time_critical_response_mean | 5 | 39.596 | 31.444 | 8.152 | -0.086 | 14.082 | 0.125 | B |
| S1 freeway pileup | ambulance_utilisation | 5 | 0.856 | 0.864 | -0.008 | -0.040 | 0.015 | 0.812 |  |
| S3 banquet food poisoning | served_rate | 5 | 0.881 | 0.906 | -0.025 | -0.044 | -0.006 | 0.250 | B |
| S3 banquet food poisoning | red_in_window_rate | 5 | 0.588 | 0.662 | -0.075 | -0.133 | -0.023 | 0.125 | B |
| S3 banquet food poisoning | unserved_critical_incidents | 5 | 3.800 | 3.000 | 0.800 | 0.200 | 1.400 | 0.250 | B |
| S3 banquet food poisoning | capability_match_rate | 5 | 0.944 | 0.931 | 0.013 | -0.031 | 0.056 | 0.750 | A |
| S3 banquet food poisoning | response_time_mean | 5 | 77.848 | 65.954 | 11.894 | -2.166 | 25.924 | 0.312 | B |
| S3 banquet food poisoning | time_critical_response_mean | 5 | 62.534 | 47.766 | 14.768 | -7.800 | 40.968 | 0.625 | B |
| S3 banquet food poisoning | ambulance_utilisation | 5 | 0.907 | 0.902 | 0.005 | -0.020 | 0.029 | 0.625 |  |
| S5 two major incidents at once | served_rate | 5 | 0.589 | 0.621 | -0.032 | -0.074 | 0.016 | 0.375 | B |
| S5 two major incidents at once | red_in_window_rate | 5 | 0.119 | 0.190 | -0.071 | -0.132 | -0.029 | 0.062 | B |
| S5 two major incidents at once | unserved_critical_incidents | 5 | 7.000 | 9.000 | -2.000 | -3.200 | -0.800 | 0.125 | A |
| S5 two major incidents at once | capability_match_rate | 5 | 0.921 | 0.826 | 0.094 | 0.042 | 0.147 | 0.125 | A |
| S5 two major incidents at once | response_time_mean | 5 | 101.900 | 165.400 | -63.500 | -92.182 | -34.684 | 0.062 | A |
| S5 two major incidents at once | time_critical_response_mean | 5 | 47.560 | 90.804 | -43.244 | -80.938 | -5.550 | 0.312 | A |
| S5 two major incidents at once | ambulance_utilisation | 5 | 0.914 | 0.934 | -0.020 | -0.047 | 0.006 | 0.312 |  |

## LLM usage per run (mean)

| policy | llm_calls | llm_failures | fallbacks | partial_fills | fallback_rate | tokens_in | tokens_out | agent_escalations | mean_rounds | rule_retries | rule_violations_kept | accept_mismatch | redirects | messages | wall_seconds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MA | 170.467 | 1.200 | 1.200 | 2.333 | 0.006 | 130931.600 | 18497.200 | 4.267 | 1.123 | 22.600 | 5.867 | 3.933 | 0.000 | 211.933 | 241.447 |
| MA-NoNeg | 143.067 | 1.133 | 1.133 | 2.867 | 0.007 | 110296.867 | 15729.200 | 0.000 | 1.000 | 13.667 | 3.533 | 3.133 | 0.000 | 183.600 | 228.373 |

## Role-rule checks

An agent that breaks a rule of its own prompt is told which rule and answers once more; the second answer is used either way. `fixed_by_retry` = share of violations the second answer corrected.

| policy | agent | violations | fixed_by_retry |
|---|---|---|---|
| MA | Dispatch | 84 | 0.786 |
| MA | HospitalCoordination | 254 | 0.732 |
| MA | ResourceAllocation | 1 | 0.000 |
| MA-NoNeg | HospitalCoordination | 205 | 0.751 |

## Transport decisions vs references

`changed_by_negotiation` = final destination differs from Dispatch's first proposal.

| policy | decisions | same_as_rule | same_as_nearest | changed_by_negotiation |
|---|---|---|---|---|
| MA | 350 | 0.706 | 0.611 | 0.300 |
| MA-NoNeg | 349 | 0.613 | 0.510 | 0.169 |
