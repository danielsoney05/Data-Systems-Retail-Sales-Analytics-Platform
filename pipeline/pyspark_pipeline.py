from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# GCS Bucket & BigQuery Config
GCS_TEMP_BUCKET  = "gs://olist-494110_bucket/temp/"
BQ_PROJECT       = "olist-494110"
BQ_SOURCE        = "olist"
BQ_DATASET       = "olist_cleaned"

# Load a table directly from BigQuery
def load_bq(spark, table_name: str):
    return (spark.read
        .format("bigquery")
        .option("table", f"{BQ_PROJECT}.{BQ_SOURCE}.{table_name}")
        .option("temporaryGcsBucket", GCS_TEMP_BUCKET.replace("gs://", "").split("/")[0])
        .load()
    )

def save(df, table_name: str):
    from pyspark.sql.types import ArrayType

    # Flatten any array columns — BigQuery does not support ArrayType via this connector
    for field in df.schema.fields:
        if isinstance(field.dataType, ArrayType):
            df = df.withColumn(field.name, F.concat_ws(",", F.col(field.name)))

    df.write \
        .format("bigquery") \
        .option("table", f"{BQ_PROJECT}.{BQ_DATASET}.{table_name}") \
        .option("writeMethod", "direct") \
        .mode("overwrite") \
        .save()

def clean_orders(df):
    return (df.dropna(subset=["order_id", "customer_id"]).dropDuplicates(["order_id"])
            .withColumn("order_purchase_timestamp", F.to_timestamp("order_purchase_timestamp", "yyyy-MM-dd HH:mm:ss"))
            .withColumn("order_estimated_delivery_date", F.to_timestamp("order_estimated_delivery_date", "yyyy-MM-dd HH:mm:ss"))
            .withColumn("order_delivered_customer_date", F.to_timestamp("order_delivered_customer_date", "yyyy-MM-dd HH:mm:ss")))

def clean_customers(df):
    return (df.dropna(subset=["customer_id"]).dropDuplicates(["customer_id"])
            .dropDuplicates(["customer_unique_id"]).withColumn("customer_city", F.lower(F.trim(F.col("customer_city"))))
            .withColumn("customer_state", F.upper(F.trim(F.col("customer_state")))))

def clean_order_items(df):
    return (df
        .dropna(subset=["order_id", "product_id", "seller_id"])
        .withColumn("price",         F.col("price").cast("float"))
        .withColumn("freight_value", F.col("freight_value").cast("float"))
        .withColumn("item_total",    F.col("price") + F.col("freight_value"))
    )

def clean_products(df, category_translation):
    return (df
        .dropna(subset=["product_id"])
        .dropDuplicates(["product_id"])
        .join(category_translation, on="product_category_name", how="left")
    )

def clean_payments(df):
    return (df
        .dropna(subset=["order_id"])
        .withColumn("payment_value", F.col("payment_value").cast("float"))
        .groupBy("order_id")
        .agg(
            F.sum("payment_value").alias("total_payment_value"),
            F.collect_set("payment_type").alias("payment_types"),
            F.max("payment_installments").alias("max_installments"),
        )
    )

def clean_reviews(df):
    return (df
        .dropna(subset=["review_id", "order_id"])
        .withColumn("review_score", F.expr("try_cast(review_score as int)"))
        .groupBy("order_id")
        .agg(
            F.max("review_score").alias("review_score"),
            F.first("review_comment_title").alias("review_comment_title"),
        )
    )

def clean_sellers(df, geolocation):
    geo_dedup = (geolocation
        .dropna(subset=["geolocation_zip_code_prefix"])
        .dropDuplicates(["geolocation_zip_code_prefix"])
        .select(
            F.col("geolocation_zip_code_prefix").alias("seller_zip_code_prefix"),
            "geolocation_lat",
            "geolocation_lng",
        )
    )
    return (df
        .dropna(subset=["seller_id"])
        .dropDuplicates(["seller_id"])
        .join(geo_dedup, on="seller_zip_code_prefix", how="left")
    )

def create_fact_orders(orders, customers, payments, reviews):
    customers_s = customers.select("customer_id", "customer_unique_id", "customer_city", "customer_state")

    return (orders
        .join(customers_s, on="customer_id", how="inner")
        .join(payments,    on="order_id",    how="left")
        .join(reviews,     on="order_id",    how="left")
        .withColumn("delivery_days",
            F.datediff("order_delivered_customer_date", "order_purchase_timestamp"))
        .withColumn("estimated_days",
            F.datediff("order_estimated_delivery_date", "order_purchase_timestamp"))
        .withColumn("is_late_delivery",
            F.col("order_delivered_customer_date") > F.col("order_estimated_delivery_date"))
        .withColumn("purchase_year",  F.year("order_purchase_timestamp"))
        .withColumn("purchase_month", F.month("order_purchase_timestamp"))
    )

def create_fact_order_items(order_items, orders, products, sellers):
    orders_s = orders.select("order_id", "customer_id",
                             "order_status", "order_purchase_timestamp")
    return (order_items
        .join(orders_s,  on="order_id",   how="left")
        .join(products,  on="product_id", how="left")
        .join(sellers.select(
                "seller_id", "seller_city",
                "seller_state", "geolocation_lat", "geolocation_lng"),
              on="seller_id", how="left")
        .withColumn("purchase_year",  F.year("order_purchase_timestamp"))
        .withColumn("purchase_month", F.month("order_purchase_timestamp"))
    )

def run_pipeline():
    import os

    # Windows Hadoop config
    os.environ["HADOOP_HOME"] = "C:/hadoop"
    os.environ["PATH"] = os.environ["PATH"] + ";C:/hadoop/bin"

    # GCP credentials — created automatically by: gcloud auth application-default login
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
        os.path.expanduser("~/AppData/Roaming/gcloud/application_default_credentials.json")
    )

    # Initialize Spark Session with BigQuery connector
    spark = (
        SparkSession.builder
        .appName("Retail Pipeline")
        .config(
            "spark.jars.packages",
            "com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.36.1"
        )
        .getOrCreate()
    )

    spark._jsc.hadoopConfiguration().set(
        "fs.gs.impl",
        "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem"
    )

    spark._jsc.hadoopConfiguration().set(
        "fs.AbstractFileSystem.gs.impl",
        "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS"
    )

    # Extract — load raw tables from BigQuery olist dataset
    raw_orders               = load_bq(spark, "orders")
    raw_customers            = load_bq(spark, "customer")
    raw_order_items          = load_bq(spark, "order_items")
    raw_products             = load_bq(spark, "products")
    raw_payments             = load_bq(spark, "order_payments")
    raw_reviews              = load_bq(spark, "order_reviews")
    raw_sellers              = load_bq(spark, "sellers")
    raw_geolocation          = load_bq(spark, "geolocation")
    raw_category_translation = load_bq(spark, "product_category_name_translation")

    print("Data Loaded Successfully!")

    # Transform — clean each table
    orders      = clean_orders(raw_orders)
    customers   = clean_customers(raw_customers)
    order_items = clean_order_items(raw_order_items)
    products    = clean_products(raw_products, raw_category_translation)
    payments    = clean_payments(raw_payments)
    reviews     = clean_reviews(raw_reviews)
    sellers     = clean_sellers(raw_sellers, raw_geolocation)

    # Build fact tables
    fact_orders_df      = create_fact_orders(orders, customers, payments, reviews)
    fact_order_items_df = create_fact_order_items(order_items, orders, products, sellers)

    fact_orders_df.show(5)
    fact_order_items_df.show(5)

    # Load — write to BigQuery under olist-494110.olist_cleaned
    save(fact_orders_df,      "fact_orders")
    save(fact_order_items_df, "fact_order_items")
    save(customers,           "dim_customers")
    save(products,            "dim_products")
    save(sellers,             "dim_sellers")

    print("Data Transformed and Saved to BigQuery Successfully!")

    spark.stop()

if __name__ == "__main__":
    run_pipeline()