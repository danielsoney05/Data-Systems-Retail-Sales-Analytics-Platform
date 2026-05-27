# Data-Systems-Retail-Sales-Analytics-Platform

An E-Commerce Sales Analytics Platform developed for the Data Systems Project, Autumn 2026.

---

## Project Overview

This project implements a retail sales analytics data system using a Flask input application, Google Cloud Storage, Apache Airflow, Google BigQuery, and Looker. The system supports daily order entry through `app.py`, stores new orders as daily CSV files in Google Cloud Storage, loads those files into a BigQuery staging table, and then transforms the staging data into the final Olist dataset for reporting.

Daily pipeline summary:

```text
Customer order in app.py
        ↓
Daily CSV file in Google Cloud Storage
        ↓
Airflow runs move_gcs_bq.py at 23:45
        ↓
BigQuery staging table: olist_staging.stg_daily_orders_raw
        ↓
BigQuery scheduled query runs append_daily_orders.sql at 23:50
        ↓
Final Olist tables: order_payments, orders, order_items
        ↓
Looker dashboard
```

---

## Looker Dashboard Link

The Looker Dashboard link can be found here: [Link to Looker Dashboard](https://datastudio.google.com/u/1/reporting/4ede62e7-54eb-44c6-814b-bdd06b0bd386/page/p_cu0tepgf3d/edit)

---

## How to Run `app.py` via Docker

### Prerequisites

Before running the app, make sure you have:

- Docker installed
- A Google Cloud service account JSON key
- Access to the required Google Cloud Storage bucket
- Access to the required BigQuery dataset and tables
- The repository cloned locally

---

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd Data-Systems-Retail-Sales-Analytics-Platform
```

---

## 2. Add the Google Cloud Key

Place your Google Cloud service account key inside:

```text
input_app/key.json
```

The file should look like a standard Google Cloud service account JSON key.

Example structure:

```text
Data-Systems-Retail-Sales-Analytics-Platform/
├── input_app/
│   ├── app.py
│   ├── key.json
│   └── templates/
├── Dockerfile
└── requirements.txt
```

Important: do not commit `key.json` to GitHub.

Make sure `.gitignore` includes:

```text
input_app/key.json
key.json
*.json
```

---

## 3. Build the Docker Image

From the repository root, run:

```bash
docker build -t olist-input-app .
```

This creates a Docker image called:

```text
olist-input-app
```

---

## 4. Run the Docker Container

Windows PowerShell / CMD:

```bash
docker run -p 5000:5000 ^
-v "%cd%\input_app\key.json:/app/input_app/key.json" ^
--name olist-app ^
olist-input-app
```

Mac/Linux:

```bash
docker run -p 5000:5000 \
-v "$(pwd)/input_app/key.json:/app/input_app/key.json" \
--name olist-app \
olist-input-app
```

This starts the Flask app and maps it to:

```text
http://localhost:5000
```

---

## 5. Open the App

Once the container is running, open:

```text
http://localhost:5000
```

You should be redirected to the login page.

---

## Navigating the Website

### 6. Login

Enter a `customer_id`.

You can use:

- an existing customer ID from the Olist dataset
- a new customer ID to simulate a new user

Existing customers will show profile details and previous orders if they exist in the dataset.

---

### 7. Useful Test Pages

Test BigQuery connection:

```text
http://localhost:5000/test-bq
```

This checks whether the app can query BigQuery.

Test GCS output folder:

```text
http://localhost:5000/test-gcs
```

This checks whether the app can access the Google Cloud Storage output folder.

Debug app config:

```text
http://localhost:5000/debug-config
```

This shows the active bucket, output path, BigQuery project, dataset, and table config.

---

### 8. Where New Orders Are Saved

New orders created through the app are saved to Google Cloud Storage as a daily CSV file.

Example:

```text
gs://olist-494110_bucket/daily_orders/orders_2026-05-06.csv
```

The file name is generated from the current date:

```text
orders_YYYY-MM-DD.csv
```

---

### 9. Stopping the Container

To stop the app:

```bash
docker stop olist-app
```

To remove the container:

```bash
docker rm olist-app
```

---

## Airflow Orchestration

### Airflow Setup

This repository includes an Airflow DAG that runs `pipeline/move_gcs_bq.py` every day at `23:45` in the `Australia/Sydney` timezone.

The DAG file is:

```text
dags/move_gcs_bq_dag.py
```

A Docker Compose setup is also included to run both the Flask app and Airflow together.

### How to Use It

1. Copy `.env.example` to `.env` and fill in your Google Cloud values:

```bash
copy .env.example .env
```

For Mac/Linux:

```bash
cp .env.example .env
```

2. Start the services:

```bash
docker compose up --build
```

3. Access Airflow:

```text
http://localhost:8080
```

4. Access the Flask app:

```text
http://localhost:5000
```

### Notes

- The Airflow service uses `Dockerfile.airflow` to install the project dependencies before running Airflow.
- The DAG executes the Python script from the mounted project root with:

```bash
cd /opt/airflow/project && python pipeline/move_gcs_bq.py
```

- If you want only Airflow and not the Flask app, run:

```bash
docker compose up --build airflow
```

---

## BigQuery Scheduled Query: Append Daily Orders

After Airflow loads the daily CSV file from Google Cloud Storage into the BigQuery staging table, a BigQuery scheduled query is used to transform and append the staged records into the final Olist dataset.

The SQL script is:

```text
pipeline/append_daily_orders.sql
```

### Purpose

The script reads raw daily order data from:

```text
olist-494110.olist_staging.stg_daily_orders_raw
```

and merges the processed records into the completed BigQuery dataset:

```text
olist-494110.olist
```

The script updates these final tables:

```text
olist.order_payments
olist.orders
olist.order_items
```

### Transformation Logic

The scheduled query performs three main merge operations:

1. **Append into `order_payments`**
   - Groups records by `order_id`, `payment_sequential`, `payment_type`, and `payment_installments`
   - Calculates payment value using item price and freight value
   - Uses `MERGE` to update existing records or insert new payment records

2. **Append into `orders`**
   - Reads order-level fields from the staging table
   - Converts string date fields into timestamp fields using `SAFE.PARSE_TIMESTAMP`
   - Uses `MERGE` to update existing records or insert new order records

3. **Append into `order_items`**
   - Reads item-level fields from the staging table
   - Converts `shipping_limit_date` into a timestamp field
   - Uses `MERGE` on `order_id` and `order_item_id` to prevent duplicate order items

### How to Set Up the Scheduled Query in BigQuery

1. Open Google BigQuery in Google Cloud Console.
2. Open the SQL file:

```text
pipeline/append_daily_orders.sql
```

3. Copy the full SQL script into the BigQuery query editor.
4. Click **Schedule**.
5. Configure the scheduled query:

```text
Name: append_daily_orders
Schedule: Daily
Time: 23:50
Time zone: Australia/Sydney
```

6. Save the scheduled query.

### Daily Pipeline Order

The daily operational pipeline should run in this order:

```text
1. Customer places an order in app.py
2. app.py appends the order to the daily CSV file in Google Cloud Storage
3. Airflow runs pipeline/move_gcs_bq.py at 23:45
4. move_gcs_bq.py loads the daily CSV into olist_staging.stg_daily_orders_raw
5. BigQuery scheduled query runs pipeline/append_daily_orders.sql at 23:50
6. The query merges data into order_payments, orders, and order_items
7. Looker dashboard can refresh from the updated Olist dataset
```

### Notes

- The Airflow DAG must run before the BigQuery scheduled query.
- The staging table must contain the latest daily order data before `append_daily_orders.sql` runs.
- The scheduled query uses `MERGE`, so new records are inserted and matching records can be updated.
- If the scheduled query fails, check whether:
  - the staging table exists
  - the staging table contains data
  - the final target tables exist
  - the column names and data types match the SQL script

---

## Common Issues

### `FileNotFoundError: key.json`

The container cannot find the Google Cloud key.

Check that this file exists locally:

```text
input_app/key.json
```

Also check that the Docker volume mount path is correct.

### Airflow DAG Fails

Check that:

- `.env` contains the correct GCP configuration
- the service account has access to GCS and BigQuery
- the daily CSV file exists in the expected GCS path
- the staging dataset and table names match the script configuration

### BigQuery Scheduled Query Fails

Check that:

- `olist_staging.stg_daily_orders_raw` exists
- the staging table has the expected columns
- the final tables exist in the `olist` dataset
- timestamp fields match the expected `%Y-%m-%d %H:%M:%S` format
