#!/usr/bin/env python3
"""
Consume and inspect CDC events from Kafka.
Shows Debezium event structure and explains how to map to Elasticsearch.
"""

import json
from kafka import KafkaConsumer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
import time

# added this im
from elasticsearch import Elasticsearch 

es = Elasticsearch("http://localhost:9200")
# till here

console = Console()

KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
TOPICS = ['cdc.public.users', 'cdc.public.orders']


def explain_event_structure():
    """Explain Debezium event structure."""
    explanation = """
[bold cyan]Debezium Event Structure:[/bold cyan]

A Debezium CDC event contains:

[green]1. Key[/green] - Identifies the record (usually primary key)
   Example: {"id": 1}

[green]2. Value - The main event envelope:[/green]
   • [yellow]op[/yellow] - Operation type:
     - 'c' = CREATE (INSERT)
     - 'u' = UPDATE
     - 'd' = DELETE
     - 'r' = READ (initial snapshot)
   
   • [yellow]before[/yellow] - Previous state (null for INSERT)
   • [yellow]after[/yellow] - New state (null for DELETE)
   • [yellow]source[/yellow] - Metadata about the change:
     - Database name
     - Table name
     - Timestamp
     - Transaction ID
     - LSN (Log Sequence Number)
   
   • [yellow]ts_ms[/yellow] - Timestamp in milliseconds
   • [yellow]transaction[/yellow] - Transaction metadata

[red]3. Tombstone[/red] - After DELETE, a message with null value
   Used to clean up compacted topics

[bold cyan]Mapping to Elasticsearch:[/bold cyan]

• [green]Key[/green] → Elasticsearch document _id
• [green]after[/green] → Elasticsearch document body
• [green]before[/green] → Used for audit/history (not stored in ES)
• [red]Deletes[/red] → Remove document from ES index
    """
    console.print(Panel(explanation, title="Understanding CDC Events"))


def create_consumer(topics):
    """Create Kafka consumer."""
    try:
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='cdc-inspector',
            value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
            key_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
            consumer_timeout_ms=5000
        )
        console.print(f"[green]✓ Connected to Kafka[/green]")
        console.print(f"[cyan]Subscribed to topics: {', '.join(topics)}[/cyan]")
        return consumer
    except Exception as e:
        console.print(f"[red]Error connecting to Kafka: {e}[/red]")
        console.print("[yellow]Make sure Kafka is running and connectors are set up[/yellow]")
        return None


def analyze_event(key, value, topic, partition, offset):
    """Analyze and display a CDC event."""
    console.print("\n" + "=" * 70)
    console.print(f"[bold cyan]Event from: {topic}[/bold cyan]")
    console.print(f"[dim]Partition: {partition}, Offset: {offset}[/dim]")
    
    # Show key
    console.print("\n[yellow]KEY (used as Elasticsearch _id):[/yellow]")
    if key:
        console.print(JSON(json.dumps(key, indent=2)))
    else:
        console.print("[red]null (TOMBSTONE)[/red]")
    
    # Show value
    console.print("\n[yellow]VALUE (event envelope):[/yellow]")
    if value is None:
        console.print("[red]null - This is a TOMBSTONE message[/red]")
        console.print("[yellow]→ Elasticsearch should DELETE the document[/yellow]")
        return
    
    console.print(JSON(json.dumps(value, indent=2)))
    
    # Extract and explain key fields
    payload = value.get("payload", {}) 
    
    # Extract CDC metadata
    op = payload.get("__op") # "c", "u", "d"
    deleted = payload.get("__deleted") # "true" or "false"
    table = payload.get("__table") # "users", "orders"
    
    # Determine index name from table
    index_name = table.lower()
    
    # Document ID
    doc_id = payload.get("id")
    
    # Handle CREATE or UPDATE
    if deleted == "false" and op in ("c", "u"):
        es.index(index=index_name, id=doc_id, document=payload)
        console.print(f"[green]Indexed document {doc_id} into {index_name}[/green]")
    
    # Handle DELETE
    elif deleted == "true" or op == "d":
        es.delete(index=index_name, id=doc_id, ignore=[404])
        console.print(f"[red]Deleted document {doc_id} from {index_name}[/red]")
    
    console.print("\n[bold cyan]Event Analysis:[/bold cyan]")
    
    # Operation type
    op_descriptions = {
        'c': 'CREATE (INSERT) - New record created',
        'u': 'UPDATE - Existing record modified',
        'd': 'DELETE - Record removed',
        'r': 'READ (SNAPSHOT) - Initial table snapshot'
    }
    console.print(f"[green]Operation:[/green] '{op}' - {op_descriptions.get(op, 'Unknown')}")
    
    # Source info
    #console.print(f"[green]Source Table:[/green] {source.get('schema')}.{source.get('table')}")
    #console.print(f"[green]Database:[/green] {source.get('db')}")
    #console.print(f"[green]Timestamp:[/green] {source.get('ts_ms')} ({time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(source.get('ts_ms', 0)/1000))} UTC)")
    
    # Data states
    if before:
        console.print("\n[yellow]BEFORE state (previous values):[/yellow]")
        console.print(JSON(json.dumps(before, indent=2)))
    
    if after:
        console.print("\n[green]AFTER state (new values):[/green]")
        console.print(JSON(json.dumps(after, indent=2)))
        console.print("\n[cyan]→ This would be the Elasticsearch document body[/cyan]")
    
    # Elasticsearch mapping
    console.print("\n[bold cyan]Elasticsearch Indexing:[/bold cyan]")
    if op == 'c' or op == 'r':
        console.print(f"[green]Action:[/green] CREATE document")
        console.print(f"[green]Document _id:[/green] {key}")
        console.print(f"[green]Document body:[/green] {after}")
    elif op == 'u':
        console.print(f"[yellow]Action:[/yellow] UPDATE document")
        console.print(f"[yellow]Document _id:[/yellow] {key}")
        console.print(f"[yellow]New body:[/yellow] {after}")
        console.print(f"[dim]Previous body:[/dim] {before}")
    elif op == 'd':
        console.print(f"[red]Action:[/red] DELETE document")
        console.print(f"[red]Document _id:[/red] {key}")
        console.print(f"[dim]Last known state:[/dim] {before}")


def show_statistics(events):
    """Show statistics about consumed events."""
    if not events:
        console.print("[yellow]No events consumed yet[/yellow]")
        return
    
    stats_table = Table(title="Event Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    
    total = len(events)
    ops = [e.get('op') for e in events if e]
    
    stats_table.add_row("Total Events", str(total))
    stats_table.add_row("CREATE (c)", str(ops.count('c')))
    stats_table.add_row("UPDATE (u)", str(ops.count('u')))
    stats_table.add_row("DELETE (d)", str(ops.count('d')))
    stats_table.add_row("READ/SNAPSHOT (r)", str(ops.count('r')))
    stats_table.add_row("Tombstones", str(events.count(None)))
    
    console.print(stats_table)


def consume_and_analyze():
    """Main consumption loop."""
    consumer = create_consumer(TOPICS)
    if not consumer:
        return
    
    events = []
    
    console.print("\n[cyan]Consuming messages...[/cyan]")
    console.print("[dim]Will timeout after 5 seconds of no new messages[/dim]\n")
    
    try:
        for message in consumer:
            events.append(message.value)
            analyze_event(
                message.key,
                message.value,
                message.topic,
                message.partition,
                message.offset
            )
            
            # Ask if user wants to continue
            if len(events) >= 5:
                continue_consuming = Prompt.ask(
                    "\n[yellow]Continue consuming?[/yellow]",
                    choices=["yes", "no"],
                    default="yes"
                )
                if continue_consuming == "no":
                    break
    
    except Exception as e:
        console.print(f"\n[yellow]Consumption ended: {e}[/yellow]")
    
    finally:
        consumer.close()
        console.print("\n[green]✓ Consumer closed[/green]")
        show_statistics(events)


def export_sample_events():
    """Export sample events to a file for documentation."""
    consumer = create_consumer(TOPICS)
    if not consumer:
        return
    
    samples = []
    console.print("[cyan]Collecting sample events...[/cyan]")
    
    try:
        for message in consumer:
            samples.append({
                'topic': message.topic,
                'partition': message.partition,
                'offset': message.offset,
                'key': message.key,
                'value': message.value
            })
            
            if len(samples) >= 10:
                break
    
    except Exception:
        pass
    
    finally:
        consumer.close()
    
    if samples:
        filename = f"sample_events_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(samples, f, indent=2)
        console.print(f"\n[green]✓ Exported {len(samples)} events to {filename}[/green]")
    else:
        console.print("\n[yellow]No events to export[/yellow]")


def main():
    """Main execution."""
    console.print("[bold blue]CDC Spike - Kafka Consumer & Event Inspector[/bold blue]")
    console.print("=" * 70)
    
    explain_event_structure()
    
    console.print("\n[bold cyan]Choose an action:[/bold cyan]")
    console.print("[green]1.[/green] Consume and analyze events (interactive)")
    console.print("[green]2.[/green] Export sample events to JSON file")
    console.print("[green]3.[/green] Show explanation and exit")
    
    choice = Prompt.ask("\n[bold]Your choice[/bold]", choices=["1", "2", "3"])
    
    if choice == "1":
        consume_and_analyze()
    elif choice == "2":
        export_sample_events()
    else:
        console.print("\n[green]Done![/green]")


if __name__ == "__main__":
    main()