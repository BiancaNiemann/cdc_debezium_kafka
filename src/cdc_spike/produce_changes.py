#!/usr/bin/env python3
"""
Produce database changes to trigger CDC events.
Demonstrates INSERT, UPDATE, and DELETE operations.
"""

import psycopg2
import time
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.panel import Panel

console = Console()

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "database": "testdb"
}


def show_menu():
    """Display interactive menu."""
    menu_text = """
[bold cyan]Choose an operation:[/bold cyan]

[green]1.[/green] INSERT new user
[green]2.[/green] INSERT new order
[yellow]3.[/yellow] UPDATE user email
[yellow]4.[/yellow] UPDATE order status
[red]5.[/red] DELETE user
[red]6.[/red] DELETE order
[blue]7.[/blue] Bulk operations (3 inserts + 2 updates)
[magenta]8.[/magenta] View current data
[white]9.[/white] Exit
    """
    console.print(Panel(menu_text, title="CDC Change Producer"))


def insert_user():
    """Insert a new user."""
    username = Prompt.ask("[cyan]Enter username[/cyan]")
    email = Prompt.ask("[cyan]Enter email[/cyan]")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    try:
        cur.execute(
            "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id;",
            (username, email)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        console.print(f"\n[green]✓ Inserted user '{username}' with ID {user_id}[/green]")
        console.print(f"[yellow]→ This triggered a CDC INSERT event (op='c')[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def insert_order():
    """Insert a new order."""
    # Show available users
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users ORDER BY id;")
    users = cur.fetchall()
    
    console.print("\n[cyan]Available users:[/cyan]")
    for user_id, username in users:
        console.print(f"  {user_id}: {username}")
    
    user_id = IntPrompt.ask("\n[cyan]Enter user ID[/cyan]")
    product_name = Prompt.ask("[cyan]Enter product name[/cyan]")
    quantity = IntPrompt.ask("[cyan]Enter quantity[/cyan]")
    total_price = float(Prompt.ask("[cyan]Enter total price[/cyan]"))
    
    try:
        cur.execute(
            """
            INSERT INTO orders (user_id, product_name, quantity, total_price, status) 
            VALUES (%s, %s, %s, %s, 'pending') RETURNING id;
            """,
            (user_id, product_name, quantity, total_price)
        )
        order_id = cur.fetchone()[0]
        conn.commit()
        console.print(f"\n[green]✓ Inserted order '{product_name}' with ID {order_id}[/green]")
        console.print(f"[yellow]→ This triggered a CDC INSERT event (op='c')[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def update_user_email():
    """Update a user's email."""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT id, username, email FROM users ORDER BY id;")
    users = cur.fetchall()
    
    console.print("\n[cyan]Current users:[/cyan]")
    for user_id, username, email in users:
        console.print(f"  {user_id}: {username} ({email})")
    
    user_id = IntPrompt.ask("\n[cyan]Enter user ID to update[/cyan]")
    new_email = Prompt.ask("[cyan]Enter new email[/cyan]")
    
    try:
        cur.execute(
            "UPDATE users SET email = %s WHERE id = %s;",
            (new_email, user_id)
        )
        conn.commit()
        console.print(f"\n[green]✓ Updated user {user_id}'s email to {new_email}[/green]")
        console.print(f"[yellow]→ This triggered a CDC UPDATE event (op='u')[/yellow]")
        console.print(f"[yellow]→ Event contains both 'before' and 'after' states[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def update_order_status():
    """Update an order's status."""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT id, product_name, status FROM orders ORDER BY id;")
    orders = cur.fetchall()
    
    console.print("\n[cyan]Current orders:[/cyan]")
    for order_id, product, status in orders:
        console.print(f"  {order_id}: {product} - {status}")
    
    order_id = IntPrompt.ask("\n[cyan]Enter order ID to update[/cyan]")
    new_status = Prompt.ask(
        "[cyan]Enter new status[/cyan]",
        choices=["pending", "shipped", "delivered", "cancelled"]
    )
    
    try:
        cur.execute(
            "UPDATE orders SET status = %s WHERE id = %s;",
            (new_status, order_id)
        )
        conn.commit()
        console.print(f"\n[green]✓ Updated order {order_id}'s status to {new_status}[/green]")
        console.print(f"[yellow]→ This triggered a CDC UPDATE event (op='u')[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def delete_user():
    """Delete a user."""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT id, username, email FROM users ORDER BY id;")
    users = cur.fetchall()
    
    console.print("\n[cyan]Current users:[/cyan]")
    for user_id, username, email in users:
        console.print(f"  {user_id}: {username} ({email})")
    
    user_id = IntPrompt.ask("\n[cyan]Enter user ID to delete[/cyan]")
    
    confirm = Prompt.ask(
        f"[red]Are you sure you want to delete user {user_id}?[/red]",
        choices=["yes", "no"]
    )
    
    if confirm == "yes":
        try:
            # First delete related orders
            cur.execute("DELETE FROM orders WHERE user_id = %s;", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            conn.commit()
            console.print(f"\n[green]✓ Deleted user {user_id}[/green]")
            console.print(f"[yellow]→ This triggered CDC DELETE events (op='d')[/yellow]")
            console.print(f"[yellow]→ Followed by TOMBSTONE messages (null value)[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            conn.rollback()
    
    cur.close()
    conn.close()


def delete_order():
    """Delete an order."""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT id, product_name, status FROM orders ORDER BY id;")
    orders = cur.fetchall()
    
    console.print("\n[cyan]Current orders:[/cyan]")
    for order_id, product, status in orders:
        console.print(f"  {order_id}: {product} - {status}")
    
    order_id = IntPrompt.ask("\n[cyan]Enter order ID to delete[/cyan]")
    
    try:
        cur.execute("DELETE FROM orders WHERE id = %s;", (order_id,))
        conn.commit()
        console.print(f"\n[green]✓ Deleted order {order_id}[/green]")
        console.print(f"[yellow]→ This triggered a CDC DELETE event (op='d')[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def bulk_operations():
    """Perform bulk operations for testing."""
    console.print("\n[cyan]Performing bulk operations...[/cyan]")
    
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    try:
        # 3 inserts
        console.print("\n[green]Inserting 3 new users...[/green]")
        for i in range(3):
            username = f"bulk_user_{int(time.time())}_{i}"
            email = f"{username}@example.com"
            cur.execute(
                "INSERT INTO users (username, email) VALUES (%s, %s);",
                (username, email)
            )
            console.print(f"  ✓ Inserted {username}")
        
        conn.commit()
        
        # 2 updates
        console.print("\n[yellow]Updating 2 existing orders...[/yellow]")
        cur.execute("SELECT id FROM orders LIMIT 2;")
        order_ids = [row[0] for row in cur.fetchall()]
        
        for order_id in order_ids:
            cur.execute(
                "UPDATE orders SET status = 'shipped' WHERE id = %s;",
                (order_id,)
            )
            console.print(f"  ✓ Updated order {order_id}")
        
        conn.commit()
        
        console.print("\n[green]✓ Bulk operations complete![/green]")
        console.print("[yellow]→ Generated 3 INSERT events and 2 UPDATE events[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def view_data():
    """View current database data."""
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # Users
    cur.execute("SELECT id, username, email, is_active FROM users ORDER BY id;")
    users_table = Table(title="Users")
    users_table.add_column("ID", style="cyan")
    users_table.add_column("Username", style="magenta")
    users_table.add_column("Email", style="green")
    users_table.add_column("Active", style="yellow")
    
    for row in cur.fetchall():
        users_table.add_row(str(row[0]), row[1], row[2], str(row[3]))
    
    console.print(users_table)
    
    # Orders
    cur.execute("""
        SELECT o.id, u.username, o.product_name, o.quantity, o.total_price, o.status 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.id;
    """)
    orders_table = Table(title="Orders")
    orders_table.add_column("ID", style="cyan")
    orders_table.add_column("User", style="magenta")
    orders_table.add_column("Product", style="green")
    orders_table.add_column("Qty", style="yellow")
    orders_table.add_column("Price", style="red")
    orders_table.add_column("Status", style="white")
    
    for row in cur.fetchall():
        orders_table.add_row(
            str(row[0]), row[1], row[2], str(row[3]), f"${row[4]}", row[5]
        )
    
    console.print(orders_table)
    
    cur.close()
    conn.close()


def main():
    """Main execution loop."""
    console.print("[bold blue]CDC Spike - Change Producer[/bold blue]")
    console.print("=" * 50)
    
    while True:
        show_menu()
        choice = Prompt.ask("\n[bold]Your choice[/bold]", choices=[str(i) for i in range(1, 10)])
        
        if choice == "1":
            insert_user()
        elif choice == "2":
            insert_order()
        elif choice == "3":
            update_user_email()
        elif choice == "4":
            update_order_status()
        elif choice == "5":
            delete_user()
        elif choice == "6":
            delete_order()
        elif choice == "7":
            bulk_operations()
        elif choice == "8":
            view_data()
        elif choice == "9":
            console.print("\n[green]Goodbye![/green]")
            break
        
        console.print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    main()