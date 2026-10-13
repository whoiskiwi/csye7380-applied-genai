# Before vs after examples (base vs v2_epoch2)

## [basic SQL] What is the sum of sales revenue from 'Men's' garments in 'Canada'?

**Gold SQL:** `SELECT SUM(revenue) FROM canada_sales_revenue WHERE garment_type = 'Men''s';`

**Before (base):**

~~~
To find the total sales revenue for 'Men's' garments sold in Canada, we can use the following SQL query:

```sql
SELECT SUM(revenue) AS Total_Revenue
FROM canada_sales_revenue
WHERE garment_type = 'Men\'s';
```

This query works as follows:
- It selects the sum of the `revenue` column (`SUM(revenue)`).
- The alias `Total_Revenue` is given to this result.
- It filters the records where the `garment_type` is 'Men\'s'.
- The result gives the total sales revenue for all 'Men's' garments sold in Canada.
~~~

**After (v2_epoch2):**

~~~
```sql
SELECT SUM(revenue) FROM canada_sales_revenue WHERE garment_type = 'Men''s';
```

Explanation: This query calculates the total sales revenue for Men's garments sold in Canada by filtering the data based on the garment type and calculating the sum of revenues.
~~~

## [single join] What is the total number of fish for each location, grouped by location, from the 'fish_stock' and 'sustainable_seafood' tables?

**Gold SQL:** `SELECT f.location, SUM(f.num_fish + s.num_fish) FROM fish_stock f FULL OUTER JOIN sustainable_seafood s ON f.location = s.location GROUP BY f.location;`

**Before (base):**

~~~
```sql
SELECT location, SUM(num_fish) AS total_fish
FROM fish_stock
UNION ALL
SELECT location, SUM(num_fish)
FROM sustainable_seafood
GROUP BY location;
```

**Explanation:**
This query combines data from both `fish_stock` and `sustainable_seafood` tables to calculate the total number of fish for each location. It uses the `SUM()` function to add up the numbers of fish in each table and groups the results by location using the `GROUP BY` clause. The `UNION ALL` operator ensures that all locations are included in the final result set, even if they appear only once in one of the tables.
~~~

**After (v2_epoch2):**

~~~
```sql
SELECT f.location, SUM(f.num_fish + ss.num_fish) as total_fish FROM fish_stock f FULL OUTER JOIN sustainable_seafood ss ON f.location = ss.location GROUP BY f.location;
```

Explanation: This query performs a full outer join on the 'fish_stock' and 'sustainable_seafood' tables based on their common column 'location'. It calculates the sum of the 'num_fish' values in both tables for each location using the SUM function and groups them by location.
~~~

## [aggregation] What was the average energy efficiency score for each region in 2021?

**Gold SQL:** `SELECT region, AVG(score) FROM energy_efficiency WHERE year = 2021 GROUP BY region;`

**Before (base):**

~~~
To find the average energy efficiency score for each region in 2021, we can use the following SQL query:

```sql
SELECT region, AVG(score) AS avg_score
FROM energy_efficiency
WHERE year = 2021;
```

This query works as follows:
- It selects the `region` column and calculates the average of the `score` column (`AVG(score)`).
- The `WHERE` clause filters the results to only include rows where the `year` is 2021.
- The result includes both the region names and their corresponding average scores.
~~~

**After (v2_epoch2):**

~~~
```sql
SELECT region, AVG(score) as avg_score FROM energy_efficiency WHERE year = 2021 GROUP BY region;
```

Explanation: This query calculates the average energy efficiency score for each region in 2021 by grouping the data by 'region' column and calculating the average of the 'score' column values where the 'year' is equal to 2021.
~~~

## [basic SQL] What are the combined sales figures for 'Lipitor' in the US and 'Crestor' in Canada?

**Gold SQL:** `SELECT SUM(revenue) FROM drug_sales WHERE (drug_name = 'Lipitor' AND region = 'US') OR (drug_name = 'Crestor' AND region = 'Canada');`

**Before (base):**

~~~
To find the combined sales figures for 'Lipitor' in the US and 'Crestor' in Canada, we can use the following SQL query:

```sql
SELECT SUM(revenue)
FROM drug_sales
WHERE drug_name IN ('Lipitor', 'Crestor')
AND region = 'US';
```

This query works as follows:
1. It selects the sum of the `revenue` column.
2. It filters the results to include only rows where the `drug_name` is either 'Lipitor' or 'Crestor'.
3. It further narrows down the selection by ensuring that the `region` is 'US'.

The result will be the total revenue from these two drugs sold in the United States.
~~~

**After (v2_epoch2):**

~~~
```sql
SELECT SUM(revenue) FROM drug_sales WHERE drug_name IN ('Lipitor', 'Crestor') AND region IN ('US', 'Canada');
```

Explanation: This query calculates the combined sales figures for 'Lipitor' in the US and 'Crestor' in Canada by summing up their respective revenues.
~~~

## [aggregation] What is the distribution of biotech startup funding sources?

**Gold SQL:** `SELECT funding_source_type, COUNT(*) FROM funding_sources GROUP BY funding_source_type`

**Before (base):**

~~~
To determine the distribution of biotech startup funding sources, we can use the following SQL query:

```sql
SELECT 
    funding_source_type,
    COUNT(*) AS total_funding_sources
FROM 
    funding_sources
WHERE 
    funding_source_type LIKE '%biotech%'
GROUP BY 
    funding_source_type;
```

This query works as follows:
- It selects `funding_source_type` from the `funding_sources` table.
- It counts the number of rows for each unique `funding_source_type`.
- The `LIKE '%biotech%'` condition filters out only those records where the `funding_source_type` contains "biotech".
- Finally, it groups these results by `funding_source_type` to show how many startups receive funding from each type.

The result will provide a clear breakdown of which types of funding sources are most commonly used in biotech startups.
~~~

**After (v2_epoch2):**

~~~
```sql
SELECT funding_source_type, COUNT(*) as num_funding_sources FROM funding_sources GROUP BY funding_source_type;
```

Explanation: This query groups the records in the funding_sources table by the funding_source_type column and calculates the count of rows for each group using the COUNT() function.
~~~
