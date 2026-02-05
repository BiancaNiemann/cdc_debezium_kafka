#!/usr/bin/env python3
"""
Setup script for PostgreSQL database.
Creates tables and initial test data.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
from rich.console import Console
from rich.table import Table

console = Console()

# Database connection parameters
DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "database": "testdb"
}


def wait_for_postgres():
    """Wait for PostgreSQL to be ready."""
    console.print("[yellow]Waiting for PostgreSQL to be ready...[/yellow]")
    
    for i in range(30):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            conn.close()
            console.print("[green]✓ PostgreSQL is ready![/green]")
            return True
        except psycopg2.OperationalError:
            time.sleep(1)
    
    console.print("[red]✗ PostgreSQL not ready after 30 seconds[/red]")
    return False


def create_tables():
    """Create the test tables."""
    console.print("\n[cyan]Creating tables...[/cyan]")
    
    conn = psycopg2.connect(**DB_PARAMS)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # Create users table
    cur.execute("""
        DROP TABLE IF EXISTS users CASCADE;
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT true
        );
    """)
    console.print("[green]✓ Created 'users' table[/green]")
    
    # Create orders table
    cur.execute("""
        DROP TABLE IF EXISTS orders CASCADE;
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            product_name VARCHAR(255) NOT NULL,
            quantity INTEGER NOT NULL,
            total_price DECIMAL(10, 2) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    console.print("[green]✓ Created 'orders' table[/green]")
    
    cur.close()
    conn.close()


def insert_sample_data():
    """Insert initial sample data."""
    console.print("\n[cyan]Inserting sample data...[/cyan]")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Insert users
    users_data = [
        ("alice", "alice@example.com"),
        ("bob", "bob@example.com"),
        ("charlie", "charlie@example.com")
    ]
    
    for username, email in users_data:
        cur.execute(
            "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id;",
            (username, email)
        )
        user_id = cur.fetchone()[0]
        console.print(f"[green]✓ Created user: {username} (ID: {user_id})[/green]")
    
    # Insert orders
    orders_data = [
        (1, "Laptop", 1, 999.99, "completed"),
        (2, "Mouse", 2, 29.99, "pending"),
        (3, "Keyboard", 1, 79.99, "shipped")
    ]
    
    for user_id, product, qty, price, status in orders_data:
        cur.execute(
            """
            INSERT INTO orders (user_id, product_name, quantity, total_price, status) 
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """,
            (user_id, product, qty, price, status)
        )
        order_id = cur.fetchone()[0]
        console.print(f"[green]✓ Created order: {product} (ID: {order_id})[/green]")
    
    conn.commit()
    cur.close()
    conn.close()


def display_current_data():
    """Display current data in tables."""
    console.print("\n[cyan]Current data in database:[/cyan]\n")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Display users
    cur.execute("SELECT id, username, email, is_active FROM users ORDER BY id;")
    users_table = Table(title="Users Table")
    users_table.add_column("ID", style="cyan")
    users_table.add_column("Username", style="magenta")
    users_table.add_column("Email", style="green")
    users_table.add_column("Active", style="yellow")
    
    for row in cur.fetchall():
        users_table.add_row(str(row[0]), row[1], row[2], str(row[3]))
    
    console.print(users_table)
    
    # Display orders
    cur.execute("""
        SELECT o.id, o.user_id, u.username, o.product_name, o.quantity, o.total_price, o.status 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.id;
    """)
    orders_table = Table(title="Orders Table")
    orders_table.add_column("ID", style="cyan")
    orders_table.add_column("User ID", style="blue")
    orders_table.add_column("Username", style="magenta")
    orders_table.add_column("Product", style="green")
    orders_table.add_column("Qty", style="yellow")
    orders_table.add_column("Price", style="red")
    orders_table.add_column("Status", style="white")
    
    for row in cur.fetchall():
        orders_table.add_row(
            str(row[0]), str(row[1]), row[2], row[3], 
            str(row[4]), f"${row[5]}", row[6]
        )
    
    console.print(orders_table)
    
    cur.close()
    conn.close()


def main():
    """Main execution function."""
    console.print("[bold blue]CDC Spike - Database Setup[/bold blue]")
    console.print("=" * 50)
    
    if not wait_for_postgres():
        return
    
    create_tables()
    insert_sample_data()
    display_current_data()
    
    console.print("\n[bold green]✓ Database setup complete![/bold green]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Run Debezium connector: python src/cdc_spike/setup_connectors.py")
    console.print("2. Make changes: python src/cdc_spike/produce_changes.py")
    console.print("3. Inspect Kafka: python src/cdc_spike/consume_kafka.py")


if __name__ == "__main__":
    main()