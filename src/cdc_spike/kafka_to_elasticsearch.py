#!/usr/bin/env python3
"""
Kafka to Elasticsearch Bridge Service

This service consumes CDC events from Kafka and indexes them into Elasticsearch.
Run this in the background to see changes appear in Kibana in real-time!

Usage:
    python src/cdc_spike/kafka_to_elasticsearch.py
"""

import json
from multiprocessing.util import info
import time
from kafka import KafkaConsumer
from elasticsearch import Elasticsearch, helpers
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
import signal
import sys

console = Console()

# Configuration
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
KAFKA_TOPICS = ['cdc.public.users', 'cdc.public.orders']
ELASTICSEARCH_HOST = 'http://localhost:9200'

# Statistics
stats = {
    'creates': 0,
    'updates': 0,
    'deletes': 0,
    'errors': 0,
    'total': 0,
    'last_event_time': None
}


class KafkaToElasticsearchBridge:
    """Bridge that moves CDC events from Kafka to Elasticsearch"""
    
    def __init__(self):
        self.es = None
        self.consumer = None
        self.running = True
        
    def connect_elasticsearch(self):
        """Connect to Elasticsearch and create indices if needed"""
        console.print("[cyan]Connecting to Elasticsearch...[/cyan]")
        
        try:
            self.es = Elasticsearch([ELASTICSEARCH_HOST])
            
            # Check connection
            info = self.es.info()
            console.print(
                f"[green]✓ Connected to Elasticsearch {info['version']['number']}[/green]"
            )
            
            # Create indices with proper mappings
            self.create_indices()
            
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Elasticsearch connection failed: {e}[/red]")
            return False
    
    def create_indices(self):
        """Create Elasticsearch indices with mappings"""
        
        indices = {
            'users': {
                'mappings': {
                    'properties': {
                        'id': {'type': 'integer'},
                        'username': {'type': 'keyword'},
                        'email': {'type': 'keyword'},
                        'created_at': {'type': 'date'},
                        'is_active': {'type': 'boolean'}
                    }
                }
            },
            'orders': {
                'mappings': {
                    'properties': {
                        'id': {'type': 'integer'},
                        'user_id': {'type': 'integer'},
                        'product_name': {'type': 'text'},
                        'quantity': {'type': 'integer'},
                        'total_price': {'type': 'float'},
                        'status': {'type': 'keyword'},
                        'created_at': {'type': 'date'}
                    }
                }
            }
        }
        
        for index_name, mapping in indices.items():
            try:
                if not self.es.indices.exists(index=index_name):
                    self.es.indices.create(index=index_name, body=mapping)
                    console.print(f"[green]✓ Created index: {index_name}[/green]")
                else:
                    console.print(f"[yellow]⚠ Index already exists: {index_name}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠ Could not create index {index_name}: {e}[/yellow]")
    
    def connect_kafka(self):
        """Connect to Kafka consumer"""
        console.print("[cyan]Connecting to Kafka...[/cyan]")
        
        try:
            self.consumer = KafkaConsumer(
                *KAFKA_TOPICS,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                group_id='elasticsearch-indexer',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                key_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                consumer_timeout_ms=1000  # 1 second timeout for graceful shutdown
            )
            
            console.print(f"[green]✓ Connected to Kafka[/green]")
            console.print(f"[cyan]Subscribed to: {', '.join(KAFKA_TOPICS)}[/cyan]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Kafka connection failed: {e}[/red]")
            return False
    
    def extract_table_name(self, topic):
        """Extract table name from Kafka topic"""
        # Topic format: cdc.public.users -> users
        parts = topic.split('.')
        return parts[-1] if parts else topic
    
    def extract_document_id(self, key):
        """Extract document ID from message key"""
        if not key:
            return None
        
        # If single field, use value directly
        if len(key) == 1:
            return str(list(key.values())[0])
        
        # If multiple fields, concatenate
        return "_".join(str(v) for v in key.values())
    
    def process_event(self, key, value, topic):
        """Process a single CDC event and index to Elasticsearch"""
        
        if value is None:
            # Tombstone - delete document
            return self.handle_delete(key, topic, is_tombstone=True)
        
        payload = value.get('payload', {})
        op = payload.get('op')
        before = payload.get('before')
        after = payload.get('after')
        
        # Determine index name from topic
        index_name = self.extract_table_name(topic)
        doc_id = self.extract_document_id(key)
        
        if not doc_id:
            console.print(f"[yellow]⚠ No document ID in message, skipping[/yellow]")
            return False
        
        try:
            if op in ['c', 'r']:  # Create or Read (snapshot)
                return self.handle_create(index_name, doc_id, after)
            
            elif op == 'u':  # Update
                return self.handle_update(index_name, doc_id, after)
            
            elif op == 'd':  # Delete
                return self.handle_delete(key, topic, is_tombstone=False)
            
            else:
                console.print(f"[yellow]⚠ Unknown operation: {op}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Error processing event: {e}[/red]")
            stats['errors'] += 1
            return False
    
    def handle_create(self, index_name, doc_id, data):
        """Handle CREATE operation"""
        try:
            self.es.index(
                index=index_name,
                id=doc_id,
                document=data,
                refresh=True  # Make immediately searchable
            )
            stats['creates'] += 1
            return True
        except Exception as e:
            console.print(f"[red]✗ Create failed: {e}[/red]")
            stats['errors'] += 1
            return False
    
    def handle_update(self, index_name, doc_id, data):
        """Handle UPDATE operation"""
        try:
            # Use upsert to handle case where document doesn't exist
            self.es.update(
                index=index_name,
                id=doc_id,
                body={
                    'doc': data,
                    'doc_as_upsert': True
                },
                refresh=True
            )
            stats['updates'] += 1
            return True
        except Exception as e:
            console.print(f"[red]✗ Update failed: {e}[/red]")
            stats['errors'] += 1
            return False
    
    def handle_delete(self, key, topic, is_tombstone=False):
        """Handle DELETE operation"""
        index_name = self.extract_table_name(topic)
        doc_id = self.extract_document_id(key)
        
        if not doc_id:
            return False
        
        try:
            # Check if document exists
            if self.es.exists(index=index_name, id=doc_id):
                self.es.delete(
                    index=index_name,
                    id=doc_id,
                    refresh=True
                )
                stats['deletes'] += 1
                return True
            else:
                # Document already deleted (idempotent)
                if not is_tombstone:
                    stats['deletes'] += 1
                return True
                
        except Exception as e:
            console.print(f"[red]✗ Delete failed: {e}[/red]")
            stats['errors'] += 1
            return False
    
    def generate_stats_table(self):
        """Generate statistics table for display"""
        table = Table(title="📊 CDC Indexing Statistics", show_header=True)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Count", style="green", justify="right")
        
        table.add_row("Creates", str(stats['creates']))
        table.add_row("Updates", str(stats['updates']))
        table.add_row("Deletes", str(stats['deletes']))
        table.add_row("Errors", str(stats['errors']), style="red" if stats['errors'] > 0 else "green")
        table.add_row("Total Events", str(stats['total']), style="bold cyan")
        
        if stats['last_event_time']:
            time_ago = int(time.time() - stats['last_event_time'])
            table.add_row("Last Event", f"{time_ago}s ago", style="yellow")
        
        return table
    
    def run(self):
        """Main processing loop"""
        
        # Setup connections
        if not self.connect_elasticsearch():
            return
        
        if not self.connect_kafka():
            return
        
        console.print("\n[bold green]🚀 Bridge service started![/bold green]")
        console.print("[cyan]Processing CDC events and indexing to Elasticsearch...[/cyan]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        # Setup signal handler for graceful shutdown
        def signal_handler(sig, frame):
            console.print("\n[yellow]Shutting down gracefully...[/yellow]")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start live display
        with Live(self.generate_stats_table(), refresh_per_second=2) as live:
            try:
                while self.running:
                    # Poll for messages with timeout
                    messages = self.consumer.poll(timeout_ms=1000, max_records=100)
                    
                    if not messages:
                        live.update(self.generate_stats_table())
                        continue
                    
                    # Process each message
                    for topic_partition, records in messages.items():
                        for message in records:
                            self.process_event(
                                message.key,
                                message.value,
                                message.topic
                            )
                            stats['total'] += 1
                            stats['last_event_time'] = time.time()
                    
                    # Commit offsets after processing batch
                    self.consumer.commit()
                    
                    # Update display
                    live.update(self.generate_stats_table())
                    
            except Exception as e:
                console.print(f"\n[red]Error in main loop: {e}[/red]")
            
            finally:
                # Cleanup
                if self.consumer:
                    self.consumer.close()
                console.print("\n[green]✓ Bridge service stopped[/green]")
                console.print(Panel(self.generate_stats_table(), title="Final Statistics"))


def check_services():
    """Check if required services are running"""
    console.print("[cyan]Checking required services...[/cyan]\n")
    
    # Check Elasticsearch
    try:
        es = Elasticsearch(ELASTICSEARCH_HOST)
        info = es.info()
        console.print(
        f"[green]✓ Elasticsearch is running (v{info['version']['number']})[/green]"
    )
    except Exception as e:
        console.print(f"[red]✗ Cannot connect to Elasticsearch: {e}[/red]")
        return False
    
    # Check Kafka
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            consumer_timeout_ms=2000
        )
        console.print("[green]✓ Kafka is running[/green]")
        consumer.close()
    except Exception as e:
        console.print(f"[red]✗ Cannot connect to Kafka: {e}[/red]")
        return False
    
    console.print()
    return True


def main():
    """Main entry point"""
    console.print("[bold blue]Kafka → Elasticsearch Bridge Service[/bold blue]")
    console.print("=" * 70)
    console.print()
    
    info = Panel(
        """[cyan]This service continuously reads CDC events from Kafka
and indexes them into Elasticsearch.

Once running, you can:
• Make changes in PostgreSQL (use produce_changes.py)
• See them appear in Kibana instantly
• Query Elasticsearch directly[/cyan]

[yellow]Kibana URL: http://localhost:5601[/yellow]
[yellow]Elasticsearch URL: http://localhost:9200[/yellow]
        """,
        title="ℹ️  Information",
        border_style="blue"
    )
    console.print(info)
    console.print()
    
    # Check services
    if not check_services():
        console.print("[red]Please start all services first:[/red]")
        console.print("[yellow]cd docker && docker-compose up -d[/yellow]\n")
        return
    
    # Start bridge
    bridge = KafkaToElasticsearchBridge()
    bridge.run()


if __name__ == "__main__":
    main()