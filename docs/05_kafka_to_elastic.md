# Kafka to Elasticsearch Bridge 🌉

A real-time CDC (Change Data Capture) bridge service that streams database changes from Kafka to Elasticsearch for instant searchability and analytics.

## What Does This Do?

This service acts as a bridge between your database changes and Elasticsearch:

1. **Listens** to CDC events from Kafka topics (database changes)
2. **Processes** CREATE, UPDATE, and DELETE operations
3. **Indexes** the data into Elasticsearch in real-time
4. **Enables** instant search and analytics in Kibana

```
PostgreSQL → Debezium → Kafka → [This Bridge] → Elasticsearch → Kibana
```

## Features

- ✅ Real-time indexing of database changes
- ✅ Support for all CDC operations (Create, Update, Delete)
- ✅ Automatic index creation with proper mappings
- ✅ Live statistics dashboard during operation
- ✅ Graceful shutdown handling
- ✅ Idempotent operations (safe to replay)
- ✅ Batch processing for efficiency

## Prerequisites

Make sure these services are running (should all start up with Docker compose):

- **Kafka** (localhost:9092)
- **Elasticsearch** (localhost:9200)
- **PostgreSQL** with Debezium CDC (optional, for generating events)

## Usage

### Start the Bridge

```bash
python src/cdc_spike/kafka_to_elasticsearch.py
```

The service will:
- Connect to Kafka and Elasticsearch
- Create necessary indices (users, orders)
- Start processing CDC events
- Display live statistics

### Monitor Progress

While running, you'll see a live dashboard showing:
- Number of creates, updates, deletes
- Total events processed
- Errors (if any)
- Time since last event

### Stop the Service

Press `Ctrl+C` for graceful shutdown. The service will:
- Finish processing current batch
- Commit Kafka offsets
- Display final statistics

## Configuration

Edit these constants in the script to match your environment:

```python
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
KAFKA_TOPICS = ['cdc.public.users', 'cdc.public.orders']
ELASTICSEARCH_HOST = 'http://localhost:9200'
```

## Supported Tables

Currently configured for:

### Users
- `id` (integer)
- `username` (keyword)
- `email` (keyword)
- `created_at` (date)
- `is_active` (boolean)

### Orders
- `id` (integer)
- `user_id` (integer)
- `product_name` (text)
- `quantity` (integer)
- `total_price` (float)
- `status` (keyword)
- `created_at` (date)

## Viewing Your Data

### Kibana
Visit [http://localhost:5601](http://localhost:5601) to:
- Explore indexed data
- Create visualizations
- Build dashboards

### Elasticsearch API
Query directly:
```bash
# Get all users
curl http://localhost:9200/users/_search?pretty

# Get all orders
curl http://localhost:9200/orders/_search?pretty
```

## How It Works

### CDC Event Processing

1. **CREATE/READ**: Indexes new document
2. **UPDATE**: Updates existing document (creates if missing)
3. **DELETE**: Removes document from index
4. **TOMBSTONE**: Kafka tombstone events trigger deletion

### Message Format

The service expects Debezium CDC format:
```json
{
  "payload": {
    "op": "c",  // Operation: c=create, u=update, d=delete, r=read
    "before": { ... },
    "after": { "id": 1, "username": "john", ... }
  }
}
```

### Error Handling

- Failed operations are logged and counted
- Processing continues on errors
- Graceful degradation for missing documents

## Troubleshooting

### "Cannot connect to Elasticsearch"
```bash
# Check if Elasticsearch is running
curl http://localhost:9200

# Start with Docker
cd docker && docker-compose up -d elasticsearch
```

### "Cannot connect to Kafka"
```bash
# Check if Kafka is running
docker ps | grep kafka

# Start with Docker
cd docker && docker-compose up -d kafka
```

### No events appearing
- Verify CDC is configured in PostgreSQL
- Check Kafka topics exist: `kafka-topics --list --bootstrap-server localhost:9092`
- Ensure Debezium connector is running

## Performance Notes

- Processes up to 100 messages per poll
- Uses `refresh=True` for immediate searchability (trades performance for real-time)
- Commits offsets after each batch
- For production, consider tuning refresh intervals

