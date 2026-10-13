# Full comparison: Base vs v1 vs v2

Every number is recomputed by this script from each version's saved prediction files. All four models were scored on the **same 300 test questions** (`data/test.jsonl`: from Gretel's official test split, SELECT queries whose gold SQL executes in SQLite and returns rows).

## 1. How the two versions differ

Identical in both: model Qwen/Qwen2.5-1.5B-Instruct, LoRA r=16 / alpha=32, learning rate 0.0002, effective batch 16, same evaluation code.

|  | v1 | v2 |
|---|---|---|
| Training data | raw data (includes MySQL/Postgres-only syntax) | cleaned data (SQLite-runnable rows only) |
| Training examples | 10000 | 10000 |
| Epochs | 1 | 2 |
| Steps | 625 | 1250 |
| Training time (L4) | 32 min | 61 min |
| Final validation loss | 0.354 | 0.343 |
| Final training loss | 0.331 | 0.287 |

## 2. Overall metrics

|  | Execution accuracy | Executable SQL | Exact match | Format compliance | Explanation ROUGE-L |
|---|---|---|---|---|---|
| Base (no fine-tuning) | 64.3% | 94.3% | 14.3% | 34.3% | 0.369 |
| v1: raw data, 1 epoch | 67.3% | 91.3% | 32.0% | 100.0% | 0.539 |
| v2: cleaned data, 1 epoch | 73.3% | 96.7% | 33.3% | 100.0% | 0.557 |
| v2: cleaned data, 2 epochs | 73.7% | 97.3% | 36.0% | 100.0% | 0.548 |

## 3. Gain from each step

Fixed = wrong before, right after; broken = right before, wrong after. The exact McNemar test uses only these two counts to judge whether the difference could be chance.

|  | Exec. accuracy change (pts) | Executable change (pts) | Fixed | Broken | McNemar p | Significant (p<0.05) |
|---|---|---|---|---|---|---|
| Fine-tuning on raw data (Base → v1) | +3.0 | -3.0 | 31 | 22 | 0.2717 | no |
| Data cleaning (v1 → v2 epoch 1) | +6.0 | +5.3 | 23 | 5 | 0.0009 | yes |
| Extra epoch (v2 epoch 1 → epoch 2) | +0.3 | +0.7 | 4 | 3 | 1.0000 | no |
| Overall (Base → v2 epoch 2) | +9.3 | +3.0 | 40 | 12 | 0.0001 | yes |
| v1 → v2 final | +6.3 | +6.0 | 23 | 4 | 0.0003 | yes |

## 4. Error breakdown (out of 300)

|  | Wrong answers | Non-executable SQL | Uses MySQL/Postgres-only syntax |
|---|---|---|---|
| Base (no fine-tuning) | 107 | 17 | 2 |
| v1: raw data, 1 epoch | 98 | 26 | 11 |
| v2: cleaned data, 1 epoch | 80 | 10 | 0 |
| v2: cleaned data, 2 epochs | 79 | 8 | 0 |

## 5. By SQL complexity (number of test questions in parentheses)

|  | Base (no fine-tuning) | v1: raw data, 1 epoch | v2: cleaned data, 1 epoch | v2: cleaned data, 2 epochs | v1 → v2 change |
|---|---|---|---|---|---|
| basic SQL (162) | 73.5% | 77.8% | 82.7% | 84.6% | +6.8 |
| aggregation (66) | 48.5% | 53.0% | 62.1% | 59.1% | +6.1 |
| single join (40) | 65.0% | 65.0% | 72.5% | 75.0% | +10.0 |
| subqueries (14) | 71.4% | 64.3% | 71.4% | 71.4% | +7.1 |
| window functions (10) | 20.0% | 0.0% | 0.0% | 0.0% | +0.0 |
| multiple_joins (5) | 60.0% | 80.0% | 80.0% | 80.0% | +0.0 |
| set operations (3) | 33.3% | 66.7% | 66.7% | 33.3% | -33.3 |

In categories with fewer than 15 questions (subqueries, window functions, multiple joins, set operations), one question moves the score by 7–33 points, so read them as trends only.

Training examples per complexity (cleaning removed some complex queries such as window functions and CTEs):

|  | v1 train | v2 train |
|---|---|---|
| basic SQL | 4847 | 5341 |
| aggregation | 2202 | 2186 |
| single join | 1493 | 1316 |
| subqueries | 672 | 528 |
| window functions | 360 | 310 |
| multiple_joins | 294 | 215 |
| set operations | 105 | 102 |
| CTEs | 27 | 2 |

## 6. Loss curves

![loss](loss_v1_vs_v2.png)

- v1 and v2 use different validation sets (each drawn from its own training data), so compare the shapes of the two validation curves, not their absolute values.
- After v2's first epoch, training loss keeps falling (0.355 → 0.287) while validation loss barely moves (0.349 → 0.343): mild overfitting, so the second epoch adds little.

Other charts: `v2/results/all_versions_metrics.png`, `v2/results/exec_accuracy_by_complexity.png`

## 7. Examples: v1 vs v2

### v1 used syntax SQLite does not support, v2 fixed it (6 questions, showing 4)

**[single join] What is the total donation amount by each program in Q1 2022?**

~~~sql
-- gold
SELECT p.pname, SUM(d.amount) as total_donation FROM donation d JOIN program p ON d.pid = p.pid WHERE d.donation_date BETWEEN '2022-01-01' AND '2022-03-31' GROUP BY p.pname;
-- v1
SELECT p.pname, SUM(d.amount) as total_donation FROM program p JOIN donation d ON p.pid = d.pid WHERE YEAR(d.donation_date) = 2022 AND QUARTER(d.donation_date) = 1 GROUP BY p.pname;
-- v2
SELECT p.pname, SUM(d.amount) as total_donation FROM program p JOIN donation d ON p.pid = d.pid WHERE d.donation_date BETWEEN '2022-01-01' AND '2022-03-31' GROUP BY p.pname;
~~~

**[aggregation] What is the total number of emergency incidents by type in 2022 in Portland?"**

~~~sql
-- gold
SELECT type, COUNT(*) as total FROM emergency_incidents WHERE city = 'Portland' AND incident_date >= '2022-01-01' AND incident_date < '2023-01-01' GROUP BY type;
-- v1
SELECT type, COUNT(*) as num_incidents FROM emergency_incidents WHERE city = 'Portland' AND YEAR(incident_date) = 2022 GROUP BY type;
-- v2
SELECT e.type, COUNT(*) as num_incidents FROM emergency_incidents e WHERE e.city = 'Portland' AND e.incident_date BETWEEN '2022-01-01' AND '2022-12-31' GROUP BY e.type;
~~~

**[basic SQL] Obtain the total number of policies issued in 'Q2 2021'**

~~~sql
-- gold
SELECT COUNT(*) FROM policies WHERE issue_date BETWEEN '2021-04-01' AND '2021-06-30';
-- v1
SELECT COUNT(*) FROM policies WHERE EXTRACT(QUARTER FROM issue_date) = 2 AND EXTRACT(YEAR FROM issue_date) = 2021;
-- v2
SELECT COUNT(*) FROM policies WHERE issue_date BETWEEN '2021-04-01' AND '2021-06-30';
~~~

**[aggregation] List the top 5 countries with the highest average temperature in July.**

~~~sql
-- gold
SELECT country, AVG(temperature) as Avg_Temperature FROM WeatherData WHERE date BETWEEN '2022-07-01' AND '2022-07-31' GROUP BY country ORDER BY Avg_Temperature DESC LIMIT 5;
-- v1
SELECT country, AVG(temperature) as avg_temp FROM WeatherData WHERE EXTRACT(MONTH FROM date) = 7 GROUP BY country ORDER BY avg_temp DESC LIMIT 5;
-- v2
SELECT country, AVG(temperature) as avg_temp FROM WeatherData WHERE date >= '2022-07-01' AND date < '2022-08-01' GROUP BY country ORDER BY avg_temp DESC LIMIT 5;
~~~

### v1 had a logic error, v2 fixed it (17 questions, showing 3)

**[basic SQL] What is the difference in total points scored between the home and away games for each team in the 2020 baseball season?**

~~~sql
-- gold
SELECT team_name, (points_home - points_away) as diff FROM baseball_season;
-- v1
SELECT team_name, SUM(points_home - points_away) as point_difference FROM baseball_season WHERE year = 2020 GROUP BY team_name;
-- v2
SELECT team_name, SUM(points_home - points_away) as point_difference FROM baseball_season GROUP BY team_name;
~~~

**[aggregation] What is the distribution of users by age group for each virtual tour?**

~~~sql
-- gold
SELECT tour_id, age_group, COUNT(*) as user_count FROM virtual_tour_users GROUP BY tour_id, age_group;
-- v1
SELECT v.tour_id, u.age_group, COUNT(*) as user_count FROM virtual_tour_users u JOIN tours t ON u.tour_id = t.id GROUP BY v.tour_id, u.age_group;
-- v2
SELECT tour_id, age_group, COUNT(*) as user_count FROM virtual_tour_users GROUP BY tour_id, age_group;
~~~

**[basic SQL] What is the minimum streaming revenue for users in Japan?**

~~~sql
-- gold
SELECT MIN(revenue) AS min_revenue FROM japan_streaming;
-- v1
SELECT MIN(revenue) FROM japan_streaming WHERE country = 'Japan';
-- v2
SELECT MIN(revenue) FROM japan_streaming;
~~~

### v1 right, v2 wrong (4 questions, showing 4)

**[set operations] What is the total number of police officers and firefighters in the city of New York?**

~~~sql
-- gold
SELECT COUNT(*) FROM nyc_police_officers UNION ALL SELECT COUNT(*) FROM nyc_firefighters;
-- v1
SELECT COUNT(*) FROM nyc_police_officers UNION ALL SELECT COUNT(*) FROM nyc_firefighters;
-- v2
SELECT COUNT(*) FROM nyc_police_officers UNION SELECT COUNT(*) FROM nyc_firefighters;
~~~

**[aggregation] What is the total retail price of sustainable fabrics by country of origin?**

~~~sql
-- gold
SELECT country_of_origin, SUM(retail_price) as total_retail_price FROM products GROUP BY country_of_origin;
-- v1
SELECT country_of_origin, SUM(retail_price) FROM products GROUP BY country_of_origin;
-- v2
SELECT country_of_origin, SUM(retail_price) FROM products WHERE product_name LIKE '%sustainable%' GROUP BY country_of_origin;
~~~

**[aggregation] What percentage of restaurants in each city have a food safety score above 90?**

~~~sql
-- gold
SELECT city, (COUNT(*) FILTER (WHERE score > 90)) * 100.0 / COUNT(*) as percentage FROM food_safety_inspections GROUP BY city;
-- v1
SELECT city, COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS pct_above_90 FROM food_safety_inspections WHERE score > 90 GROUP BY city;
-- v2
SELECT city, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM food_safety_inspections WHERE city = fsi.city), 2) as pct_above_90 FROM food_safety_inspections fsi GROUP BY city;
~~~

**[aggregation] What is the minimum landfill capacity in cubic meters for each country in the European Union?**

~~~sql
-- gold
SELECT country, MIN(landfill_capacity) FROM LandfillCapacity WHERE region = 'European Union' GROUP BY country;
-- v1
SELECT country, MIN(landfill_capacity) FROM LandfillCapacity WHERE region = 'European Union' GROUP BY country;
-- v2
SELECT MIN(l landfill_capacity) FROM LandfillCapacity WHERE region = 'European Union';
~~~

## 8. Conclusions

1. **Fine-tuning works**: execution accuracy 64.3% → 73.7%, format compliance 34.3% → 100%, explanation ROUGE-L 0.37 → 0.55.
2. **Data quality matters more than epochs**: data cleaning (v1 → v2 epoch 1) gives +6.0 points, while an extra epoch gives only +0.3 and doubles training time.
3. v1's problem: about 23% of Gretel's training SQL is MySQL/Postgres dialect, and the model learned syntax SQLite does not support. After cleaning, dialect errors drop 11 → 0.
4. **Limitations**: window functions 0/10 (few training examples, small 1.5B model); execution accuracy requires identical columns, so `SELECT *` or a different column order counts as wrong and real ability is slightly underestimated; with only 300 test questions, small categories are unstable.
5. **Model used in the app**: the v2 epoch-2 adapter (`v2/outputs/qwen2.5-1.5b-instruct-text2sql-lora-v2/final_adapter`).
