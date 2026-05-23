import os
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIG
# =========================================================
PROJECT_ID = os.getenv("BQ_PROJECT")
DATASET_ID = os.getenv("BQ_DATASET_STG")
LOCATION = os.getenv("BQ_LOCATION")
BUCKET_NAME = os.getenv("BUCKET_NAME")

TODAY = datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d")

# Example:
# gs://your-bucket/daily_orders/orders_2026-05-05.csv
GCS_DAILY_ORDERS_FILE = f"gs://{BUCKET_NAME}/daily_orders/orders_{TODAY}.csv"


OVERWRITE = True

# =========================================================
# TABLE MAP
# key   = BigQuery staging table name
# value = GCS CSV path
# =========================================================
TABLES = {
    "stg_daily_orders_raw": GCS_DAILY_ORDERS_FILE
}

# =========================================================
# CLIENT
# =========================================================
client = bigquery.Client(project=PROJECT_ID)

dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

# =========================================================
# SCHEMA
# Keep date/time columns as STRING first.
# Later, dbt can parse them into proper TIMESTAMP columns.
# =========================================================
DAILY_ORDERS_SCHEMA = [
    # Order item fields
    bigquery.SchemaField("order_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("order_item_id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("seller_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("shipping_limit_date", "STRING"),
    bigquery.SchemaField("price", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("freight_value", "FLOAT64"),

    # Order fields
    bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("order_status", "STRING"),
    bigquery.SchemaField("order_purchase_timestamp", "STRING"),
    bigquery.SchemaField("order_approved_at", "STRING"),
    bigquery.SchemaField("order_delivered_carrier_date", "STRING"),
    bigquery.SchemaField("order_delivered_customer_date", "STRING"),
    bigquery.SchemaField("order_estimated_delivery_date", "STRING"),

    # Seller fields
    bigquery.SchemaField("seller_zip_code_prefix", "INT64"),
    bigquery.SchemaField("seller_lat", "FLOAT64"),
    bigquery.SchemaField("seller_lng", "FLOAT64"),
    bigquery.SchemaField("seller_city", "STRING"),
    bigquery.SchemaField("seller_state", "STRING"),

    # Customer fields
    bigquery.SchemaField("customer_unique_id", "STRING"),
    bigquery.SchemaField("customer_zip_code_prefix", "INT64"),
    bigquery.SchemaField("customer_city", "STRING"),
    bigquery.SchemaField("customer_state", "STRING"),
    bigquery.SchemaField("customer_lat", "FLOAT64"),
    bigquery.SchemaField("customer_lng", "FLOAT64"),

    # Product fields
    bigquery.SchemaField("product_category_name", "STRING"),
    bigquery.SchemaField("product_category_name_english", "STRING"),
    bigquery.SchemaField("product_name_length", "INT64"),
    bigquery.SchemaField("product_description_length", "INT64"),
    bigquery.SchemaField("product_photos_qty", "INT64"),
    bigquery.SchemaField("product_weight_g", "INT64"),
    bigquery.SchemaField("product_length_cm", "INT64"),
    bigquery.SchemaField("product_height_cm", "INT64"),
    bigquery.SchemaField("product_width_cm", "INT64"),

    # Payment fields
    bigquery.SchemaField("payment_sequential", "INT64"),
    bigquery.SchemaField("payment_type", "STRING"),
    bigquery.SchemaField("payment_installments", "INT64"),
    bigquery.SchemaField("payment_value", "FLOAT64"),
]

# =========================================================
# HELPERS
# =========================================================
def ensure_dataset():
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset exists: {dataset_ref}")

    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = LOCATION
        client.create_dataset(dataset)
        print(f"Created dataset: {dataset_ref}")

def load_csv_table(table_name: str, gcs_uri: str):
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=DAILY_ORDERS_SCHEMA,
        autodetect=False,
        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE
            if OVERWRITE
            else bigquery.WriteDisposition.WRITE_APPEND
        ),
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        allow_quoted_newlines=True,
        allow_jagged_rows=False,
        ignore_unknown_values=False,
    )

    print(f"Loading {gcs_uri} -> {table_id}")

    load_job = client.load_table_from_uri(
        gcs_uri,
        table_id,
        job_config=job_config,
        location=LOCATION,
    )

    load_job.result()

    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows:,} rows into {table_id}")


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    ensure_dataset()

    for table_name, gcs_uri in TABLES.items():
        try:
            load_csv_table(table_name, gcs_uri)

        except Exception as e:
            print(f"FAILED loading {table_name}: {e}")