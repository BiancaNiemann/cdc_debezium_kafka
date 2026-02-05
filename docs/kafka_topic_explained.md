# Understanding Kafka Topics in CDC Pipeline

A beginner-friendly guide to understanding how Kafka topics work in this Change Data Capture (CDC) system.

## Simple Analogy 🎯

Think of Kafka **topics** like different **mailboxes** or **channels** on Slack:

- **Topic = A specific channel for a specific type of message**
- Just like you might have `#engineering`, `#sales`, `#general` channels in Slack
- In this project, we have `cdc.public.users` and `cdc.public.orders` topics

## The Complete Flow

### 1. **Debezium Watches Your Database** 👀

Debezium is connected to your PostgreSQL database and watches for changes:
- Someone inserts a new user → Debezium sees it
- Someone updates an order → Debezium sees it
- Someone deletes a record → Debezium sees it

### 2. **Debezium Sends Events to Kafka Topics** 📮

When Debezium sees a change, it creates an **event** (a message) and sends it to a specific Kafka **topic**:

```
PostgreSQL Table          →    Kafka Topic
─────────────────────────────────────────────────
public.users              →    cdc.public.users
public.orders             →    cdc.public.orders
```

**The naming pattern**: `cdc.{schema}.{table_name}`
- `cdc` = change data capture
- `public` = database schema name
- `users` or `orders` = table name

### 3. **The Bridge Reads from These Topics** 📖

The Python script subscribes to these topics:

```python
KAFKA_TOPICS = ['cdc.public.users', 'cdc.public.orders']
```

This means: "Hey Kafka, send me all messages from these two mailboxes!"

### 4. **What Does an Event Look Like?** 📧

When a user is created in PostgreSQL, Debezium sends an event like this to the `cdc.public.users` topic:

```json
{
  "payload": {
    "op": "c",
    "after": {
      "id": 123,
      "username": "john_doe",
      "email": "john@example.com",
      "created_at": "2026-02-05T10:30:00Z",
      "is_active": true
    }
  }
}
```

**Operation Types:**
- `c` = **Create** (new record inserted)
- `u` = **Update** (existing record modified)
- `d` = **Delete** (record removed)
- `r` = **Read** (initial snapshot)

### 5. **Bridge Processes and Sends to Elasticsearch** 🔄

The bridge script:
1. Reads this event from the `cdc.public.users` topic
2. Sees it's a "create" operation (`op: "c"`)
3. Extracts the data from the `after` field
4. Sends it to Elasticsearch index called `users`

## Visual Flow 🌊

```
┌─────────────┐
│ PostgreSQL  │
│             │
│ INSERT INTO │
│ users ...   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Debezium   │ ← Watches database
│  Connector  │
└──────┬──────┘
       │ Creates event
       ▼
┌─────────────────────────┐
│  Kafka                  │
│                         │
│  Topic: cdc.public.users│ ← Event stored here
│  [Event 1]              │
│  [Event 2]              │
│  [Event 3]              │
└──────┬──────────────────┘
       │
       │ Bridge subscribes
       ▼
┌─────────────┐
│ Python      │
│ Bridge      │ ← Reads events
└──────┬──────┘
       │ Indexes data
       ▼
┌─────────────┐
│ Elastic-    │
│ search      │
│             │
│ Index: users│ ← Data searchable here
└─────────────┘
```

## Why Use Topics? 🤔

1. **Organization**: Different types of data go to different topics
2. **Scalability**: Multiple services can read from the same topic
3. **Reliability**: Events are stored in Kafka until processed
4. **Replay**: If the bridge crashes, it can pick up where it left off
5. **Decoupling**: Database and Elasticsearch don't need to know about each other

## Real-World Example 💡

Let's say you run an e-commerce site:

1. **Customer places order** 
   - PostgreSQL `orders` table updated with new row

2. **Debezium captures change** 
   - Creates an event with order details

3. **Event sent to Kafka** 
   - Event goes to `cdc.public.orders` topic
   - Stored safely in Kafka (won't be lost)

4. **Bridge reads event** 
   - Python script consumes from `cdc.public.orders` topic
   - Processes the order data

5. **Data indexed in Elasticsearch** 
   - Order becomes searchable in Elasticsearch `orders` index
   - Appears instantly in Kibana dashboards

**The magic**: All of this happens in **milliseconds**, so your Elasticsearch is almost always in sync with your database! ⚡

## Topic Details in This Project

### `cdc.public.users`
Events for the `users` table containing:
- User ID
- Username
- Email
- Account creation time
- Active status

### `cdc.public.orders`
Events for the `orders` table containing:
- Order ID
- User ID (who placed it)
- Product name
- Quantity
- Total price
- Order status
- Order creation time

## How to View Topics

### List all Kafka topics:
```bash
kafka-topics --list --bootstrap-server localhost:9092
```

### View messages in a topic:
```bash
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic cdc.public.users \
  --from-beginning
```

### Check topic details:
```bash
kafka-topics --describe --topic cdc.public.users \
  --bootstrap-server localhost:9092
```

## Consumer Groups

The bridge uses a **consumer group** called `elasticsearch-indexer`:

```python
group_id='elasticsearch-indexer'
```

**What's a consumer group?**
- A named group of consumers working together
- Kafka tracks which messages this group has already processed
- If the bridge restarts, it continues from the last processed message
- No duplicate processing (each event processed once)

## Common Questions

### Q: What happens if the bridge stops?
**A:** Events pile up in Kafka topics. When you restart the bridge, it picks up where it left off and processes all missed events.

### Q: Can multiple services read from the same topic?
**A:** Yes! You could have one service indexing to Elasticsearch and another sending email notifications, both reading from `cdc.public.orders`.

### Q: How long are events stored in Kafka?
**A:** By default, Kafka retains messages for 7 days (configurable). After processing, events can be deleted or kept for replay.

### Q: What if I add a new table to PostgreSQL?
**A:** Configure Debezium to watch it, and it will create a new topic (e.g., `cdc.public.products`). Then add that topic to the bridge's `KAFKA_TOPICS` list.

## Further Reading

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Debezium Documentation](https://debezium.io/documentation/)
- [CDC Pattern Explained](https://en.wikipedia.org/wiki/Change_data_capture)

---

**Remember**: Topics are just organized message queues. They help route the right data to the right places efficiently! 📬
