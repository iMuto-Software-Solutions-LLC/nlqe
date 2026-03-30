#!/usr/bin/env python3
"""Create sample datasource for prototyping."""

import random
from datetime import datetime, timedelta

import pandas as pd


# Create sample transaction data
def create_sample_data() -> None:
    """Create sample parquet files for testing."""
    # Set fixed seed for deterministic data generation
    random.seed(42)

    # Sample regions with more variety
    regions = [
        ("North America", "USA"),
        ("North America", "Canada"),
        ("Europe", "UK"),
        ("Europe", "Germany"),
        ("Asia", "Japan"),
        ("Asia", "India"),
        ("South America", "Brazil"),
        ("Africa", "South Africa"),
    ]

    # Create transactions data with realistic distribution
    start_date = datetime(2024, 1, 1)
    transactions = []
    product_categories = ["Electronics", "Clothing", "Food", "Home", "Sports"]
    product_names = {
        "Electronics": ["Laptop", "Phone", "Tablet", "Headphones", "Camera"],
        "Clothing": ["T-Shirt", "Jeans", "Jacket", "Shoes", "Dress"],
        "Food": ["Coffee", "Bread", "Milk", "Cheese", "Fruit"],
        "Home": ["Lamp", "Chair", "Pillow", "Rug", "Clock"],
        "Sports": ["Soccer Ball", "Tennis Racket", "Yoga Mat", "Dumbbells", "Bicycle"],
    }

    for i in range(2500):  # Increased to 2500 transactions
        date = start_date + timedelta(days=random.randint(0, 90))
        transaction_id = i + 1
        customer_id = random.randint(1, 150)  # 150 customers
        region_id = random.randint(1, len(regions))
        category = random.choice(product_categories)
        product_name = random.choice(product_names[category])

        # Price varies by category
        if category == "Electronics":
            amount = round(random.uniform(500, 2000), 2)
        elif category == "Clothing":
            amount = round(random.uniform(20, 150), 2)
        elif category == "Food":
            amount = round(random.uniform(5, 50), 2)
        elif category == "Home":
            amount = round(random.uniform(50, 500), 2)
        else:  # Sports
            amount = round(random.uniform(30, 300), 2)

        quantity = random.randint(1, 10)
        is_return = random.choice([True, False]) if random.random() < 0.1 else False

        transactions.append(
            {
                "transaction_id": transaction_id,
                "date": date,
                "customer_id": customer_id,
                "region_id": region_id,
                "product_name": product_name,
                "category": category,
                "amount": amount,
                "quantity": quantity,
                "is_return": is_return,
                "profit_margin": round(amount * random.uniform(0.15, 0.4), 2),
            }
        )

    # Create customers data with more detail
    customers = []
    for i in range(150):
        customer_id = i + 1
        region_id = random.randint(1, len(regions))
        signup_date = start_date + timedelta(days=random.randint(-365, 90))
        lifetime_value = round(random.uniform(100, 50000), 2)
        is_active = random.choice([True, False])

        customers.append(
            {
                "customer_id": customer_id,
                "name": f"Customer {customer_id}",
                "region_id": region_id,
                "signup_date": signup_date,
                "is_active": is_active,
                "lifetime_value": lifetime_value,
                "tier": random.choice(["Gold", "Silver", "Bronze"]),
            }
        )

    # Create regions data with more columns
    regions_data = [
        {
            "region_id": i + 1,
            "name": region[0],
            "country": region[1],
            "timezone": random.choice(["EST", "CET", "JST", "IST", "BRT", "SAST"]),
            "is_priority": random.choice([True, False]),
        }
        for i, region in enumerate(regions)
    ]

    # Create products table (new)
    products = []
    for category in product_categories:
        for i, product_name in enumerate(product_names[category]):
            products.append(
                {
                    "product_id": len(products) + 1,
                    "product_name": product_name,
                    "category": category,
                    "price": round(random.uniform(10, 1000), 2),
                    "stock_level": random.randint(0, 500),
                }
            )

    # Convert to DataFrames
    df_transactions = pd.DataFrame(transactions)
    df_customers = pd.DataFrame(customers)
    df_regions = pd.DataFrame(regions_data)
    df_products = pd.DataFrame(products)

    # Save to parquet
    df_transactions.to_parquet("fixtures/transactions.parquet", index=False)
    df_customers.to_parquet("fixtures/customers.parquet", index=False)
    df_regions.to_parquet("fixtures/regions.parquet", index=False)
    df_products.to_parquet("fixtures/products.parquet", index=False)

    print("Created fixtures/transactions.parquet (2500 rows)")
    print(f"Created fixtures/customers.parquet ({len(customers)} rows)")
    print(f"Created fixtures/regions.parquet ({len(regions_data)} rows)")
    print(f"Created fixtures/products.parquet ({len(products)} rows)")

    # Print schemas
    print("\n--- Transaction Schema ---")
    print(df_transactions.dtypes)
    print(f"\nSample transactions:\n{df_transactions.head(3)}")

    print("\n--- Customer Schema ---")
    print(df_customers.dtypes)
    print(f"\nSample customers:\n{df_customers.head(3)}")

    print("\n--- Region Schema ---")
    print(df_regions.dtypes)
    print(f"\nSample regions:\n{df_regions.head(3)}")

    print("\n--- Product Schema ---")
    print(df_products.dtypes)
    print(f"\nSample products:\n{df_products.head(3)}")

    # Print some statistics
    print("\n--- Statistics ---")
    print(f"Total revenue: ${df_transactions['amount'].sum():,.2f}")
    print(f"Average transaction: ${df_transactions['amount'].mean():,.2f}")
    print(f"Transactions by category:")
    print(df_transactions["category"].value_counts())


if __name__ == "__main__":
    create_sample_data()
