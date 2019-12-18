#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module is used to listen for Firepower syslog events, parse them, then place them in a RabbitMQ queue.
"""

import json
import os
import re
import socketserver
import time

import pika

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

event_queue = None


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


class FirepowerSyslogHandler():
    """
    A class to parse Firepower syslog events.
    """

    def parse_event(self, data):
        """
        Parse the data using regex to extract the pertinent Firepower data.
        """

        # A Regex string for parsing Firepower IPS events generated by the FMC
        regex_string = r"([a-zA-z]{3}\s*\d{1,2}\s\d{2}:\d{2}:\d{2}) (\S*) SFIMS: \[([0-9:]*)\] \"([^\"]*)\"\s*" \
                       r"\[Impact: ([^\]]*)\]?\s*From \"([^\"]*)\" at ([a-zA-Z]{3}\s[a-zA-Z]{3}\s*\d{1,2}\s\d{2}:\d{2}:\d{2}\s\d{4}\s\S*)\s*" \
                       r"\[Classification: ([^\]]*)\]?\s*\[Priority: ([^\]]*)\]\s\{([^\}]*)\} ([0-9.]*):?([0-9]*)?\s?\(?([^\)]*)\)?->([0-9.]*)" \
                       r":?([0-9]*)?\s*\(?([^\)]*)\)?"

        # Try to parse the event, if this fails None is returned
        parsed_event = re.search(regex_string, data, re.MULTILINE)

        # If we properly parsed the event, do stuff
        if parsed_event:

            # Store the parsed data into a dict
            event_json = {
                "product": "Firepower",
                "fmc_hostname": parsed_event.group(2),
                "snort_id": parsed_event.group(3),
                "snort_name": parsed_event.group(4),
                "event_name": parsed_event.group(4),
                "event_details": f"{parsed_event.group(8)} event {parsed_event.group(4)} was detected by '{parsed_event.group(6)}'.",
                "impact_level": parsed_event.group(5),
                "sensor_name": parsed_event.group(6),
                "timestamp": parsed_event.group(7),
                "classification": parsed_event.group(8),
                "priority": parsed_event.group(9),
                "protocol": parsed_event.group(10),
                "src_ip": parsed_event.group(11),
                "src_port": parsed_event.group(12),
                "src_geo": parsed_event.group(13),
                "dst_ip": parsed_event.group(14),
                "dst_port": parsed_event.group(15),
                "dst_geo": parsed_event.group(16),
            }

            # Return the parsed event
            return event_json

        else:
            return None


class SyslogHandler(socketserver.BaseRequestHandler):
    """
    The RequestHandler class for Command Center Syslog events.
    """

    def handle(self):
        """
        Handle when a packet is received on the socket.
        """

        self.data = bytes.decode(self.request[0].strip())
        self.socket = self.request[1]

        print(f"{self.client_address[0]} sent the following: {self.data}")

        event_parser = FirepowerSyslogHandler()

        # Try to parse the event data
        event_json = event_parser.parse_event(self.data)

        # If we were able to parse the event, then put it on the queue
        if event_json:
            event_queue.queue_data(event_json)


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

    # Now that an event queue is ready, open up a syslog listener for events
    # Parse the syslog port from environment variables
    syslog_port = int(os.getenv("SYSLOG_PORT"))

    try:
        # Open a UDP listener on the specified port, and listen forever
        server = socketserver.UDPServer(("0.0.0.0", syslog_port), SyslogHandler)
        print(f" [x] Server listening on port {syslog_port}...")
        server.serve_forever()
    except (IOError, SystemExit):
        event_queue.close()
        raise
    except KeyboardInterrupt:
        event_queue.close()
        print("\nCrtl+C Pressed. Shutting down.")
