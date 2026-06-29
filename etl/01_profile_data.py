from pathlib import Path

import pandas as pd


RAW_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

REQUIRED_COLUMNS = {
    "customers": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ],
    "geolocation": [
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ],
    "order_items": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ],
    "order_payments": [
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ],
    "order_reviews": [
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "orders": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "products": [
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "sellers": [
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ],
    "category_translation": [
        "product_category_name",
        "product_category_name_english",
    ],
}


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def load_csv(file_name: str) -> pd.DataFrame:
    file_path = RAW_DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Missing file: {file_path}")

    return pd.read_csv(file_path)


def validate_required_columns(name: str, df: pd.DataFrame) -> None:
    expected_columns = REQUIRED_COLUMNS[name]
    missing_columns = [column for column in expected_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(
            f"{name} is missing required columns: {', '.join(missing_columns)}"
        )


def profile_dataframe(name: str, df: pd.DataFrame) -> None:
    print_section(f"DATASET: {name}")

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print("\nColumn names:")
    print(list(df.columns))

    print("\nMissing values:")
    missing = df.isna().sum()
    missing = missing[missing > 0]

    if missing.empty:
        print("No missing values.")
    else:
        missing_report = pd.DataFrame(
            {
                "missing_count": missing,
                "missing_percent": (missing / len(df) * 100).round(2),
            }
        )
        print(missing_report)

    print(f"\nDuplicate rows: {df.duplicated().sum():,}")

    print("\nFirst 5 rows:")
    print(df.head())


def print_duplicate_check(label: str, df: pd.DataFrame, columns: list[str]) -> None:
    duplicate_count = df.duplicated(subset=columns).sum()
    print(f"{label}: {duplicate_count:,}")

    if duplicate_count:
        print(df[df.duplicated(subset=columns, keep=False)][columns].head(10))


def check_business_key_duplicates(dataframes: dict[str, pd.DataFrame]) -> None:
    print_section("BUSINESS KEY DUPLICATE CHECKS")

    print_duplicate_check(
        "orders.order_id",
        dataframes["orders"],
        ["order_id"],
    )
    print_duplicate_check(
        "customers.customer_id",
        dataframes["customers"],
        ["customer_id"],
    )
    print_duplicate_check(
        "products.product_id",
        dataframes["products"],
        ["product_id"],
    )
    print_duplicate_check(
        "sellers.seller_id",
        dataframes["sellers"],
        ["seller_id"],
    )
    print_duplicate_check(
        "order_items by order_id + order_item_id",
        dataframes["order_items"],
        ["order_id", "order_item_id"],
    )
    print_duplicate_check(
        "payments by order_id + payment_sequential",
        dataframes["order_payments"],
        ["order_id", "payment_sequential"],
    )
    print_duplicate_check(
        "reviews.review_id",
        dataframes["order_reviews"],
        ["review_id"],
    )
    print_duplicate_check(
        "reviews per order_id",
        dataframes["order_reviews"],
        ["order_id"],
    )
    print_duplicate_check(
        "geolocation full-row duplicates",
        dataframes["geolocation"],
        list(dataframes["geolocation"].columns),
    )
    print_duplicate_check(
        "geolocation zip/city/state duplicates",
        dataframes["geolocation"],
        [
            "geolocation_zip_code_prefix",
            "geolocation_city",
            "geolocation_state",
        ],
    )


def check_relationships(dataframes: dict[str, pd.DataFrame]) -> None:
    print_section("FOREIGN KEY / RELATIONSHIP CHECKS")

    orders = dataframes["orders"]
    customers = dataframes["customers"]
    order_items = dataframes["order_items"]
    payments = dataframes["order_payments"]
    reviews = dataframes["order_reviews"]
    products = dataframes["products"]
    sellers = dataframes["sellers"]
    category_translation = dataframes["category_translation"]
    geolocation = dataframes["geolocation"]

    checks = [
        {
            "name": "orders.customer_id -> customers.customer_id",
            "left": orders["customer_id"],
            "right": customers["customer_id"],
        },
        {
            "name": "order_items.order_id -> orders.order_id",
            "left": order_items["order_id"],
            "right": orders["order_id"],
        },
        {
            "name": "payments.order_id -> orders.order_id",
            "left": payments["order_id"],
            "right": orders["order_id"],
        },
        {
            "name": "reviews.order_id -> orders.order_id",
            "left": reviews["order_id"],
            "right": orders["order_id"],
        },
        {
            "name": "order_items.product_id -> products.product_id",
            "left": order_items["product_id"],
            "right": products["product_id"],
        },
        {
            "name": "order_items.seller_id -> sellers.seller_id",
            "left": order_items["seller_id"],
            "right": sellers["seller_id"],
        },
        {
            "name": (
                "products.product_category_name -> "
                "category_translation.product_category_name"
            ),
            "left": products["product_category_name"],
            "right": category_translation["product_category_name"],
        },
        {
            "name": (
                "customers.customer_zip_code_prefix -> "
                "geolocation.geolocation_zip_code_prefix"
            ),
            "left": customers["customer_zip_code_prefix"],
            "right": geolocation["geolocation_zip_code_prefix"],
        },
        {
            "name": (
                "sellers.seller_zip_code_prefix -> "
                "geolocation.geolocation_zip_code_prefix"
            ),
            "left": sellers["seller_zip_code_prefix"],
            "right": geolocation["geolocation_zip_code_prefix"],
        },
    ]

    for check in checks:
        missing_keys = set(check["left"].dropna()) - set(check["right"].dropna())

        print(f"\n{check['name']}")
        print(f"Missing references: {len(missing_keys):,}")

        if missing_keys:
            print(f"Example missing keys: {list(missing_keys)[:5]}")


def check_date_ranges_and_quality(dataframes: dict[str, pd.DataFrame]) -> None:
    print_section("DATE RANGE AND QUALITY CHECKS")

    orders = dataframes["orders"].copy()

    date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]

    for column in date_columns:
        orders[column] = pd.to_datetime(orders[column], errors="coerce")

        print(f"\n{column}")
        print(f"Minimum date: {orders[column].min()}")
        print(f"Maximum date: {orders[column].max()}")
        print(f"Missing dates: {orders[column].isna().sum():,}")

    purchase = orders["order_purchase_timestamp"]
    approved = orders["order_approved_at"]
    delivered = orders["order_delivered_customer_date"]
    estimated = orders["order_estimated_delivery_date"]

    approved_before_purchase = approved.notna() & purchase.notna() & (approved < purchase)
    delivered_before_purchase = (
        delivered.notna() & purchase.notna() & (delivered < purchase)
    )
    estimated_before_purchase = (
        estimated.notna() & purchase.notna() & (estimated < purchase)
    )
    late_deliveries = delivered.notna() & estimated.notna() & (delivered > estimated)
    delivered_orders = delivered.notna()
    late_delivery_rate = (
        late_deliveries.sum() / delivered_orders.sum() * 100
        if delivered_orders.sum()
        else 0
    )

    print("\nDate quality issues:")
    print(f"Approved date before purchase date: {approved_before_purchase.sum():,}")
    print(
        "Delivered customer date before purchase date: "
        f"{delivered_before_purchase.sum():,}"
    )
    print(
        "Estimated delivery date before purchase date: "
        f"{estimated_before_purchase.sum():,}"
    )
    print(
        "Delivered customer date later than estimated delivery date: "
        f"{late_deliveries.sum():,}"
    )
    print(f"Late delivery count: {late_deliveries.sum():,}")
    print(f"Late delivery rate among delivered orders: {late_delivery_rate:.2f}%")


def check_basic_business_metrics(dataframes: dict[str, pd.DataFrame]) -> None:
    print_section("BASIC BUSINESS METRICS")

    order_items = dataframes["order_items"].copy()
    orders = dataframes["orders"].copy()
    reviews = dataframes["order_reviews"].copy()
    payments = dataframes["order_payments"].copy()
    customers = dataframes["customers"].copy()
    products = dataframes["products"].copy()
    category_translation = dataframes["category_translation"].copy()

    order_items["total_item_value"] = (
        order_items["price"] + order_items["freight_value"]
    )

    total_orders = orders["order_id"].nunique()
    product_revenue = order_items["price"].sum()
    freight_revenue = order_items["freight_value"].sum()
    total_revenue = order_items["total_item_value"].sum()
    average_order_value = product_revenue / total_orders if total_orders else 0
    freight_ratio = freight_revenue / total_revenue * 100 if total_revenue else 0

    print(f"Total orders: {total_orders:,}")
    print(f"Total order items: {len(order_items):,}")
    print(f"Total products sold: {order_items['product_id'].nunique():,}")
    print(f"Total sellers: {order_items['seller_id'].nunique():,}")
    print(f"Total product revenue: {product_revenue:,.2f}")
    print(f"Total freight value: {freight_revenue:,.2f}")
    print(f"Total revenue including freight: {total_revenue:,.2f}")
    print(f"Average order value: {average_order_value:,.2f}")
    print(f"Freight ratio: {freight_ratio:.2f}%")
    print(f"Average review score: {reviews['review_score'].mean():.2f}")

    print("\nOrder status distribution:")
    print(orders["order_status"].value_counts(dropna=False))

    print("\nPayment method distribution:")
    print(payments["payment_type"].value_counts(dropna=False))

    revenue_by_state = (
        order_items.merge(orders[["order_id", "customer_id"]], on="order_id", how="left")
        .merge(
            customers[["customer_id", "customer_state"]],
            on="customer_id",
            how="left",
        )
        .groupby("customer_state", dropna=False)["total_item_value"]
        .sum()
        .sort_values(ascending=False)
    )

    print("\nRevenue by customer state:")
    print(revenue_by_state)

    revenue_by_category = (
        order_items.merge(
            products[["product_id", "product_category_name"]],
            on="product_id",
            how="left",
        )
        .merge(
            category_translation,
            on="product_category_name",
            how="left",
        )
        .assign(
            product_category_name_english=lambda df: df[
                "product_category_name_english"
            ].fillna("unknown")
        )
        .groupby("product_category_name_english", dropna=False)["total_item_value"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )

    print("\nTop 20 revenue by product category:")
    print(revenue_by_category)


def main() -> None:
    dataframes = {}

    for name, file_name in FILES.items():
        df = load_csv(file_name)
        validate_required_columns(name, df)
        dataframes[name] = df
        profile_dataframe(name, df)

    check_business_key_duplicates(dataframes)
    check_relationships(dataframes)
    check_date_ranges_and_quality(dataframes)
    check_basic_business_metrics(dataframes)


if __name__ == "__main__":
    main()
