# Change Data Capture (CDC) Stack Overview

This repository demonstrates a **Change Data Capture (CDC)** pipeline using **PostgreSQL → Debezium → Kafka → Elasticsearch**, with **Kibana** for visualization.

The goal of this README is to explain:
- What each component does
- How they work together
- How connectors fit into the picture

This is written for learning and spike purposes, not production hardening.

---

## 1. What is Change Data Capture (CDC)?

**Change Data Capture** is a pattern where you capture *changes* in a database (inserts, updates, deletes) and stream them to other systems in near real-time.

Key idea:
> CDC streams **changes**, not full tables.

Instead of polling the database, CDC reads the database’s **transaction log** and emits events when data changes.

---

## 2. PostgreSQL (Source of Truth)

PostgreSQL is the **source database**.

### How CDC works in Postgres
Postgres writes every data change to a **Write-Ahead Log (WAL)**. Debezium reads this log.

Important configuration:
- `wal_level=logical`
- Replication slots enabled

Postgres itself does **not** send events. It only records changes. Debezium does the rest.

---

## 3. Debezium (CDC Engine)

**Debezium** is a CDC platform built on top of Kafka Connect.

### What Debezium does
- Connects to PostgreSQL
- Reads the WAL (logical replication)
- Converts row-level changes into **events**
- Publishes those events to Kafka topics

Debezium does **not** store data long-term. It only emits events.

### Example CDC event
A single row update becomes a structured event containing:
- Before state
- After state
- Operation type (c, u, d)
- Metadata (table, timestamp, transaction id)

---

## 4. Kafka (Event Backbone)

**Apache Kafka** is the event streaming platform at the center of the system.

### What Kafka does
- Receives CDC events from Debezium
- Stores them durably in topics
- Allows multiple consumers to read the same events independently

Kafka acts as a **buffer and decoupling layer**.

### Topics
Debezium creates topics automatically, typically named like:

```
cdc.public.users
cdc.public.orders
```

Each topic represents a table.

### Important Kafka concepts
- **Topic**: A stream of events
- **Partition**: Parallelism and ordering unit
- **Offset**: Position in the stream

Kafka does *not* understand your data — it only moves bytes.

---

## 5. Kafka Connect (Integration Runtime)

**Kafka Connect** is a framework for running connectors.

Debezium runs **inside Kafka Connect**, not as a standalone service.

Kafka Connect provides:
- REST API (port 8083)
- Offset management
- Scaling and fault tolerance

Think of Kafka Connect as:
> A managed runtime for moving data in and out of Kafka

---

## 6. Elasticsearch (Search & Indexing)

**Elasticsearch** is used as a downstream system to index CDC events.

### What Elasticsearch does here
- Stores denormalized documents
- Allows fast search and filtering
- Supports analytics-style queries

Each Postgres row becomes an Elasticsearch document.

CDC events are translated into:
- Index document (create/update)
- Delete document (delete)

---

## 7. Kibana (Visualization)

**Kibana** is the UI for Elasticsearch.

It allows you to:
- Inspect indexed documents
- Explore data visually
- Debug CDC pipelines

Kibana is optional and not required for CDC to function.

---

## 8. How Connectors Work

Connectors are **plugins** that Kafka Connect runs.

There are two main types:

### Source Connectors
- Read data **into Kafka**
- Example: Debezium PostgreSQL connector

### Sink Connectors
- Read data **from Kafka**
- Write it to another system
- Example: Elasticsearch sink connector

---

## 9. Debezium PostgreSQL Source Connector

This connector:
1. Connects to Postgres
2. Creates a replication slot
3. Reads WAL changes
4. Emits CDC events into Kafka topics

Key properties:
- Database connection info
- Tables to capture
- Topic naming

Important behavior:
- Initial snapshot happens **once**
- After that, only changes are streamed

---

## 10. Elasticsearch Sink (Custom Bridge)

In this project, a **custom bridge service** consumes Kafka events and indexes them into Elasticsearch.

Flow:
```
Kafka Topic → Consumer → Transform → Elasticsearch Index
```

Responsibilities:
- Deserialize CDC events
- Detect operation type (create/update/delete)
- Apply the correct Elasticsearch action

This logic could also be implemented using an off-the-shelf Elasticsearch Sink Connector.

---

## 11. End-to-End Data Flow

```
PostgreSQL
   ↓ (WAL)
Debezium (Source Connector)
   ↓
Kafka Topics
   ↓
Consumer / Sink
   ↓
Elasticsearch
   ↓
Kibana
```

Each step is decoupled and can fail or restart independently.

---

## 12. Key Takeaways

- CDC streams **changes**, not data dumps
- Kafka is the backbone, not the brain
- Debezium reads database logs, not tables
- Kafka Connect manages connectors and offsets
- Elasticsearch is just one of many possible sinks

This architecture scales well, but even in small setups it teaches real-world event-driven design.

---

## 13. Common Gotchas (Dev Environment)

- JVM memory pressure (Kafka, Connect, ES)
- Debezium only emits events on **actual changes**
- Restarting without clearing offsets won’t replay data
- Elasticsearch needs kernel tuning (`vm.max_map_count`)

---

## 14. When to Use This Pattern

Use CDC when:
- You need near real-time data sync
- You want to avoid database polling
- Multiple downstream systems need the same changes

Avoid it when:
- Simple batch jobs are sufficient
- Operational complexity is not acceptable

---

Happy streaming 🚀

