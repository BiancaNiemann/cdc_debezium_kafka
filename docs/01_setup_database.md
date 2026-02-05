# PostgreSQL Setup Script

## What is this?
This Python script sets up the PostgreSQL database for the CDC pipeline.

### What it does:
1. Waits for PostgreSQL to be ready
2. Creates two tables: `users` and `orders`
3. Inserts sample data into both tables
4. Displays the current data in a nice table format using Rich

### Why it matters:
- Prepares your database so Debezium can capture changes
- Ensures there is initial data to stream to Kafka and Elasticsearch

### How to run:
```bash
python src/cdc_spike/setup_database.py
```

### Next steps:
1. Run Debezium connector: `src/cdc_spike/setup_connectors.py`
2. Make changes: `src/cdc_spike/produce_changes.py`
3. Inspect Kafka: `src/cdc_spike/consume_kafka.py`

This script is perfect for quickly initializing your CDC environment with test data.