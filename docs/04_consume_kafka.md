
# CDC Event Consumer & Inspector – Plain English Guide

## What is this script?

This script listens to database change events coming from Kafka, explains what each event means, and keeps Elasticsearch in sync with those changes.

In simple terms:

“Whenever data changes in the database, this script listens to those change messages, explains them in a human-readable way, and updates Elasticsearch accordingly.”

---

## Big Picture: What problem does this solve?

Databases change constantly:
- New records are added
- Existing records are updated
- Old records are deleted

This script:
1. Listens for those changes in Kafka
2. Explains what kind of change happened
3. Updates Elasticsearch so it always matches the database

---

## Key Concepts (Plain English)

| Term | Meaning |
|----|--------|
| CDC | Watching a database for changes |
| Kafka | A system that moves event messages |
| Topic | A stream of related messages |
| Consumer | A program that reads messages |
| Debezium | Tool that turns DB changes into events |
| Elasticsearch | A fast search database |
| Index | A collection of searchable documents |

---

## What does the script do overall?

At a high level, the script:

1. Connects to Kafka
2. Subscribes to CDC topics
3. Explains how CDC events are structured
4. Reads change events one by one
5. Decides whether to create, update, or delete data
6. Syncs the change to Elasticsearch
7. Shows statistics and summaries

---

## Step-by-Step Breakdown

### 1. Explains CDC events before doing anything

The script first explains:
- What CREATE, UPDATE, and DELETE mean
- What “before” and “after” data represent
- How CDC events map to Elasticsearch documents

This makes it ideal for demos and learning.

---

### 2. Connects to Kafka

The script connects to Kafka running locally and subscribes to topics such as:
- cdc.public.users
- cdc.public.orders

If Kafka is not running, the script explains the issue and exits safely.

---

### 3. Listens for database changes

Once connected, the script waits for:
- Inserts
- Updates
- Deletes

Each database change produces an event.

---

### 4. Displays and explains each event

For every event, the script shows:
- Which table it came from
- The type of operation
- The record’s ID
- The event data in readable JSON

---

### 5. Decides what to do with Elasticsearch

Based on the event type:

INSERT → Create a document  
UPDATE → Update a document  
DELETE → Remove a document  

This keeps Elasticsearch in sync automatically.

---

### 6. Updates Elasticsearch in real time

The script:
- Uses the database ID as the document ID
- Stores the latest data as the document body
- Deletes documents when records are removed

---

### 7. Pauses and asks whether to continue

After processing a few events, the script asks whether to continue.
This prevents endless output during demos.

---

### 8. Shows a summary at the end

When finished, the script displays:
- Total events processed
- Number of creates, updates, deletes
- Number of cleanup (tombstone) events

---

## Optional Feature: Export sample events

The script can also export example events to a JSON file.
This is useful for:
- Documentation
- Debugging
- Sharing examples

---

## Why this script is useful

- Makes CDC easy to understand
- Demonstrates real-time data pipelines
- Keeps Elasticsearch in sync
- Ideal for demos and portfolios

---

### How to run:
```bash
python consume_kafka.py
```
