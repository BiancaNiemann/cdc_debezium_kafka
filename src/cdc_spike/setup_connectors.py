#!/usr/bin/env python3
"""
Setup Debezium and Elasticsearch connectors via Kafka Connect REST API.
"""

import requests
import json
import time
from rich.console import Console
from rich.json import JSON

console = Console()

KAFKA_CONNECT_URL = "http://localhost:8083"


def wait_for_kafka_connect():
    """Wait for Kafka Connect to be ready."""
    console.print("[yellow]Waiting for Kafka Connect to be ready...[/yellow]")
    
    for i in range(60):
        try:
            response = requests.get(f"{KAFKA_CONNECT_URL}/", timeout=2)
            if response.status_code == 200:
                console.print("[green]✓ Kafka Connect is ready![/green]")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    
    console.print("[red]✗ Kafka Connect not ready after 2 minutes[/red]")
    return False


def get_connectors():
    """List all existing connectors."""
    try:
        response = requests.get(f"{KAFKA_CONNECT_URL}/connectors")
        return response.json()
    except Exception as e:
        console.print(f"[red]Error getting connectors: {e}[/red]")
        return []


def delete_connector(name):
    """Delete a connector if it exists."""
    try:
        response = requests.delete(f"{KAFKA_CONNECT_URL}/connectors/{name}")
        if response.status_code == 204:
            console.print(f"[yellow]Deleted existing connector: {name}[/yellow]")
            return True
    except Exception as e:
        console.print(f"[red]Error deleting connector {name}: {e}[/red]")
    return False


def create_connector(config_file, connector_name):
    """Create a connector from config file."""
    console.print(f"\n[cyan]Creating connector: {connector_name}[/cyan]")
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Delete if exists
        existing = get_connectors()
        if connector_name in existing:
            delete_connector(connector_name)
            time.sleep(2)
        
        # Create connector
        response = requests.post(
            f"{KAFKA_CONNECT_URL}/connectors",
            json=config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            console.print(f"[green]✓ Successfully created {connector_name}[/green]")
            console.print("\n[cyan]Connector configuration:[/cyan]")
            console.print(JSON(json.dumps(config, indent=2)))
            return True
        else:
            console.print(f"[red]✗ Failed to create {connector_name}[/red]")
            console.print(f"[red]Status: {response.status_code}[/red]")
            console.print(f"[red]Response: {response.text}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error creating connector: {e}[/red]")
        return False


def check_connector_status(connector_name):
    """Check the status of a connector."""
    try:
        response = requests.get(f"{KAFKA_CONNECT_URL}/connectors/{connector_name}/status")
        if response.status_code == 200:
            status = response.json()
            console.print(f"\n[cyan]Status for {connector_name}:[/cyan]")
            console.print(JSON(json.dumps(status, indent=2)))
            
            # Check if running
            connector_state = status.get('connector', {}).get('state', '')
            if connector_state == 'RUNNING':
                console.print(f"[green]✓ {connector_name} is RUNNING[/green]")
                return True
            else:
                console.print(f"[yellow]⚠ {connector_name} state: {connector_state}[/yellow]")
                return False
    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")
    return False


def list_topics():
    """List Kafka topics (requires kafka-python or curl)."""
    console.print("\n[cyan]Attempting to list Kafka topics...[/cyan]")
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "exec", "cdc-kafka", "kafka-topics", 
             "--bootstrap-server", "localhost:9092", "--list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            topics = result.stdout.strip().split('\n')
            console.print("[green]Current Kafka topics:[/green]")
            for topic in topics:
                if topic:
                    console.print(f"  • {topic}")
        else:
            console.print("[yellow]Could not list topics (normal if Kafka not fully ready)[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Could not list topics: {e}[/yellow]")


def main():
    """Main execution function."""
    console.print("[bold blue]CDC Spike - Connector Setup[/bold blue]")
    console.print("=" * 50)
    
    if not wait_for_kafka_connect():
        return
    
    # Show existing connectors
    existing = get_connectors()
    console.print(f"\n[cyan]Existing connectors: {existing}[/cyan]")
    
    # Create Debezium PostgreSQL connector
    success_debezium = create_connector(
        "config/debezium-postgres-connector.json",
        "postgres-source-connector"
    )
    
    if success_debezium:
        time.sleep(5)
        check_connector_status("postgres-source-connector")
        time.sleep(3)
        list_topics()
    
    console.print("\n[bold green]✓ Connector setup complete![/bold green]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Make database changes: python src/cdc_spike/produce_changes.py")
    console.print("2. Inspect messages: python src/cdc_spike/consume_kafka.py")


if __name__ == "__main__":
    main()