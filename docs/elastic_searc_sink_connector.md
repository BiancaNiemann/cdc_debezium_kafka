# Elasticsearch Sink Connector 

## What is this?
This configuration creates an **Elasticsearch Sink Connector**.

In simple terms:

👉 It **watches Kafka topics**
👉 **Reads messages from Kafka** (data from Postgres via Debezium)
👉 **Writes that data into Elasticsearch**

This is usually the **final step** in a CDC (Change Data Capture) pipeline.

---

## Big Picture (What’s happening overall)

```
Postgres tables
   ↓ (Debezium watches changes)
Kafka topics
   ↓ (Elasticsearch Sink Connector reads)
Elasticsearch indexes
```

This connector:
- Reads data from **Kafka topics**
- Writes data into **Elasticsearch**
- Makes it searchable in real time

---

## Which Kafka topics does it read?

```json
"topics": "cdc.public.users,cdc.public.orders"
```

It will read from:
- `cdc.public.users`
- `cdc.public.orders`

These topics are created by the **Debezium Postgres source connector**.

---

## Connection to Elasticsearch

```json
"connection.url": "http://elasticsearch:9200"
```

This tells the connector:
- Where Elasticsearch is running
- How to send data there

`elasticsearch` is the **Docker service name**, not localhost.

---

## Document type and keys

```json
"type.name": "_doc",
"key.ignore": "false",
"transforms.extractKey.field": "id"
```

- Each row becomes an Elasticsearch **document**
- The document ID comes from the `id` field
- This ensures updates/deletes affect the correct document

---

## Schema handling

```json
"schema.ignore": "false"
```

- Schema info from Kafka is **kept**
- Elasticsearch can interpret field types correctly

---

## Handling deletes and malformed documents

```json
"behavior.on.null.values": "delete",
"behavior.on.malformed.documents": "warn"
```

- If Kafka sends a tombstone (row deleted in Postgres) → the document is deleted in Elasticsearch
- Malformed documents trigger a warning instead of breaking the connector

---

## Transforms (simplifying messages)

```json
"transforms": "unwrap,extractKey"
```

1. **unwrap**
   - Removes the Debezium envelope
   - Keeps only the row data
   - Handles deletes properly (`rewrite` mode)

2. **extractKey**
   - Pulls the `id` field from the Kafka message key
   - Uses it as the Elasticsearch document ID

This ensures documents in Elasticsearch match rows in Postgres.

---

## Kafka message format (JSON)

```json
"key.converter": "org.apache.kafka.connect.json.JsonConverter",
"value.converter": "org.apache.kafka.connect.json.JsonConverter",
"key.converter.schemas.enable": "false",
"value.converter.schemas.enable": "true"
```

- Data is read as **JSON**
- Keeps the schema for Elasticsearch mapping

---

## Summary (one paragraph)

This connector reads all messages from the Kafka topics created by the Debezium Postgres source connector (`users` and `orders`) and writes them into Elasticsearch as searchable documents. It handles inserts, updates, and deletes in real time and ensures each document in Elasticsearch matches the corresponding row in Postgres.

---

## Next step (typical)

After this connector is running:
1. Verify data appears in Elasticsearch
2. You can search, visualize, or use dashboards in Kibana
3. New changes in Postgres automatically appear in Elasticsearch

You do NOT need to manually create Elasticsearch indexes.

