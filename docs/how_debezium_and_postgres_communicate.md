# CDC with PostgreSQL & Debezium

This readme explains **Change Data Capture (CDC)** using:

-   PostgreSQL
-   Debezium
-   Kafka
-   Kafka Connect
-   Python (CDC change producer + consumer)

This README is written for **beginners** and explains **how Debezium
listens to PostgreSQL** step by step.

------------------------------------------------------------------------

## What problem does this solve?

Normally, applications **poll databases** to detect changes.

CDC flips that idea:

> Instead of asking *"what changed?"*, the database *tells you* when
> something changes.

Debezium makes this possible.

------------------------------------------------------------------------

## High-level architecture

``` mermaid
flowchart LR
    A[Python Script] -->|SQL changes| B[(PostgreSQL)]
    B -->|WAL records| C[WAL]
    C -->|Logical replication| D[Debezium Connector]
    D -->|CDC events| E[Kafka Topics]
    E -->|Consumed by| F[Elasticsearch]

```

------------------------------------------------------------------------

## What each component does

### Python script (produce_changes,py)

-   Connects to PostgreSQL
-   Runs INSERT / UPDATE / DELETE statements
-   Has **no idea Debezium exists**

Its only job is to **change data**.

------------------------------------------------------------------------

### PostgreSQL

-   Stores your data
-   Writes every change to the **Write-Ahead Log (WAL)**

Your Postgres config enables this:

``` yaml
wal_level=logical
```

Without this, CDC does not work.

------------------------------------------------------------------------

### Write-Ahead Log (WAL)

The WAL is PostgreSQL's internal change log.

Every row change becomes a WAL entry: - INSERT - UPDATE - DELETE

Debezium reads **this**, not the tables.

------------------------------------------------------------------------

### Logical Replication Slot

Created automatically by Debezium:

``` json
"slot.name": "debezium_slot"
```

A replication slot: - Remembers how far Debezium has read - Prevents
Postgres from deleting unread WAL data

Think of it as a **bookmark** in the change log.

------------------------------------------------------------------------

### Debezium (Kafka Connect)

Runs inside this container (see docker-compose.yml):

``` yaml
image: debezium/connect:2.5
```

Debezium: - Connects to PostgreSQL - Subscribes to the WAL - Decodes
row-level changes - Converts them into CDC events

This is where Debezium is **listening**.

------------------------------------------------------------------------

### Debezium Connector Configuration (Key Lines in debezium-postgres-connector.json)

``` json
"database.hostname": "postgres",
"plugin.name": "pgoutput",
"table.include.list": "public.users,public.orders"
```

This means: - Connect to Postgres - Use logical decoding - Only listen
to selected tables

------------------------------------------------------------------------

### Kafka

Kafka acts as the **event highway**.

Debezium publishes events to topics like:

    cdc.dbserver1.public.users
    cdc.dbserver1.public.orders

------------------------------------------------------------------------

### Kafka Consumer Script

-   Subscribes to Kafka topics
-   Receives CDC events
-   Can print, transform, or forward them

This is the "other side" of CDC.

------------------------------------------------------------------------

## What happens when you insert a row?

``` mermaid
sequenceDiagram
    participant P as Python Script
    participant PG as PostgreSQL
    participant WAL as WAL
    participant D as Debezium
    participant K as Kafka

    P->>PG: INSERT INTO users
    PG->>WAL: Write change
    WAL->>D: Stream change
    D->>K: Publish CDC event
```

------------------------------------------------------------------------

## CDC event types

  Operation   Code   Meaning
  ----------- ------ ---------
  INSERT      c      Create
  UPDATE      u      Update
  DELETE      d      Delete

Debezium adds metadata such as: - operation type - table name -
timestamp - WAL position

------------------------------------------------------------------------

## Important things this project shows

✅ Applications do **not** talk to Debezium\
✅ Debezium listens independently\
✅ Any client can trigger CDC\
✅ CDC works in real time

------------------------------------------------------------------------

## What this project does NOT do

❌ No polling\
❌ No triggers\
❌ No application-level CDC logic

All changes flow naturally from the database.

------------------------------------------------------------------------

