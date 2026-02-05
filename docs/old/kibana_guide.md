# Kibana Real-Time CDC Visualization Guide

## Overview

This guide shows you how to see database changes appear in Kibana in real-time!

## Architecture

```
PostgreSQL                     Kibana (You!)
    ↓                              ↑
Debezium                           |
    ↓                              |
Kafka                         Elasticsearch
    ↓                              ↑
kafka_to_elasticsearch.py ─────────┘
(Bridge Service)
```

## Setup Steps

### Step 1: Install Elasticsearch Dependency

If you haven't already:

```bash
# Make sure virtual environment is active
source .venv/bin/activate

# Install/update dependencies
uv pip install -e .
```

### Step 2: Ensure All Services Are Running

```bash
cd docker
docker-compose ps

# All services should show (healthy)
# If not:
docker-compose up -d
sleep 30  # Wait for services to be ready
```

### Step 3: Setup Database (if not done)

```bash
cd ..
python src/cdc_spike/setup_database.py
```

### Step 4: Setup Debezium Connector (if not done)

```bash
python src/cdc_spike/setup_connectors.py
```

### Step 5: Start the Bridge Service

This is the **key component** that moves data from Kafka to Elasticsearch:

```bash
python src/cdc_spike/kafka_to_elasticsearch.py
```

You should see:
```
✓ Elasticsearch is running
✓ Kafka is running
🚀 Bridge service started!
```

**Leave this running!** It needs to stay active to index changes.

### Step 6: Open Kibana

1. In Codespaces, you'll see a **"PORTS"** tab at the bottom
2. Find port **5601** (Kibana)
3. Click the globe icon 🌐 to open in browser
4. Or visit: `http://localhost:5601` if running locally

### Step 7: Create Data Views in Kibana

First time setup in Kibana:

1. Click the hamburger menu (☰) in top left
2. Go to **Management** → **Stack Management**
3. Under "Kibana", click **Data Views**
4. Click **"Create data view"**

**For Users Index:**
- Name: `Users`
- Index pattern: `users`
- Timestamp field: `created_at`
- Click **"Save data view to Kibana"**

**For Orders Index:**
- Name: `Orders`
- Index pattern: `orders`
- Timestamp field: `created_at`
- Click **"Save data view to Kibana"**

### Step 8: View Your Data

1. Click hamburger menu (☰)
2. Go to **Analytics** → **Discover**
3. Select **"Users"** or **"Orders"** from the data view dropdown
4. You should see your data!

## Making Changes and Watching in Real-Time

### Open Multiple Windows

You'll want **THREE** windows/panels:

1. **Terminal 1**: Bridge service (already running)
2. **Terminal 2**: Make changes
3. **Browser**: Kibana

### Make a Change

In Terminal 2:

```bash
python src/cdc_spike/produce_changes.py
```

Choose an operation, like:
- `1` - INSERT new user
- Enter username: `john_doe`
- Enter email: `john@example.com`

### Watch It Happen

**In Terminal 1 (Bridge Service):**
```
Creates         3
Updates         0
Deletes         0
Total Events    3
```

**In Kibana:**
1. Make sure you're in **Discover**
2. Set time range to **"Last 15 minutes"** (top right)
3. Click **Refresh** button (or enable auto-refresh)
4. **You'll see the new user appear!** 🎉

## Cool Things to Try

### 1. Watch an UPDATE

**Terminal 2:**
```bash
python src/cdc_spike/produce_changes.py
# Choose: 3 - UPDATE user email
# Select a user
# Enter new email
```

**Kibana:**
- Click refresh
- Find the user document
- Click the expand arrow (▶) next to it
- You'll see the email has changed!

### 2. Watch a DELETE

**Terminal 2:**
```bash
python src/cdc_spike/produce_changes.py
# Choose: 5 - DELETE user
# Select a user
# Confirm deletion
```

**Kibana:**
- Click refresh
- The document is gone!
- Check Terminal 1 - you'll see the delete count increased

### 3. Bulk Operations

**Terminal 2:**
```bash
python src/cdc_spike/produce_changes.py
# Choose: 7 - Bulk operations
```

**Kibana:**
- Watch as multiple documents appear at once
- See the bridge service stats update rapidly

## Creating Visualizations

### Example: Orders by Status

1. Go to **Analytics** → **Visualize Library**
2. Click **"Create visualization"**
3. Choose **"Pie"** chart
4. Select **Orders** data view
5. Configure:
   - **Slice by**: `status.keyword`
   - **Size**: Count
6. Click **"Save and return"**

Now whenever you change order statuses, the pie chart updates!

### Example: Orders Over Time

1. Create new visualization
2. Choose **"Line"** chart
3. Select **Orders** data view
4. Configure:
   - **Horizontal axis**: `created_at` (Date histogram)
   - **Vertical axis**: Count
5. Save it

## Verifying Data via Command Line

### Check Elasticsearch Directly

```bash
# List all indices
curl http://localhost:9200/_cat/indices?v

# Count users
curl http://localhost:9200/users/_count?pretty

# Count orders
curl http://localhost:9200/orders/_count?pretty

# Get a specific user (ID = 1)
curl http://localhost:9200/users/_doc/1?pretty

# Search for users with email containing "example"
curl -X GET "http://localhost:9200/users/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match": {
      "email": "example"
    }
  }
}
'
```

## Dashboard Setup (Advanced)

### Create a CDC Monitoring Dashboard

1. Go to **Analytics** → **Dashboard**
2. Click **"Create dashboard"**
3. Add these visualizations:
   - Total users (Metric)
   - Total orders (Metric)
   - Orders by status (Pie chart)
   - Orders over time (Line chart)
   - Recent users (Data table)

4. Set auto-refresh to 5 seconds

Now you have a live dashboard showing database state!

## Troubleshooting

### "No results match your search criteria" in Kibana

**Check:**
1. Is the bridge service running?
2. Is data in Elasticsearch?
   ```bash
   curl http://localhost:9200/users/_search?pretty
   ```
3. Is your time range correct? (Try "Last 7 days")
4. Did you create the data view correctly?

### Bridge Service Shows Errors

**Common issues:**

**"Elasticsearch connection failed"**
```bash
# Check Elasticsearch
curl http://localhost:9200
# Should return cluster info

# If not running:
cd docker
docker-compose restart elasticsearch
sleep 10
```

**"Kafka connection failed"**
```bash
# Check Kafka
docker exec cdc-kafka kafka-topics --list --bootstrap-server localhost:9092

# If not running:
cd docker
docker-compose restart kafka
sleep 10
```

### No New Events Appearing

**Check:**
1. Is Debezium connector running?
   ```bash
   curl http://localhost:8083/connectors/postgres-source-connector/status
   ```

2. Are there messages in Kafka?
   ```bash
   python src/cdc_spike/consume_kafka.py
   # Choose option 1 - if no messages, connector might be down
   ```

3. Restart the connector:
   ```bash
   python src/cdc_spike/setup_connectors.py
   ```

### Bridge Service Stats Not Updating

The service shows stats every second. If frozen:
- Check terminal for error messages
- Restart the bridge service (Ctrl+C, then run again)

## Performance Tips

### For High Volume Testing

If you're generating lots of changes:

1. **Increase batch size** in bridge service
2. **Disable refresh on write** for better performance (edit the script)
3. **Use bulk API** instead of individual operations

### Auto-Refresh in Kibana

Set reasonable intervals:
- **5 seconds** - Good for demos
- **10 seconds** - Good for monitoring
- **30 seconds** - Good for dashboards with heavy queries

## Real-World Scenario

### Simulate a User Journey

**Terminal 2:**
```bash
python src/cdc_spike/produce_changes.py
```

1. Create new user `sarah`
2. Create order for sarah (laptop)
3. Update order status to "shipped"
4. Update order status to "delivered"
5. Create another order (mouse)

**In Kibana:**
- Watch each change appear in real-time
- See order statuses change
- View the timeline of events

This is exactly what happens in production - database changes flow through CDC and appear in your search index instantly!

## Architecture Benefits You're Seeing

1. **Real-time**: Changes appear in seconds
2. **Reliable**: Kafka ensures no data loss
3. **Scalable**: Can handle thousands of events per second
4. **Decoupled**: Database and search index are independent

## Next Steps

Now that you see it working:

1. **Understand the flow**: Review how the bridge service works
2. **Design your adapters**: Use this pattern for your indexing service
3. **Add transformations**: Modify the bridge to transform data as needed
4. **Handle edge cases**: Add error handling, retries, etc.

## Cleaning Up

When you're done:

### Stop the Bridge Service
Press `Ctrl+C` in Terminal 1

### Stop All Services
```bash
cd docker
docker-compose down
```

### Delete Elasticsearch Data (optional)
```bash
cd docker
docker-compose down -v  # -v removes volumes (data)
```

---

**You're now seeing CDC in action!** Database changes → Debezium → Kafka → Elasticsearch → Kibana

This is the foundation for building your indexing service. The bridge script (`kafka_to_elasticsearch.py`) shows exactly what your `kafka/` and `debezium/` adapters need to do!