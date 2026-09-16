import sqlite3
import os
import datetime
import random
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "db.sqlite")

def seed_database():
    print(f"Initializing database at: {DB_PATH}")
    
    # Remove existing db if overwrite is desired (to start fresh)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database file.")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        product TEXT NOT NULL,
        region TEXT NOT NULL,
        revenue REAL NOT NULL,
        units INTEGER NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT UNIQUE NOT NULL,
        stock_level INTEGER NOT NULL,
        reorder_point INTEGER NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        segment TEXT NOT NULL,
        ltv REAL NOT NULL
    )
    """)
    
    print("Tables created successfully.")
    
    # Seed Customers
    customers_data = [
        ("Acme Corporation", "Enterprise", 125000.0),
        ("Globex Corporation", "Enterprise", 95000.0),
        ("Initech LLC", "Mid-Market", 35000.0),
        ("Umbrella Corp", "Enterprise", 150000.0),
        ("Wayne Enterprises", "Enterprise", 180000.0),
        ("Stark Industries", "Enterprise", 220000.0),
        ("Hooli Inc", "Mid-Market", 48000.0),
        ("Soylent Corp", "SMB", 8500.0),
        ("Wonka Industries", "Mid-Market", 42000.0),
        ("Dunder Mifflin", "SMB", 9500.0),
        ("Aperture Science", "Mid-Market", 31000.0),
        ("Tyrell Corp", "Enterprise", 140000.0),
        ("Veer Industries", "SMB", 6000.0),
        ("Pied Piper", "SMB", 7500.0),
        ("Massive Dynamic", "Enterprise", 115000.0)
    ]
    cursor.executemany(
        "INSERT INTO customers (name, segment, ltv) VALUES (?, ?, ?)",
        customers_data
    )
    print(f"Seeded {len(customers_data)} customers.")
    
    # Products and prices/characteristics
    products = {
        "Widget A": {"price": 25.0, "base_qty": 20, "mult": 1.2},
        "Widget B": {"price": 40.0, "base_qty": 12, "mult": 0.9},
        "Gadget X": {"price": 15.0, "base_qty": 35, "mult": 1.5},
        "Gadget Y": {"price": 60.0, "base_qty": 8, "mult": 0.8},
        "Gizmo Z": {"price": 100.0, "base_qty": 5, "mult": 1.0}
    }
    
    regions = ["North", "South", "West"]
    
    # Seed Inventory
    inventory_data = []
    for prod in products.keys():
        stock = random.randint(100, 450)
        reorder = random.randint(30, 80)
        inventory_data.append((prod, stock, reorder))
    cursor.executemany(
        "INSERT INTO inventory (product, stock_level, reorder_point) VALUES (?, ?, ?)",
        inventory_data
    )
    print("Seeded inventory.")
    
    # Seed 12 Months of Sales Data
    # Let's run from 365 days ago up to yesterday
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=365)
    
    sales_records = []
    
    # Set a fixed random seed for reproducible "seasonality" and trends
    random.seed(42)
    
    current_date = start_date
    day_count = 0
    
    while current_date < today:
        date_str = current_date.strftime("%Y-%m-%d")
        day_of_week = current_date.weekday() # 0 = Monday, 6 = Sunday
        is_weekend = day_of_week >= 5
        
        # Day index for overall upward trend (growth over time)
        trend_mult = 1.0 + (day_count / 365.0) * 0.4  # 40% growth over the year
        
        # Seasonality - Monthly factors (e.g. Q4 boost in Nov/Dec, summer dip in July)
        month = current_date.month
        month_factor = 1.0
        if month in [11, 12]:  # Holiday spike
            month_factor = 1.3
        elif month in [7, 8]:  # Summer slump
            month_factor = 0.85
        elif month == 3:       # Spring pickup
            month_factor = 1.1
            
        for prod, info in products.items():
            for region in regions:
                # Add regional sales variations
                reg_mult = 1.0
                if region == "North":
                    reg_mult = 1.15
                elif region == "West":
                    reg_mult = 0.95
                else:
                    reg_mult = 0.90
                
                # Probability of sale
                prob = 0.80 if not is_weekend else 0.40
                
                if random.random() < prob:
                    # Base units with weekend/week adjustments
                    base_units = info["base_qty"]
                    if is_weekend:
                        base_units = max(1, int(base_units * 0.5))
                    else:
                        base_units = int(base_units * random.uniform(0.8, 1.2))
                    
                    # Apply trend, region, and monthly seasonality multipliers
                    final_units = int(base_units * info["mult"] * trend_mult * reg_mult * month_factor)
                    final_units = max(1, final_units)
                    
                    # Small variation
                    final_units += random.randint(-2, 3)
                    final_units = max(1, final_units)
                    
                    revenue = round(final_units * info["price"], 2)
                    sales_records.append((date_str, prod, region, revenue, final_units))
        
        current_date += datetime.timedelta(days=1)
        day_count += 1
        
    cursor.executemany(
        "INSERT INTO sales (date, product, region, revenue, units) VALUES (?, ?, ?, ?, ?)",
        sales_records
    )
    
    conn.commit()
    print(f"Seeded {len(sales_records)} daily sales records.")
    
    # Run a quick check
    cursor.execute("SELECT COUNT(*) FROM sales")
    print(f"Total sales rows: {cursor.fetchone()[0]}")
    cursor.execute("SELECT SUM(revenue) FROM sales")
    print(f"Total revenue generated: ${cursor.fetchone()[0]:,.2f}")
    
    conn.close()
    print("Database seeding completed.")

if __name__ == "__main__":
    seed_database()
