# Postgres Debezium Source Connector 

## What is this?
This configuration creates a **Debezium Postgres Source Connector**.

In very simple terms:

👉 It **watches your Postgres database**
👉 **Copies all existing rows** from selected tables
👉 Then **streams every change** (new rows, updates, deletes)
👉 Into **Kafka topics**, in real time

This is usually the **first step** in a CDC (Change Data Capture) pipeline.

---

## Big Picture (What’s happening overall)

```
Postgres tables
   ↓ (Debezium watches changes)
Kafka topics
   ↓ (optional sink connector)
Elasticsearch / other systems
```

This connector:
- Reads data from **Postgres**
- Writes data into **Kafka**
- Does NOT write directly to Elasticsearch

---

## What databases and tables does this watch?

- **Database name:** `testdb`
- **Tables included:**
  - `public.users`
  - `public.orders`

Only these tables are captured. Nothing else in the database is touched.

---

## What happens when this connector starts?

When you start this connector:

1. Debezium connects to Postgres
2. It takes a **snapshot** of the tables
   - This means it copies **all existing rows**
3. It sends those rows into Kafka topics
4. After the snapshot:
   - Every INSERT, UPDATE, or DELETE
   - Is streamed to Kafka instantly

So you get:
- Old data ✅
- New data ✅
- Changes in real time ✅

---

## Connector name

```json
"name": "postgres-source-connector"
```

This is just the **name Kafka Connect uses** to manage this connector.

---

## Connection to Postgres

```json
"database.hostname": "postgres",
"database.port": "5432",
"database.user": "postgres",
"database.password": "postgres",
"database.dbname": "testdb"
```

This tells Debezium:
- Where Postgres is running
- How to log in
- Which database to read from

`postgres` is the **Docker service name**, not localhost.

---

## Server name / topic naming

```json
"database.server.name": "dbserver1",
"topic.prefix": "cdc"
```

These control how Kafka topics are named.

Kafka topics will look like:

```
cdc.dbserver1.public.users
cdc.dbserver1.public.orders
```

Each table gets its own topic.

---

## Postgres logical replication

```json
"plugin.name": "pgoutput"
```

This tells Postgres to use **logical replication**, which is how Debezium reads changes without slowing the database down.

---

## Table filtering

```json
"table.include.list": "public.users,public.orders"
```

Only these tables are captured.

If a table is not listed here:
- It will be completely ignored

---

## Replication slot

```json
"slot.name": "debezium_slot"
```

A **replication slot** is how Postgres remembers:
- Which changes Debezium has already read

This prevents data loss if:
- The connector restarts
- Kafka goes down

---

## Snapshot mode (very important)

```json
"snapshot.mode": "initial"
```

This means:
- When the connector starts the first time
- It copies **all existing rows** from the tables

Without this:
- Only NEW changes would be captured
- Old data would be missed

---

## Kafka message format (JSON)

```json
"key.converter": "org.apache.kafka.connect.json.JsonConverter",
"value.converter": "org.apache.kafka.connect.json.JsonConverter",
"key.converter.schemas.enable": "false",
"value.converter.schemas.enable": "true"
```

This controls how messages look in Kafka:

- Data is sent as **JSON**
- The value includes a **schema** (field types)
- This is useful for sinks like Elasticsearch

---

## Heartbeat messages

```json
"heartbeat.interval.ms": "10000"
```

Every 10 seconds, Debezium sends a small heartbeat message.

Why this matters:
- Keeps replication slot alive
- Helps detect connection issues

---

## Deletes and tombstones

```json
"tombstones.on.delete": "true"
```

When a row is deleted:
- Debezium sends a delete event
- Then sends a **tombstone message**

This helps downstream systems (like Kafka compaction).

---

## Schema history

```json
"schema.history.internal.kafka.bootstrap.servers": "kafka:29092",
"schema.history.internal.kafka.topic": "schema-changes.testdb"
```

Debezium tracks:
- Table structure changes (ALTER TABLE, etc.)

These changes are stored in Kafka so:
- The connector can restart safely
- Schema changes are not lost

---

## Single Message Transform (SMT): unwrap

```json
"transforms": "unwrap"
```

By default, Debezium messages are very verbose.

This transform:
- **Removes the Debezium envelope**
- Sends only the actual row data

Much easier for beginners and Elasticsearch.

---

## Extra fields added to each message

```json
"transforms.unwrap.add.fields": "op,table,lsn,source.ts_ms"
```

Each Kafka message will also include:

- `op` → operation type (c = insert, u = update, d = delete)
- `table` → table name
- `lsn` → Postgres log sequence number
- `source.ts_ms` → timestamp of the change

This is very useful for debugging and analytics.

---

## Delete handling mode

```json
"transforms.unwrap.delete.handling.mode": "rewrite"
```

Instead of removing deleted rows completely:
- A delete event is rewritten
- So downstream systems (like Elasticsearch)
  can handle deletes properly

---

## Summary (one paragraph)

This connector watches the `users` and `orders` tables in Postgres, copies all existing data when it starts, then streams every insert, update, and delete into Kafka topics as JSON messages. It simplifies the data format so it is easy to send into Elasticsearch or other systems later.

---

## Next step (typical)

After this connector is running:
1. Verify Kafka topics have data
2. Start an **Elasticsearch sink connector**
3. Data appears automatically in Elasticsearch

You do NOT need to create Elasticsearch indexes manually.

