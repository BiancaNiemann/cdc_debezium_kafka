# CDC Spike - Technical Findings & Adapter Requirements

**Document Version:** 1.0  
**Last Updated:** 2026-01-19

## Executive Summary

This document outlines the key findings from the CDC spike and specifies requirements for the `kafka/` and `debezium/` adapters in the indexing service.

## Debezium Event Structure Deep Dive

### Complete Event Anatomy

Every Debezium CDC event consists of two parts:

#### 1. Key (Message Key)

```json
{
  "id": 123
}
```

**Purpose:** Identifies the record uniquely  
**Usage:** Maps to Elasticsearch document `_id`  
**Note:** Always contains the primary key field(s)

#### 2. Value (Event Envelope)

```json
{
  "schema": { ... },
  "payload": {
    "before": { ... },
    "after": { ... },
    "source": { ... },
    "op": "c|u|d|r",
    "ts_ms": 1705683234567,
    "transaction": null
  }
}
```

### Operation Types

| Code | Operation | Before | After | Elasticsearch Action |
|------|-----------|--------|-------|---------------------|
| `c` | CREATE (INSERT) | null | populated | Create document |
| `u` | UPDATE | populated | populated | Update document |
| `d` | DELETE | populated | null | Delete document |
| `r` | READ (snapshot) | null | populated | Create document |

### Field Breakdown

#### `before` Field

- **When null:** INSERT or initial snapshot
- **When populated:** UPDATE or DELETE
- **Contains:** Previous state of the record
- **Use case:** Audit trails, change tracking, conflict resolution

#### `after` Field

- **When null:** DELETE operation
- **When populated:** CREATE, UPDATE, or READ
- **Contains:** New/current state of the record
- **Use case:** Document body for Elasticsearch

#### `source` Field

Critical metadata about the change:

```json
{
  "source": {
    "version": "2.5.0.Final",
    "connector": "postgresql",
    "name": "dbserver1",
    "ts_ms": 1705683234567,
    "snapshot": "false",
    "db": "testdb",
    "sequence": "[null,\"23456789\"]",
    "schema": "public",
    "table": "users",
    "txId": 789,
    "lsn": 23456789,
    "xmin": null
  }
}
```

**Key fields:**
- `ts_ms` - Change timestamp (milliseconds since epoch)
- `db` / `schema` / `table` - Source location
- `snapshot` - "true" for initial snapshot, "false" for real-time change
- `lsn` - Log Sequence Number (PostgreSQL WAL position)
- `txId` - Transaction ID

#### `ts_ms` Field (Top-level)

- **Type:** Long (milliseconds since epoch)
- **Represents:** When Debezium processed the event
- **Note:** Different from `source.ts_ms` (when change occurred)

### Tombstone Messages

After a DELETE event, Debezium sends a tombstone:

```
Key: {"id": 123}
Value: null
```

**Purpose:** Enable Kafka log compaction  
**Handling:** Confirm deletion in Elasticsearch  
**Configuration:** Controlled by `tombstones.on.delete` setting

## Kafka Topic Structure

### Topic Naming Convention

Format: `{topic.prefix}.{schema}.{table}`

Examples:
- `cdc.public.users`
- `cdc.public.orders`

### Partitioning

- Default: Single partition per topic
- Key determines partition (using message key hash)
- Ordering guaranteed within partition

### Message Ordering

**Guaranteed:**
- Changes to same record (same key) are ordered
- Changes within same transaction maintain order

**Not Guaranteed:**
- Changes across different records
- Changes across different tables

## Adapter Requirements

### 1. Kafka Adapter (`kafka/`)

#### Responsibilities

- Connect to Kafka cluster
- Subscribe to Debezium topics
- Deserialize messages
- Handle offset management
- Pass events to Debezium adapter

#### Required Functionality

```python
class KafkaAdapter:
    def __init__(self, bootstrap_servers, topics):
        """Initialize Kafka consumer"""
        pass
    
    def consume_messages(self, callback):
        """
        Consume messages and call callback for each.
        
        Args:
            callback: Function(key, value, metadata) -> None
        """
        pass
    
    def commit_offsets(self):
        """Commit current offsets"""
        pass
    
    def handle_errors(self, error):
        """Handle Kafka-specific errors"""
        pass
```

#### Error Scenarios to Handle

1. **Connection failures**
   - Retry with exponential backoff
   - Alert on sustained failures

2. **Deserialization errors**
   - Log malformed message
   - Skip and continue (or dead letter queue)

3. **Offset commit failures**
   - Retry commit
   - May result in duplicate processing

4. **Partition rebalancing**
   - Handle gracefully
   - Commit offsets before rebalance

#### Configuration Needs

```python
KAFKA_CONFIG = {
    "bootstrap_servers": ["localhost:9092"],
    "topics": ["cdc.public.users", "cdc.public.orders"],
    "group_id": "indexing-service",
    "auto_offset_reset": "earliest",  # or "latest" for production
    "enable_auto_commit": False,  # Manual commit for reliability
    "max_poll_records": 500,
    "session_timeout_ms": 30000,
}
```

### 2. Debezium Adapter (`debezium/`)

#### Responsibilities

- Parse Debezium event envelope
- Extract relevant data
- Transform to Elasticsearch operations
- Handle edge cases

#### Required Functionality

```python
class DebeziumAdapter:
    def parse_event(self, key, value):
        """
        Parse Debezium event into Elasticsearch operation.
        
        Returns:
            ESOperation object or None if tombstone
        """
        pass
    
    def extract_document_id(self, key):
        """Extract Elasticsearch document ID from key"""
        pass
    
    def extract_document_body(self, after):
        """Extract document body from 'after' field"""
        pass
    
    def should_index(self, event):
        """Determine if event should be indexed"""
        pass
```

#### Event Processing Logic

```python
def process_debezium_event(key, value):
    """Pseudo-code for event processing"""
    
    # Handle tombstone
    if value is None:
        return DeleteOperation(
            doc_id=extract_id(key),
            operation_type="TOMBSTONE"
        )
    
    payload = value.get('payload', {})
    op = payload.get('op')
    before = payload.get('before')
    after = payload.get('after')
    source = payload.get('source', {})
    
    # Determine operation
    if op in ['c', 'r']:  # Create or Read (snapshot)
        return CreateOperation(
            doc_id=extract_id(key),
            body=after,
            metadata={
                'timestamp': source.get('ts_ms'),
                'source_table': f"{source.get('schema')}.{source.get('table')}",
                'is_snapshot': source.get('snapshot') == 'true'
            }
        )
    
    elif op == 'u':  # Update
        return UpdateOperation(
            doc_id=extract_id(key),
            body=after,
            previous=before,  # Optional: for audit
            metadata={
                'timestamp': source.get('ts_ms'),
                'changed_fields': detect_changes(before, after)
            }
        )
    
    elif op == 'd':  # Delete
        return DeleteOperation(
            doc_id=extract_id(key),
            last_known_state=before,  # Optional: for audit
            metadata={
                'timestamp': source.get('ts_ms')
            }
        )
    
    else:
        raise UnknownOperationError(f"Unknown op: {op}")
```

#### Edge Cases to Handle

##### 1. Schema Evolution

**Scenario:** Column added to table

```json
// Before schema change
"after": {
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}

// After schema change (new column 'phone')
"after": {
  "id": 1,
  "username": "alice",
  "email": "alice@example.com",
  "phone": null
}
```

**Handling:**
- Elasticsearch will automatically add new fields
- Existing documents won't have new field (expected)
- Consider re-indexing if field is critical

##### 2. Snapshot Events

**Scenario:** Initial table snapshot

```json
{
  "op": "r",
  "before": null,
  "after": {...},
  "source": {
    "snapshot": "true"
  }
}
```

**Handling:**
- Treat exactly like CREATE
- May want to track snapshot completion
- High volume during initial snapshot

##### 3. Tombstones

**Scenario:** Delete followed by tombstone

```
Event 1 - Delete:
{
  "op": "d",
  "before": {...},
  "after": null
}

Event 2 - Tombstone:
Key: {"id": 123}
Value: null
```

**Handling:**
- First event deletes document
- Second event (tombstone) should be idempotent
- Don't error if document already deleted

##### 4. Complex Primary Keys

**Scenario:** Composite primary key

```json
{
  "id": 123,
  "tenant_id": 456
}
```

**Handling:**
- Concatenate fields for Elasticsearch ID
- Example: `"123_456"` or hash the combination
- Must be consistent and deterministic

##### 5. Large Payloads

**Scenario:** Table with many columns or large text fields

**Handling:**
- Check Kafka message size limits
- Consider field filtering in Debezium config
- May need to increase `max.message.bytes`

##### 6. Transaction Markers

**Scenario:** Multiple events in one transaction

```json
{
  "transaction": {
    "id": "txn-789",
    "total_order": 5,
    "data_collection_order": 2
  }
}
```

**Handling:**
- May want to batch updates
- Consider transaction boundaries for consistency
- Not all operations include transaction info

## Elasticsearch Indexing Strategy

### Index Naming

Two options:

**Option 1: Mirror Kafka Topics**
- Index: `cdc.public.users`
- Pro: Clear 1:1 mapping
- Con: Non-standard naming

**Option 2: Simplified Names**
- Index: `users`
- Pro: Cleaner
- Con: Need mapping config

### Document ID Strategy

```python
def generate_document_id(key):
    """
    Generate Elasticsearch document ID from message key.
    
    Single field: Use value directly
    Multiple fields: Concatenate with separator
    """
    if len(key) == 1:
        return str(list(key.values())[0])
    else:
        # Composite key: "123_456"
        return "_".join(str(v) for v in key.values())
```

### Mapping Considerations

**Dynamic Mapping (Simpler):**
- Let Elasticsearch infer types
- Works well for simple schemas
- May need explicit mappings for dates, geo, etc.

**Explicit Mapping (Better):**
```json
{
  "mappings": {
    "properties": {
      "id": {"type": "integer"},
      "username": {"type": "keyword"},
      "email": {"type": "keyword"},
      "created_at": {"type": "date"},
      "is_active": {"type": "boolean"}
    }
  }
}
```

### Update vs. Upsert

Recommended: Use upsert for all operations

```python
# Elasticsearch Python client
es.update(
    index="users",
    id=doc_id,
    body={
        "doc": after_data,
        "doc_as_upsert": True
    }
)
```

Benefits:
- Handles CREATE and UPDATE with same code
- No error if document doesn't exist
- Simpler logic

### Delete Handling

```python
# Check if document exists first (optional)
if es.exists(index="users", id=doc_id):
    es.delete(index="users", id=doc_id)
else:
    # Already deleted or never existed (tombstone idempotency)
    pass
```

## Performance Considerations

### Batching

**Recommendation:** Batch Elasticsearch operations

```python
from elasticsearch import helpers

def batch_index(operations, batch_size=500):
    """Batch Elasticsearch operations"""
    batch = []
    
    for op in operations:
        batch.append(convert_to_es_action(op))
        
        if len(batch) >= batch_size:
            helpers.bulk(es, batch)
            batch = []
    
    # Process remaining
    if batch:
        helpers.bulk(es, batch)
```

### Backpressure

If Elasticsearch can't keep up:

1. **Slow down Kafka consumption**
2. **Increase batch size** (more efficient)
3. **Add more Elasticsearch nodes**
4. **Buffer operations** (with caution)

### Monitoring Metrics

Track these metrics:

- **Kafka consumer lag** - Are we falling behind?
- **Events processed per second**
- **Elasticsearch indexing latency**
- **Error rate** - Failed operations
- **Tombstone count** - Track deletions

## Testing Recommendations

### Unit Tests

Test adapter logic with sample events:

```python
def test_create_event():
    event = {
        "op": "c",
        "after": {"id": 1, "username": "test"}
    }
    key = {"id": 1}
    
    operation = debezium_adapter.parse_event(key, event)
    
    assert operation.type == "CREATE"
    assert operation.doc_id == "1"
    assert operation.body["username"] == "test"
```

### Integration Tests

1. **End-to-end flow**
   - Insert in PostgreSQL
   - Verify Elasticsearch document

2. **Update handling**
   - Update in PostgreSQL
   - Verify Elasticsearch document updated

3. **Delete handling**
   - Delete in PostgreSQL
   - Verify Elasticsearch document removed

4. **Snapshot handling**
   - Start with populated table
   - Verify all documents indexed

### Load Testing

Simulate production load:

1. Generate high volume of changes
2. Monitor consumer lag
3. Check Elasticsearch indexing keeps up
4. Verify no data loss

## Common Pitfalls

### 1. Not Handling Tombstones

**Problem:** Tombstones cause NullPointerException  
**Solution:** Always check if value is null before processing

### 2. Ignoring Operation Type

**Problem:** Treating all events as creates  
**Solution:** Always check `op` field and handle accordingly

### 3. Not Committing Offsets

**Problem:** Reprocessing same events after restart  
**Solution:** Commit offsets after successful Elasticsearch write

### 4. Blocking on Elasticsearch

**Problem:** Slow Elasticsearch writes block Kafka consumption  
**Solution:** Use async operations or batching

### 5. Schema Mismatch

**Problem:** Elasticsearch rejects document due to type conflict  
**Solution:** Use explicit mappings or transform data

## Sample Event Library

### INSERT Event (op='c')

```json
{
  "key": {
    "id": 4
  },
  "value": {
    "schema": {...},
    "payload": {
      "before": null,
      "after": {
        "id": 4,
        "username": "dave",
        "email": "dave@example.com",
        "created_at": 1705683234567890,
        "is_active": true
      },
      "source": {
        "version": "2.5.0.Final",
        "connector": "postgresql",
        "name": "dbserver1",
        "ts_ms": 1705683234567,
        "snapshot": "false",
        "db": "testdb",
        "schema": "public",
        "table": "users",
        "txId": 789,
        "lsn": 23456789
      },
      "op": "c",
      "ts_ms": 1705683234789,
      "transaction": null
    }
  }
}
```

### UPDATE Event (op='u')

```json
{
  "key": {
    "id": 4
  },
  "value": {
    "payload": {
      "before": {
        "id": 4,
        "username": "dave",
        "email": "dave@example.com",
        "is_active": true
      },
      "after": {
        "id": 4,
        "username": "dave",
        "email": "dave@newmail.com",
        "is_active": true
      },
      "source": {
        "ts_ms": 1705683240123,
        "db": "testdb",
        "schema": "public",
        "table": "users"
      },
      "op": "u",
      "ts_ms": 1705683240234
    }
  }
}
```

### DELETE Event (op='d')

```json
{
  "key": {
    "id": 4
  },
  "value": {
    "payload": {
      "before": {
        "id": 4,
        "username": "dave",
        "email": "dave@newmail.com"
      },
      "after": null,
      "source": {
        "ts_ms": 1705683250123,
        "db": "testdb",
        "table": "users"
      },
      "op": "d",
      "ts_ms": 1705683250234
    }
  }
}
```

### Tombstone

```json
{
  "key": {
    "id": 4
  },
  "value": null
}
```

### Snapshot Event (op='r')

```json
{
  "key": {
    "id": 1
  },
  "value": {
    "payload": {
      "before": null,
      "after": {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com"
      },
      "source": {
        "snapshot": "true",
        "ts_ms": 1705680000000
      },
      "op": "r",
      "ts_ms": 1705680000123
    }
  }
}
```

## Conclusion

### Key Takeaways

1. **Debezium events have predictable structure** - Parse `op`, `before`, `after`
2. **Tombstones must be handled** - They're not errors, they're cleanup
3. **Kafka guarantees ordering per key** - Not across keys
4. **Snapshots are CREATE operations** - Treat them identically
5. **Batching improves performance** - Don't index one-by-one

### Recommended Adapter Architecture

```
KafkaAdapter
  ↓ consumes messages
  ↓ deserializes JSON
  ↓
DebeziumAdapter
  ↓ parses event envelope
  ↓ extracts operation & data
  ↓
ElasticsearchAdapter
  ↓ batches operations
  ↓ indexes documents
  ↓
Commit offsets
```

### Next Steps for Implementation

1. Implement `KafkaAdapter` with offset management
2. Implement `DebeziumAdapter` event parsing
3. Add Elasticsearch client with bulk operations
4. Write unit tests for each adapter
5. Integration test with real Debezium
6. Load test to determine capacity

---

**Questions?** Review the sample events in this spike or run `consume_kafka.py` to see real events.