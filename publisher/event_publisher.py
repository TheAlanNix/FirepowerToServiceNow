#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module is used to consume RabbitMQ events, then publish them to ServiceNow.
"""

import json
import os
import time

import pika
import requests

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class EventQueue():
    """
    A class to handle event queuing.
    """

    def __init__(self, host, queue_name="events", debug=False):
        """
        Initialize the EventQueue object.
        """

        self._debug = debug
        self._rabbit_mq_channel = None
        self._rabbit_mq_connection = None
        self._rabbit_mq_host = host
        self._rabbit_mq_queue = None
        self._rabbit_mq_queue_name = queue_name

    def close(self):
        """
        Close the RabbitMQ connection.
        """

        # Close the connection
        self._rabbit_mq_connection.close()

    def create_channel(self):
        """
        Create a RabbitMQ channel.
        """

        # Create RabbitMQ connection parameters
        connection_parameters = pika.ConnectionParameters(heartbeat=600, host=self._rabbit_mq_host)

        # Build the RabbitMQ connection
        self._rabbit_mq_connection = pika.BlockingConnection(connection_parameters)

        # Get a channel for the RabbitMQ connection
        self._rabbit_mq_channel = self._rabbit_mq_connection.channel()

    def create_queue(self):
        """
        Create a RabbitMQ queue.
        """

        # If we have a channel, create a queue
        if self._rabbit_mq_channel:

            # Declare a new queue for events
            self._rabbit_mq_queue = self._rabbit_mq_channel.queue_declare(queue=self._rabbit_mq_queue_name)

    def queue_data(self, data):
        """
        Put the provided data onto a RabbitMQ queue.
        """

        # Publish the event to RabbitMQ
        self._rabbit_mq_channel.basic_publish(exchange="", routing_key=self._rabbit_mq_queue_name, body=json.dumps(data))

        print(" [x] Event published to queue.")

        # If debugging enabled, print details
        if self._debug:
            print(f"Event details:\n{json.dumps(data, indent=4)}")


class ServiceNowPublisher():
    """
    A class to publish events to ServiceNow.
    """

    def __init__(self, debug=False):
        """
        Initialize the ServiceNowPublisher object.
        """

        self._debug = debug
        self._snow_tenant = os.getenv("SNOW_TENANT")
        self._snow_username = os.getenv("SNOW_USERNAME")
        self._snow_password = os.getenv("SNOW_PASSWORD")

    def submit_to_snow(self, ch, method, properties, body):
        """
        Submit the event to ServiceNow as an incident.
        """

        # Load the body as JSON
        body = json.loads(body)

        # Build the ServiceNow API URL
        snow_url = f"https://{self._snow_tenant}.service-now.com/api/now/table/incident"

        # Specify headers for the ServiceNow POST request
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        data = {
            "category": "Network",
            "impact": 2,
            "urgency": 2,
            "short_description": "Firepower Alert: {}".format(body['event_name']),
            "description": json.dumps(body, indent=4)
        }

        # Send the data to ServiceNow
        response = requests.post(snow_url, auth=(self._snow_username, self._snow_password), headers=headers, data=json.dumps(data))

        print(f" [x]Event published to ServiceNow. HTTP response code: {response.status_code}")

        # If debugging enabled, print details
        if self._debug:
            print(f"Headers: {response.headers}\nResponse: {response.text}")


if __name__ == "__main__":

    # Instantiate an EventQueue object
    event_queue = EventQueue(os.getenv("RABBIT_MQ_HOST"), "events")

    # Wait for RabbitMQ to become available
    while True:
        try:
            # Create a RabbitMQ channel if not already done
            if not event_queue._rabbit_mq_channel:
                print(" [x] Creating RabbitMQ channel...")
                event_queue.create_channel()
                print(" [x] RabbitMQ channel created.")

            # Create a RabbitMQ queue if not already done
            if not event_queue._rabbit_mq_queue:
                print(" [x] Creating RabbitMQ queue...")
                event_queue.create_queue()
                print(" [x] RabbitMQ queue created.")

            break
        except:
            print(" [x] Unable to create RabbitMQ channel. Retrying...")
            # If we weren't able to create the channel, wait X seconds and try again
            time.sleep(5)

    # Instantiate the ServiceNowPublisher object
    servicenow_publisher = ServiceNowPublisher()

    # Set up an event consumer on the provided channel, and start consuming
    event_queue._rabbit_mq_channel.basic_consume(queue="events",
                                                 on_message_callback=servicenow_publisher.submit_to_snow,
                                                 auto_ack=True)
    event_queue._rabbit_mq_channel.start_consuming()
