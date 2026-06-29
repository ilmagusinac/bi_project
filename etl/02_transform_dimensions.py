from pathlib import Path
import unicodedata

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

ORDER_DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

ITEM_DATE_COLUMNS = ["shipping_limit_date"]

REVIEW_DATE_COLUMNS = [
    "review_creation_date",
    "review_answer_timestamp",
]


def load_csv(file_name: str) -> pd.DataFrame:
    file_path = RAW_DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Missing raw data file: {file_path}")

    return pd.read_csv(file_path)


def load_raw_data() -> dict[str, pd.DataFrame]:
    return {name: load_csv(file_name) for name, file_name in FILES.items()}


def parse_datetime_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cleaned = df.copy()

    for column in columns:
        cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")

    return cleaned


def normalize_text(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.lower()
    return normalized.map(strip_accents)


def strip_accents(value: str | pd.NA) -> str | pd.NA:
    if pd.isna(value):
        return value

    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )


def build_dim_date(dataframes: dict[str, pd.DataFrame]) -> pd.DataFrame:
    date_sources = []

    for column in ORDER_DATE_COLUMNS:
        date_sources.append(dataframes["orders"][column])

    for column in ITEM_DATE_COLUMNS:
        date_sources.append(dataframes["order_items"][column])

    for column in REVIEW_DATE_COLUMNS:
        date_sources.append(dataframes["order_reviews"][column])

    full_dates = (
        pd.concat(date_sources, ignore_index=True)
        .pipe(pd.to_datetime, errors="coerce")
        .dropna()
        .dt.date
        .drop_duplicates()
        .sort_values()
    )

    dim_date = pd.DataFrame({"full_date": pd.to_datetime(full_dates)})
    iso_calendar = dim_date["full_date"].dt.isocalendar()

    dim_date["year"] = dim_date["full_date"].dt.year.astype("int16")
    dim_date["quarter"] = dim_date["full_date"].dt.quarter.astype("int16")
    dim_date["month"] = dim_date["full_date"].dt.month.astype("int16")
    dim_date["month_name"] = dim_date["full_date"].dt.month_name()
    dim_date["day"] = dim_date["full_date"].dt.day.astype("int16")
    dim_date["day_of_week"] = iso_calendar.day.astype("int16")
    dim_date["day_name"] = dim_date["full_date"].dt.day_name()
    dim_date["week_of_year"] = iso_calendar.week.astype("int16")
    dim_date["is_weekend"] = dim_date["day_of_week"].isin([6, 7])
    dim_date["full_date"] = dim_date["full_date"].dt.date

    return dim_date.reset_index(drop=True)


def build_dim_geolocation(geolocation: pd.DataFrame) -> pd.DataFrame:
    cleaned = geolocation.copy()
    cleaned["city"] = normalize_text(cleaned["geolocation_city"])
    cleaned["state"] = cleaned["geolocation_state"].astype("string").str.strip().str.upper()

    zip_city_state = (
        cleaned.groupby(
            ["geolocation_zip_code_prefix", "city", "state"],
            dropna=False,
            as_index=False,
        )
        .agg(
            latitude=("geolocation_lat", "mean"),
            longitude=("geolocation_lng", "mean"),
            source_row_count=("geolocation_zip_code_prefix", "size"),
        )
    )

    canonical_location = (
        zip_city_state.sort_values(
            ["geolocation_zip_code_prefix", "source_row_count", "city", "state"],
            ascending=[True, False, True, True],
        )
        .drop_duplicates(subset=["geolocation_zip_code_prefix"])
        [["geolocation_zip_code_prefix", "city", "state"]]
    )

    zip_coordinates = (
        cleaned.groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(
            latitude=("geolocation_lat", "mean"),
            longitude=("geolocation_lng", "mean"),
            source_row_count=("geolocation_zip_code_prefix", "size"),
        )
    )

    dim_geolocation = (
        zip_coordinates.merge(
            canonical_location,
            on="geolocation_zip_code_prefix",
            how="left",
        )
        .rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"})
        .sort_values(["zip_code_prefix", "city", "state"])
        .reset_index(drop=True)
    )

    dim_geolocation["latitude"] = dim_geolocation["latitude"].round(6)
    dim_geolocation["longitude"] = dim_geolocation["longitude"].round(6)

    return dim_geolocation[
        [
            "zip_code_prefix",
            "city",
            "state",
            "latitude",
            "longitude",
            "source_row_count",
        ]
    ]


def build_dim_customer(customers: pd.DataFrame) -> pd.DataFrame:
    dim_customer = customers.copy()
    dim_customer["customer_city"] = normalize_text(dim_customer["customer_city"])
    dim_customer["customer_state"] = (
        dim_customer["customer_state"].astype("string").str.strip().str.upper()
    )
    dim_customer["geolocation_sk"] = pd.NA

    return dim_customer[
        [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
            "geolocation_sk",
        ]
    ].drop_duplicates(subset=["customer_id"])


def build_dim_product(
    products: pd.DataFrame,
    category_translation: pd.DataFrame,
) -> pd.DataFrame:
    renamed_products = products.rename(
        columns={
            "product_name_lenght": "product_name_length",
            "product_description_lenght": "product_description_length",
        }
    ).copy()

    renamed_products["product_category_name"] = (
        renamed_products["product_category_name"].fillna("unknown")
    )

    translation = category_translation.copy()
    translation["product_category_name"] = translation["product_category_name"].fillna(
        "unknown"
    )

    dim_product = renamed_products.merge(
        translation,
        on="product_category_name",
        how="left",
    )
    dim_product["product_category_name_english"] = dim_product[
        "product_category_name_english"
    ].fillna("unknown")

    dim_product["product_volume_cm3"] = (
        dim_product["product_length_cm"]
        * dim_product["product_height_cm"]
        * dim_product["product_width_cm"]
    )

    return dim_product[
        [
            "product_id",
            "product_category_name",
            "product_category_name_english",
            "product_name_length",
            "product_description_length",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
            "product_volume_cm3",
        ]
    ].drop_duplicates(subset=["product_id"])


def build_dim_seller(sellers: pd.DataFrame) -> pd.DataFrame:
    dim_seller = sellers.copy()
    dim_seller["seller_city"] = normalize_text(dim_seller["seller_city"])
    dim_seller["seller_state"] = (
        dim_seller["seller_state"].astype("string").str.strip().str.upper()
    )
    dim_seller["geolocation_sk"] = pd.NA

    return dim_seller[
        [
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
            "geolocation_sk",
        ]
    ].drop_duplicates(subset=["seller_id"])


def build_dim_payment_summary(
    orders: pd.DataFrame,
    order_payments: pd.DataFrame,
) -> pd.DataFrame:
    payments = order_payments.copy()
    payments["payment_type"] = normalize_text(payments["payment_type"])

    primary_payment_type = (
        payments.groupby(["order_id", "payment_type"], as_index=False)
        .agg(
            payment_type_value=("payment_value", "sum"),
            payment_type_rows=("payment_type", "size"),
        )
        .sort_values(
            ["order_id", "payment_type_value", "payment_type_rows", "payment_type"],
            ascending=[True, False, False, True],
        )
        .drop_duplicates(subset=["order_id"])
        [["order_id", "payment_type"]]
        .rename(columns={"payment_type": "primary_payment_type"})
    )

    dim_payment_summary = (
        payments.groupby("order_id", as_index=False)
        .agg(
            payment_count=("payment_sequential", "count"),
            payment_type_count=("payment_type", "nunique"),
            max_payment_installments=("payment_installments", "max"),
            total_payment_value=("payment_value", "sum"),
        )
        .merge(primary_payment_type, on="order_id", how="left")
    )

    payment_type_flags = (
        payments.assign(flag_value=True)
        .pivot_table(
            index="order_id",
            columns="payment_type",
            values="flag_value",
            aggfunc="any",
            fill_value=False,
        )
        .reset_index()
    )

    for payment_type in ["voucher", "credit_card", "boleto", "debit_card"]:
        if payment_type not in payment_type_flags.columns:
            payment_type_flags[payment_type] = False

    dim_payment_summary = dim_payment_summary.merge(
        payment_type_flags[
            ["order_id", "voucher", "credit_card", "boleto", "debit_card"]
        ],
        on="order_id",
        how="left",
    )

    dim_payment_summary = dim_payment_summary.rename(
        columns={
            "voucher": "has_voucher",
            "credit_card": "has_credit_card",
            "boleto": "has_boleto",
            "debit_card": "has_debit_card",
        }
    )
    dim_payment_summary["total_payment_value"] = dim_payment_summary[
        "total_payment_value"
    ].round(2)

    all_orders = orders[["order_id"]].drop_duplicates()
    dim_payment_summary = all_orders.merge(
        dim_payment_summary,
        on="order_id",
        how="left",
    )

    missing_payment_orders = dim_payment_summary["payment_count"].isna()
    if missing_payment_orders.any():
        print(
            "Missing-payment orders handled: "
            f"{int(missing_payment_orders.sum()):,}"
        )

    dim_payment_summary["payment_count"] = (
        dim_payment_summary["payment_count"].fillna(0).astype("int64")
    )
    dim_payment_summary["payment_type_count"] = (
        dim_payment_summary["payment_type_count"].fillna(0).astype("int64")
    )
    dim_payment_summary["primary_payment_type"] = dim_payment_summary[
        "primary_payment_type"
    ].fillna("missing")
    dim_payment_summary["max_payment_installments"] = (
        dim_payment_summary["max_payment_installments"].fillna(0).astype("int64")
    )
    dim_payment_summary["total_payment_value"] = dim_payment_summary[
        "total_payment_value"
    ].fillna(0).round(2)

    for column in [
        "has_voucher",
        "has_credit_card",
        "has_boleto",
        "has_debit_card",
    ]:
        dim_payment_summary[column] = dim_payment_summary[column].fillna(False)

    return dim_payment_summary[
        [
            "order_id",
            "payment_count",
            "payment_type_count",
            "primary_payment_type",
            "max_payment_installments",
            "total_payment_value",
            "has_voucher",
            "has_credit_card",
            "has_boleto",
            "has_debit_card",
        ]
    ]


def build_dim_review(order_reviews: pd.DataFrame) -> pd.DataFrame:
    reviews = order_reviews.copy()
    reviews["review_creation_date"] = pd.to_datetime(
        reviews["review_creation_date"],
        errors="coerce",
    )
    reviews["review_answer_timestamp"] = pd.to_datetime(
        reviews["review_answer_timestamp"],
        errors="coerce",
    )

    review_counts = (
        reviews.groupby("order_id", as_index=False)
        .size()
        .rename(columns={"size": "review_count"})
    )

    canonical_reviews = (
        reviews.sort_values(
            [
                "order_id",
                "review_answer_timestamp",
                "review_creation_date",
                "review_id",
            ],
            ascending=[True, False, False, True],
            na_position="last",
        )
        .drop_duplicates(subset=["order_id"])
        .merge(review_counts, on="order_id", how="left")
    )

    response_delta = (
        canonical_reviews["review_answer_timestamp"]
        - canonical_reviews["review_creation_date"]
    )
    canonical_reviews["review_response_days"] = response_delta.dt.days
    canonical_reviews["is_canonical_review"] = True

    return canonical_reviews[
        [
            "order_id",
            "review_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
            "review_response_days",
            "review_count",
            "is_canonical_review",
        ]
    ].reset_index(drop=True)


def transform_dimensions(dataframes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    parsed_dataframes = dataframes.copy()
    parsed_dataframes["orders"] = parse_datetime_columns(
        parsed_dataframes["orders"],
        ORDER_DATE_COLUMNS,
    )
    parsed_dataframes["order_items"] = parse_datetime_columns(
        parsed_dataframes["order_items"],
        ITEM_DATE_COLUMNS,
    )
    parsed_dataframes["order_reviews"] = parse_datetime_columns(
        parsed_dataframes["order_reviews"],
        REVIEW_DATE_COLUMNS,
    )

    return {
        "dim_date": build_dim_date(parsed_dataframes),
        "dim_geolocation": build_dim_geolocation(parsed_dataframes["geolocation"]),
        "dim_customer": build_dim_customer(parsed_dataframes["customers"]),
        "dim_product": build_dim_product(
            parsed_dataframes["products"],
            parsed_dataframes["category_translation"],
        ),
        "dim_seller": build_dim_seller(parsed_dataframes["sellers"]),
        "dim_payment_summary": build_dim_payment_summary(
            parsed_dataframes["orders"],
            parsed_dataframes["order_payments"]
        ),
        "dim_review": build_dim_review(parsed_dataframes["order_reviews"]),
    }


def transform_all_dimensions() -> dict[str, pd.DataFrame]:
    dataframes = load_raw_data()
    return transform_dimensions(dataframes)


def print_dimension_preview(name: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)
    print(f"Rows: {len(df):,}")
    print(df.head())


def main() -> None:
    dimensions = transform_all_dimensions()

    for name, df in dimensions.items():
        print_dimension_preview(name, df)


if __name__ == "__main__":
    main()
