# Quick Start Guide - 5 Minutes to CDC

## Prerequisites
- GitHub account
- Web browser
- That's it!

## Steps (For Real, It's This Simple)

### 1. Open in Codespaces (1 minute)

1. Push all this code to a GitHub repository
2. Go to the repository on GitHub
3. Click green "Code" button
4. Click "Codespaces" tab
5. Click "Create codespace on main"

☕ Wait 1-2 minutes while your environment sets up automatically.

### 2. Install Python Dependencies (1 minute)

Open the terminal in Codespaces and run:

```bash
# Activate the shell configuration
source ~/.bashrc

# Create virtual environment with uv
uv venv

# Activate it
source .venv/bin/activate

# Install dependencies
uv pip install -e .
```

### 3. Start All Services (2 minutes)

```bash
# Go to docker folder
cd docker

# Start everything
docker-compose up -d

# Check services are healthy (wait until all show "healthy")
watch -n 2 docker-compose ps
```

Press `Ctrl+C` when all services show "(healthy)".

### 4. Setup Database (30 seconds)

```bash
# Go back to project root
cd ..

# Create tables and sample data
python src/cdc_spike/setup_database.py
```

You should see a nice table with sample users and orders!

### 5. Start Debezium (30 seconds)

```bash
python src/cdc_spike/setup_connectors.py
```

You should see:
- ✓ Kafka Connect is ready!
- ✓ Successfully created postgres-source-connector
- List of Kafka topics

### 6. See It In Action! (1 minute)

Open TWO terminals:

**Terminal 1 - Watch Events:**
```bash
python src/cdc_spike/consume_kafka.py
# Choose option 1
```

**Terminal 2 - Make Changes:**
```bash
python src/cdc_spike/produce_changes.py
# Choose option 1 (INSERT new user)
# Enter username: "testuser"
# Enter email: "test@example.com"
```

**Watch Terminal 1** - You'll see the CDC event appear in real-time! 🎉

## What Just Happened?

1. You created a user in PostgreSQL
2. Debezium noticed the change in the database log
3. It published a message to Kafka
4. Your consumer script caught it and displayed it

This is CDC in action!

## Next Steps

### Make More Changes

Try all the operations:
- INSERT new records
- UPDATE existing ones
- DELETE records
- Watch the different event types

### Explore the Data

```bash
# See what's in PostgreSQL
docker exec -it cdc-postgres psql -U postgres -d testdb -c "SELECT * FROM users;"

# See Kafka topics
docker exec cdc-kafka kafka-topics --bootstrap-server localhost:9092 --list

# See Elasticsearch (once you set it up)
curl http://localhost:9200/_cat/indices?v
```

### View Kibana (Optional)

Open your browser to the forwarded port 5601 (Codespaces will show you the URL).

This gives you a web UI to explore Elasticsearch.

## Troubleshooting

### Services Not Starting?

```bash
cd docker
docker-compose down
docker-compose up -d
```

### Can't Connect to Postgres?

Wait 30 seconds - it takes a moment to initialize.

```bash
docker-compose logs postgres
```

### Kafka Connect Not Ready?

```bash
docker-compose restart kafka-connect
sleep 30
python src/cdc_spike//setup_connectors.py
```

### "Module not found" Error?

Make sure you activated the virtual environment:

```bash
source .venv/bin/activate
```

## Sharing With Team

### Option 1: Share the Codespace

Just share your GitHub repository URL! Anyone can:
1. Open the repository
2. Click "Code" → "Codespaces" → "Create codespace"
3. Follow steps 2-6 above

### Option 2: Share as Dev Container

Team members with VS Code + Docker Desktop installed:
1. Clone the repository
2. Open in VS Code
3. When prompted, click "Reopen in Container"
4. Follow steps 2-6 above

## That's It!

You now have a working CDC pipeline. Changes flow automatically from PostgreSQL → Debezium → Kafka → (your service would go here) → Elasticsearch.

**Ready to build?** Check `docs/FINDINGS.md` for what your adapters need to handle.

**Have questions?** The scripts have lots of comments explaining what they do.