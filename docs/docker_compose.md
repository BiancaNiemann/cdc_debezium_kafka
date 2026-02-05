# CDC Docker Compose 

## What is this?
This `docker-compose.yml` file sets up a **Change Data Capture (CDC) pipeline** using Docker. It includes Postgres, Kafka, Debezium connectors, Elasticsearch, and Kibana. Everything is ready to watch database changes and push them to Elasticsearch.

---

## Services Overview

### 1. PostgreSQL (Database)
- Container name: `cdc-postgres`
- Stores your data in `testdb`
- Configured for **CDC (Change Data Capture)** using logical replication
- Exposes port `5432` for connections
- Data persists in `postgres-data` volume

### 2. Zookeeper (Kafka Coordinator)
- Container name: `cdc-zookeeper`
- Coordinates Kafka brokers
- Exposes port `2181`
- Required by Kafka to manage cluster state

### 3. Kafka (Message Broker)
- Container name: `cdc-kafka`
- Receives data changes from Debezium connectors
- Exposes ports `9092` and `29092`
- Depends on Zookeeper to be healthy
- Auto-creates topics for Debezium

### 4. Kafka Connect (Runs Connectors)
- Container name: `cdc-kafka-connect`
- Runs Debezium source connectors and Elasticsearch sink connector
- Depends on Postgres and Kafka being healthy
- Exposes port `8083` for REST API
- Reads connector configs from `./configs` folder

### 5. Elasticsearch (Search Engine)
- Container name: `cdc-elasticsearch`
- Indexes data from Kafka
- Exposes ports `9200` (HTTP) and `9300` (Transport)
- Java memory is limited to 512 MB for container stability
- Data persists in `es-data` volume

### 6. Kibana (Web UI for Elasticsearch)
- Container name: `cdc-kibana`
- Optional UI for viewing and searching indexed data
- Depends on Elasticsearch being healthy
- Exposes port `5601`

### 7. pgAdmin (Optional)
- Currently commented out
- Would provide a web UI for Postgres at port `5050`

---

## How it works (High-Level Flow)

```
Postgres tables
   ↓ (Debezium connector in Kafka Connect)
Kafka topics
   ↓ (Elasticsearch Sink Connector)
Elasticsearch indexes
   ↓ (Optional) Kibana
```

- Any changes in Postgres tables are automatically captured
- Changes are sent to Kafka topics
- Elasticsearch sink reads from Kafka and updates indexes
- Kibana allows you to view the indexed data

---

## Volumes
- `postgres-data` → persists Postgres database files
- `es-data` → persists Elasticsearch index data

---

## Notes for Beginners
- Start the services in order: Postgres → Kafka → Kafka Connect → Elasticsearch → Kibana
- Debezium connectors should be configured after Postgres and Kafka are healthy
- No need to manually create tables in Elasticsearch; the sink connector handles this
- pgAdmin is optional and can be enabled if needed

This setup is great for learning CDC and streaming data pipelines with Docker.

