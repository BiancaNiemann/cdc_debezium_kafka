
# CDC Connector Setup

## What is this script?

This script **automatically sets up and checks a data pipeline** that tracks changes in a database and sends them into Kafka.

You can think of it like this:

> **“Whenever something changes in the database, this setup makes sure those changes are noticed, captured, and sent along so other systems can use them.”**

It removes the need to manually configure connectors through a web interface or command line.

---

## Key Concepts (No Tech Speak)

Before we go step-by-step, here’s a simple translation of the main components:

| Term | What it means in plain English |
|-----|--------------------------------|
| Kafka Connect | A service that moves data between systems |
| Connector | A “plug” that knows how to read from or write to a system |
| Debezium | A tool that watches a database for changes |
| REST API | A way for programs to talk to each other using web requests |
| Topic | A named stream where messages are sent |

---

## What does the script do overall?

At a high level, the script:

1. Waits for Kafka Connect to be ready
2. Checks which connectors already exist
3. Deletes an old connector if needed
4. Creates a new connector from a config file
5. Confirms that the connector is running
6. Shows which Kafka topics were created
7. Tells you what to do next

---

## Step-by-Step Breakdown

### 1. The script starts and prints a title

When the script runs, it prints a friendly heading so you know what’s happening:

```
CDC Spike – Connector Setup
```

This is purely for clarity and logging.

---

### 2. It waits for Kafka Connect to be ready

**Why?**  
Kafka Connect might still be starting up.

**What happens?**
- The script checks every 2 seconds
- It keeps trying for up to 2 minutes
- If Kafka Connect responds, the script continues
- If not, the script stops safely

**Real-world analogy:**  
Like refreshing a website until it loads before clicking anything.

---

### 3. It checks which connectors already exist

The script asks Kafka Connect:

> “What connectors are already set up?”

This helps avoid duplicates or conflicts.

---

### 4. It prepares to create a new connector

The script loads a configuration file:

```
config/debezium-postgres-connector.json
```

This file describes:
- Which database to watch
- What data to capture
- Where to send the changes

**Important:**  
The script does **not** hardcode these details — it reads them from a file so they’re easy to change.

---

### 5. If a connector already exists, it deletes it

If a connector with the same name already exists:
- The old one is deleted
- The script waits briefly
- A clean version is created

**Why this matters:**  
It prevents outdated or broken configurations from lingering.

---

### 6. It creates the connector

The script sends the configuration to Kafka Connect using a web request.

If successful:
- It confirms creation
- It prints the connector configuration in a readable format

If it fails:
- It prints clear error messages

---

### 7. It checks if the connector is actually running

Creating a connector doesn’t always mean it works.

So the script asks:

> “Is the connector running?”

Possible outcomes:
- ✅ RUNNING → all good
- ⚠ PAUSED or FAILED → something needs attention

---

### 8. It lists Kafka topics

Kafka automatically creates topics when data starts flowing.

The script:
- Looks inside the Kafka container
- Lists available topics
- Shows what data streams now exist

**Analogy:**  
Like checking which folders were created after installing software.

---

### 9. It prints next steps

At the end, the script tells you exactly what to do next:

1. Make changes in the database  
2. Watch those changes appear in Kafka  

This helps guide testing and demos.

---

## Why this script is useful

✅ Repeatable setup  
✅ No manual clicking  
✅ Clear logging  
✅ Safe checks before actions  
✅ Easy to explain and demo  

It’s especially useful for:
- Proofs of concept
- Demos
- Local development
- Team onboarding

---

### How to run:
```bash
python src/cdc_spike/setup_connectors.py
```
