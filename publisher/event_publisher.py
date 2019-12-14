#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module is used to import Firepower syslog events into ServiceNow
"""

import json
import os
import time

import pika
import requests

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class ServiceNowPublisher():
    """
    A class to parse Firepower syslog events.
    """

    __debug = None
    __rabbit_mq_host = None
    __snow_tenant = None
    __snow_username = None
    __snow_password = None

    def __init__(self, debug=False):
        self.__debug = debug
        self.__rabbit_mq_host = os.getenv("RABBIT_MQ_HOST")
        self.__snow_tenant = os.getenv("SNOW_TENANT")
        self.__snow_username = os.getenv("SNOW_USERNAME")
        self.__snow_password = os.getenv("SNOW_PASSWORD")

    def create_queue_channel(self):
        """
        Create a connection to RabbitMQ and return the channel.
        """

        # Create RabbitMQ connection parameters
        connection_parameters = pika.ConnectionParameters(host=self.__rabbit_mq_host)

        # Build the RabbitMQ connection
        connection = pika.BlockingConnection(connection_parameters)

        print(f" [x] Connected to RabbitMQ.")

        # Get a channel for the RabbitMQ connection
        channel = connection.channel()

        print(f" [x] Built RabbitMQ channel.")

        return channel


    def submit_to_snow(self, ch, method, properties, body):
        """
        Submit the event to ServiceNow as an incident.
        """

        # Load the body as JSON
        body = json.loads(body)

        # Build the ServiceNow API URL
        snow_url = "https://{}.service-now.com/api/now/table/incident".format(self.__snow_tenant)

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
        response = requests.post(snow_url, auth=(self.__snow_username, self.__snow_password), headers=headers, data=json.dumps(data))

        # Print logging
        print(f"Status: {response.status_code}\nHeaders: {response.headers}\nResponse: {response.json()}")


if __name__ == "__main__":

    # Create the ServiceNowPublisher object
    servicenow_publisher = ServiceNowPublisher()

    # Wait for RabbitMQ to become available
    while True:
        try:
            # Create a channel on RabbitMQ
            channel = servicenow_publisher.create_queue_channel()
            break
        except:
            print(f" [x] Unable to create RabbitMQ channel. Retrying...")
            # If we weren't able to create the channel, wait X seconds and try again
            time.sleep(5)

    # Declare a new queue for events
    channel.queue_declare(queue="events")

    # Set up an event consumer on the provided channel
    channel.basic_consume(queue="events", on_message_callback=servicenow_publisher.submit_to_snow, auto_ack=True)

    # Start consuming queued events
    channel.start_consuming()
