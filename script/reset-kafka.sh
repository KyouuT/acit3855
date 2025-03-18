#!/bin/bash
echo " Resetting Kafka cluster ID"
rm -f /kafka/kafka-logs-kafka/meta.properties
echo "Resetting Kafka cluster ID has been completed"

echo "Starting Kafka"
start-kafka.sh &

echo "Creating Kafka topic: events"

if /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server kafka:9092 | grep -q "^events$"; then
    echo "Topic 'events' already exists."
else
    echo "Creating Kafka topic: events"
    /opt/kafka/bin/kafka-topics.sh --create --topic events --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
    echo "Topic 'events' created successfully!"
fi

wait