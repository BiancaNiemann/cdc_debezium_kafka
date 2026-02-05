# CDC Spike: PostgreSQL → Debezium → Kafka → Elasticsearch

**Learning-focused proof of concept demonstrating Change Data Capture (CDC) flow**

## 🎯 What This Is

This project demonstrates how database changes automatically propagate through a CDC pipeline. When you INSERT, UPDATE, or DELETE a row in PostgreSQL, Debezium captures that change and sends it through Kafka, where it can be indexed in Elasticsearch.

### Simple Explanation

Think of it like this:
- **PostgreSQL** = Your filing cabinet where documents are stored
- **Debezium** = A camera watching the filing cabinet
- **Kafka** = A delivery service for change notifications
- **Elasticsearch** = A searchable index that gets updated automatically

## 🏗️ Architecture

```
PostgreSQL (WAL)
    ↓
Debezium PostgreSQL Connector
    ↓
Kafka Topics
    ↓
[Your Indexing Service adapters would go here]
    ↓
Elasticsearch
```

## 📋 Prerequisites

- GitHub account (for Codespaces)
- Basic understanding of databases
- No local setup required!

## 🚀 Quick Start (GitHub Codespaces)

### Step 1: Create the Repository

1. Create a new repository on GitHub
2. Clone this code into it
3. Click "Code" → "Open with Codespaces" → "New codespace"

### Step 2: Wait for Environment Setup

The devcontainer will automatically:
- Install Python 3.11
- Install Docker-in-Docker
- Install `uv` package manager
- Forward necessary ports

### Step 3: Install Dependencies

```bash
# Initialize Python environment with uv
source ~/.bashrc
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Step 4: Start Services

```bash
cd docker
docker-compose up -d

# Wait for all services to be healthy (takes ~30 seconds)
docker-compose ps
```

### Step 5: Setup Database

```bash
cd ..
python src/cdc_spike/setup_database.py
```

This creates two tables (`users` and `orders`) with sample data.

### Step 6: Start Debezium Connector

```bash
python src/cdc_spike/setup_connectors.py
```

This configures Debezium to watch the PostgreSQL database.

### Step 7: Make Changes & Observe

```bash
# Terminal 1: Make database changes
python src/cdc_spike/produce_changes.py

# Terminal 2: Watch CDC events
python src/cdc_spike/consume_kafka.py

# Terminal 3: Watch Elasticsearch
python src/cdc_spike/kafka_to_elasticsearch.py
```

## 📚 Understanding the Flow

### 1. PostgreSQL Configuration

PostgreSQL needs these settings for CDC:
```sql
wal_level = logical
max_wal_senders = 10
max_replication_slots = 10
```

Our `docker-compose.yml` sets these automatically.

### 2. Debezium Event Structure

When you change data, Debezium publishes events like this:

**INSERT Event:**
```json
{
  "op": "c",
  "before": null,
  "after": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com"
  },
  "source": {
    "db": "testdb",
    "table": "users",
    "ts_ms": 1705683234567
  }
}
```

**UPDATE Event:**
```json
{
  "op": "u",
  "before": {
    "id": 1,
    "email": "alice@example.com"
  },
  "after": {
    "id": 1,
    "email": "alice@newmail.com"
  }
}
```

**DELETE Event:**
```json
{
  "op": "d",
  "before": {
    "id": 1,
    "username": "alice"
  },
  "after": null
}
```

Followed by a **TOMBSTONE** (null value) for topic compaction.

### 3. Kafka Topics

Debezium creates topics with this pattern:
- `cdc.public.users` - Changes to users table
- `cdc.public.orders` - Changes to orders table

### 4. Elasticsearch Mapping

Your indexing service adapters need to:

1. **Extract the Key** → Use as Elasticsearch `_id`
2. **Check operation type:**
   - `op='c'` or `op='r'` → CREATE document with `after` data
   - `op='u'` → UPDATE document with `after` data
   - `op='d'` → DELETE document
   - `value=null` → TOMBSTONE, confirm deletion

## 🔍 What Your Adapters Must Handle

### Kafka Adapter (`kafka/`)

**Input:** Raw Kafka messages from Debezium topics

**Must Handle:**
- Deserialization of JSON events
- Key extraction for document ID
- Partition/offset management
- Error handling for malformed messages

**Example:**
```python
def process_kafka_message(message):
    key = message.key()  # Document ID
    value = message.value()  # Event envelope
    
    if value is None:
        # TOMBSTONE - confirm deletion
        return DeleteOperation(doc_id=key)
    
    op = value.get('op')
    after = value.get('after')
    
    if op in ['c', 'r']:
        return CreateOperation(doc_id=key, body=after)
    elif op == 'u':
        return UpdateOperation(doc_id=key, body=after)
    elif op == 'd':
        return DeleteOperation(doc_id=key)
```

### Debezium Adapter (`debezium/`)

**Input:** Debezium event envelope

**Must Parse:**
- Operation type (`op` field)
- Before/after states
- Source metadata
- Timestamp information

**Edge Cases to Handle:**

1. **Snapshot Events** (`op='r'`)
   - Initial table data
   - Treat like CREATE operations

2. **Tombstones** (null value)
   - Sent after deletes
   - Confirm document removal

3. **Schema Changes**
   - New columns appear in `after`
   - Removed columns missing from `after`
   - Handle gracefully or reject

4. **Transaction Boundaries**
   - Multiple events in one transaction
   - May need to batch updates

## 📊 Observing the System

### Check Kafka Topics

```bash
docker exec cdc-kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### View Elasticsearch Indices

```bash
curl http://localhost:9200/_cat/indices?v
```

### View Elasticsearch Documents

```bash
# View all users
curl http://localhost:9200/cdc.public.users/_search?pretty

# View specific document
curl http://localhost:9200/cdc.public.users/_doc/1?pretty
```

### Monitor Connector Status

```bash
curl http://localhost:8083/connectors/postgres-source-connector/status | json_pp
```

## 🧪 Test Scenario

###  Basic CRUD Operations

1. INSERT a user → Check Elasticsearch has new document
2. UPDATE the user's email → Check document updated
3. DELETE the user → Check document removed


Observe how Debezium handles the new field.

## 📁 Project Structure

```
cdc-spike/
├── .devcontainer/
│   └── devcontainer.json          # Codespaces configuration
├── configs/
│   ├── debezium-postgres-connector.json
│   └── elasticsearch-sink-connector.json
├── docker/
│   └── docker-compose.yml         # All services
├── src/cdc_spike/
│   ├── setup_database.py          # Create tables & data
│   ├── setup_connectors.py        # Configure Debezium
│   ├── produce_changes.py         # Make DB changes
│   └── consume_kafka.py           # Inspect events
|   └── kafka_to_elasticsearch.py  # Watch changes in elasticsearch
├── docs/
│   └── Notes on each script plus connectors and tool explanations
├── pyproject.toml                 # Python dependencies
└── README.md                      # This file
```

## 🤝 Sharing the Environment

To let other team members use this setup:

### Option 1: GitHub Codespaces (Recommended)

1. Commit all changes to the repository
2. Push to GitHub
3. Share the repository URL
4. Team members open in Codespaces

**Advantages:**
- Identical environment for everyone
- No local setup required
- Works on any OS

### Option 2: Dev Container Locally

Team members with VS Code + Docker:

1. Clone the repository
2. Open in VS Code
3. Click "Reopen in Container"

### Option 3: Manual Setup

For team members who prefer local setup:

```bash
# Install dependencies
pip install uv
uv venv
source .venv/bin/activate
uv pip install -e .

# Start services
cd docker
docker-compose up -d

# Run src/cdc_spike as normal
```

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs postgres
docker-compose logs kafka
docker-compose logs kafka-connect
```

### Kafka Connect Not Responding

```bash
# Restart Kafka Connect
docker-compose restart kafka-connect

# Wait 30 seconds, then check
curl http://localhost:8083/
```

### No Events Appearing

1. Check connector status:
   ```bash
   curl http://localhost:8083/connectors/postgres-source-connector/status
   ```

2. Verify PostgreSQL replication slot:
   ```bash
   docker exec cdc-postgres psql -U postgres -d testdb -c "SELECT * FROM pg_replication_slots;"
   ```

3. Check Kafka topics exist:
   ```bash
   docker exec cdc-kafka kafka-topics --bootstrap-server localhost:9092 --list
   ```

## 🎓 Learning Resources

- [Debezium Documentation](https://debezium.io/documentation/)
- [Kafka Connect Deep Dive](https://docs.confluent.io/platform/current/connect/)
- [PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html)

## 📝 Next Steps

1. **Review** `docs/FINDINGS.md` for adapter-specific requirements
2. **Experiment** with different data changes
3. **Document** any edge cases you discover
4. **Design** your adapter interfaces based on observations

## 🎯 Success Criteria

- ✅ Database changes appear in Kafka
- ✅ Event structure is well understood
- ✅ Elasticsearch mapping is clear
- ✅ Team can run and modify the setup
- ✅ Adapter requirements are documented

