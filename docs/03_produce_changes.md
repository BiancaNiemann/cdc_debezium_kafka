# CDC Change Producer

The Python script lets you **manually create database changes** (INSERT,
UPDATE, DELETE) so you can **see CDC events being produced** by Debezium
in real time.

Think of this script as a **remote control** for triggering database
changes on purpose.

------------------------------------------------------------------------

## High-level overview (in plain English)

1.  You run this Python script
2.  The script changes data in PostgreSQL
3.  **Debezium watches PostgreSQL**
4.  When data changes, Debezium emits CDC events
5.  Those events can be sent to Kafka (or another system)

👉 **The Python script does NOT talk to Debezium directly**\
👉 It only talks to PostgreSQL

Debezium does the watching.

------------------------------------------------------------------------

## What does this script actually do?

This script:

-   Connects to a PostgreSQL database
-   Shows you a menu in the terminal
-   Lets you:
    -   Insert users
    -   Insert orders
    -   Update users or orders
    -   Delete users or orders
    -   Run bulk operations
    -   View current data

Every action you choose creates **real database changes**.

------------------------------------------------------------------------

## Why are we doing INSERT, UPDATE, DELETE?

Because **CDC only works when data changes**.

Each operation triggers a CDC event:

  Database Action   CDC Event
  ----------------- ---------------------
  INSERT            Create (`op = 'c'`)
  UPDATE            Update (`op = 'u'`)
  DELETE            Delete (`op = 'd'`)

This script is designed to **intentionally trigger all of them**.

------------------------------------------------------------------------

## What is Debezium? (Very simple explanation)

**Debezium is a tool that listens to database changes.**

Instead of querying the database again and again, Debezium:

-   Reads the database **transaction log**
-   Detects every change
-   Converts each change into an **event**
-   Sends that event to a streaming platform (usually Kafka)

You can think of Debezium as:

> "A microphone placed next to the database that records everything that
> changes."

------------------------------------------------------------------------

## How does Debezium work here? (Step-by-step)

### 1. PostgreSQL writes to its WAL

PostgreSQL keeps a **Write-Ahead Log (WAL)**.\
This log records **every change** made to the database.

INSERT, UPDATE, DELETE → all go into the WAL.

------------------------------------------------------------------------

### 2. Debezium reads the WAL

Debezium connects to PostgreSQL and continuously reads the WAL.

It does **not**: - Poll tables - Run SELECT queries

It only reads the log.

------------------------------------------------------------------------

### 3. Debezium turns changes into events

For each change, Debezium creates a structured event that contains:

-   The operation type (`c`, `u`, `d`)
-   The table name
-   The primary key
-   The row **before** the change (for updates/deletes)
-   The row **after** the change (for inserts/updates)

------------------------------------------------------------------------

### 4. Events are published (usually to Kafka)

Debezium sends these events to Kafka topics like:

    dbserver1.public.users
    dbserver1.public.orders

Other systems can then: - Update caches - Sync databases - Trigger
analytics pipelines - Power real-time dashboards

------------------------------------------------------------------------

## How this script fits into Debezium

This script's job is very simple:

> **Create database changes on demand**

That's it.

  Component       Responsibility
  --------------- --------------------
  Python script   Changes data
  PostgreSQL      Stores data + WAL
  Debezium        Detects changes
  Kafka           Distributes events

------------------------------------------------------------------------

## Script structure (simple explanation)

### Database connection

``` python
psycopg2.connect(**DB_PARAMS)
```

Connects Python to PostgreSQL.

------------------------------------------------------------------------

### Menu system

The script shows an interactive menu using `rich`:

-   You choose an option
-   The corresponding function runs

------------------------------------------------------------------------

### Insert functions

-   `insert_user()`
-   `insert_order()`

These create **INSERT CDC events** (`op = 'c'`).

------------------------------------------------------------------------

### Update functions

-   `update_user_email()`
-   `update_order_status()`

These create **UPDATE CDC events** (`op = 'u'`).\
Debezium records **before and after values**.

------------------------------------------------------------------------

### Delete functions

-   `delete_user()`
-   `delete_order()`

These create **DELETE CDC events** (`op = 'd'`).\
Debezium also emits **tombstone messages** for Kafka cleanup.

------------------------------------------------------------------------

## What this script does NOT do

Important clarification:

❌ It does NOT configure Debezium\
❌ It does NOT send messages to Kafka\
❌ It does NOT parse CDC events

It only **triggers** them.

------------------------------------------------------------------------

## How to use this

1.  Start PostgreSQL
2.  Start Debezium and Kafka
3.  Run this script:

``` bash
python src/cdc_spike/produce_changes.py
```

4.  Choose menu options
5.  Watch CDC events appear in Debezium/Kafka

------------------------------------------------------------------------



