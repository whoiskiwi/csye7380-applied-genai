# Before vs after examples

## [aggregation] What is the total retail price of sustainable fabrics by country of origin?

**Gold SQL:** `SELECT country_of_origin, SUM(retail_price) as total_retail_price FROM products GROUP BY country_of_origin;`

**Before (base):**

~~~
To find the total retail price of sustainable fabrics by country of origin, we need to sum up the prices for products where the `country_of_origin` is either "India" or "France". Here's the SQL query to achieve this:

```sql
SELECT SUM(retail_price), country_of_origin
FROM products
WHERE country_of_origin IN ('India', 'France')
GROUP BY country_of_origin;
```

This query works as follows:
- It selects the sum of `retail_price` and the `country_of_origin`.
- It filters the rows where `country_of_origin` is either "India" or "France".
- It groups the results by `country_of_origin` to get the total price per country.
- The `SUM()` function calculates the total retail price across all matching countries.

The result will show each country along with its corresponding total retail price of sustainable fabrics.
~~~

**After (fine-tuned):**

~~~
```sql
SELECT country_of_origin, SUM(retail_price) FROM products GROUP BY country_of_origin;
```

Explanation: This query calculates the total retail price of sustainable fabrics by country of origin by grouping the records based on the country_of_origin column and summing up the retail_price for each group.
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

**After (fine-tuned):**

~~~
```sql
SELECT f.location, SUM(f.num_fish + ss.num_fish) as total_fish FROM fish_stock f JOIN sustainable_seafood ss ON f.location = ss.location GROUP BY f.location;
```

Explanation: This query joins the 'fish_stock' and 'sustainable_seafood' tables on the 'location' column, calculates the sum of the 'num_fish' values in both tables for each location, and groups the results by location.
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

**After (fine-tuned):**

~~~
```sql
SELECT region, AVG(score) as avg_score FROM energy_efficiency WHERE year = 2021 GROUP BY region;
```

Explanation: This query calculates the average energy efficiency score for each region in 2021 by grouping the data based on the 'region' column and calculating the mean of the 'score' column for each group.
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

**After (fine-tuned):**

~~~
```sql
SELECT SUM(revenue) FROM drug_sales WHERE drug_name IN ('Lipitor', 'Crestor') AND region IN ('US', 'Canada');
```

Explanation: This query calculates the total revenue from Lipitor sold in the US and Crestor sold in Canada by summing up the revenue values where the drug name is either 'Lipitor' or 'Crestor' and the region is either 'US' or 'Canada'.
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

**After (fine-tuned):**

~~~
```sql
SELECT funding_source_type, COUNT(*) as total_funding FROM funding_sources GROUP BY funding_source_type;
```

Explanation: This query groups the records in the funding_sources table by the funding_source_type column and calculates the count for each group to determine the distribution of biotech startup funding sources.
~~~
