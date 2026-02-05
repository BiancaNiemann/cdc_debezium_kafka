#### In a bash terminal
- source .venv/bin/activate
- cd docker
- docker compose up -d
- python src/cdc_spike/setup_database.py (Creates a dummy database of users and orders)
- python scripts/setup_connectors.py

#### Open a new bash terminal called make changes
- source .venv/bin/activate
- python src/cdc_spike/produce_changes.py

#### Open another bash terminal called cdc events
- source .venv/bin/activate
- python src/cdc_spike/consume_kafka.py

#### Open another bash terminal called elastic events
- source .venv/bin/activate
- python src/cdc_spike/kafka_to_elasticsearch.py

#### Open kibana on http://localhost:5601 and select Users under discovery

- in changes terminal create a new user or do an update on a user
- in cdc events select 1 so kafka consumes and analyzes event
- Have a look in elastic event tab, should see a change change appear
- Check kibana on localhost and should see the change appear there
