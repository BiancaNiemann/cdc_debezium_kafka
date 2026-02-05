# Kafka Connect Connector Setup Script 
## What is this?
This Python script sets up the **Debezium PostgreSQL connector** via the Kafka Connect REST API.

### What it does:
1. Waits for Kafka Connect to be ready
2. Lists existing connectors
3. Deletes any existing connector with the same name
4. Creates the Debezium PostgreSQL source connector
5. Checks the connector status and ensures it is running
6. Lists Kafka topics created by the connector

### Why it matters:
- This is how changes in your Postgres tables are captured and sent to Kafka
- Prepares Kafka topics so downstream systems (like Elasticsearch or Python consumers) can read them

### How to run:
```bash
python setup_connectors.py
```

### Next steps:
1. Make database changes: `produce_changes.py`
2. Inspect messages in Kafka: `consume_kafka.py`

This script is beginner-friendly and automates creating the source connector for your CDC pipeline.