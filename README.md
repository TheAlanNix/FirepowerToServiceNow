# Firepower IPS Events to ServiceNow

## Summary

This project is meant as proof-of-concept code for ingesting Firepower Management Center syslog events in order to create ServiceNow incidents.  There are three containers that are used in this project:

- Event Listener:  This container will open a Syslog listener which will take in Impact Flag Alerts from the Firepower Management Center (FMC).
- Event Publisher:  This container will monitor a RabbitMQ event queue and submit any pending events to ServiceNow.
- Event Queue:  This container simply runs a RabbitMQ instance for queuing events.

Once the *.env* file is configured for your ServiceNow instance and running, simply direct your FMC to send Impact Flag Alerts via syslog to the host on the specified port (Default: 4514/UDP).

> Impact Flag Alerts are configured under Policies -> Actions -> Alerts in the FMC.

## Requirements

1. Docker
2. Docker Compose

## How To Run

1. Prior to running the script for the first time, copy the ***.env.example*** to ***.env***.
    * ```cp .env.example .env```
2. Open the ***.env*** file and configure the ServiceNow parameters.
    - RABBIT_MQ_HOST: The container name for the RabbitMQ container. (String)
    - SNOW_USERNAME: The username to be used to authenticate to ServiceNow. (String)
    - SNOW_PASSWORD: The password to be used to authenticate to ServiceNow. (String)
    - SNOW_TENANT: The ServiceNow Tenant ID to use. (String)
    - SYSLOG_PORT: The UDP port to be used to listen for inbound events. (Integer)
3. Once configuration is in place, simply use Docker Compose to build, deploy, and run the containers as daemons.
    - ```docker-compose up -d```
