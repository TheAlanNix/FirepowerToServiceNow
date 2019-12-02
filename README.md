# Firepower IPS Events to ServiceNow

## Summary

This project is meant as proof-of-concept code for ingesting Firepower Management Center syslog events in order to create ServiceNow incidents.

Once the code is configured for your ServiceNow instance and running, simply direct your FMC to send syslog events to the host on the specified port (Default: 4514/UDP).

## Requirements

1. Python 3.x

> **Optional**: If running this script as a container, you'll want to have Docker and Docker Compose installed on your system.

## How To Run

1. Prior to running the script for the first time, copy the ***.env.example*** to ***.env***.
    * ```cp .env.example .env```
2. Open the ***.env*** file and configure the ServiceNow parameters.
    - SNOW_USERNAME: The username to be used to authenticate to ServiceNow. (String)
    - SNOW_PASSWORD: The password to be used to authenticate to ServiceNow. (String)
    - SNOW_TENANT: The ServiceNow Tenant ID to use. (String)
    - SYSLOG_PORT: The UDP port to be used to listen for inbound events. (Integer)
2. Install the required packages from the ***requirements.txt*** file.
    * ```pip install -r requirements.txt```
    * You'll probably want to set up a virtual environment: [Python 'venv' Tutorial](https://docs.python.org/3/tutorial/venv.html)
    * Activate the Python virtual environment, if you created one.
3. Run the script with ```python firepower_to_servicenow.py```

## Docker Container

This script is Docker friendly, and can be deployed as a container.  Once the ***.env*** file is created and populated, run the following command from the root of the project to build the container and run it as a daemon:

- ```docker-compose up -d```
