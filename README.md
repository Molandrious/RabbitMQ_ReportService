# RabbitMQ_ReportService

Welcome to this repository! Follow the steps below to get started.

## Getting Started

### 1. Download the Project

Firstly, clone or download this repository to your local machine using:

```bash
git clone [URL_OF_THIS_REPOSITORY]
```

### 2. Create the `resources` Directory

After you've downloaded the project, navigate to its root directory and create a `resources` directory.
Inside this directory, place your `data.json` file:

### 3. Setup RabbitMQ Container Settings

The RabbitMQ settings for the Docker container can be found in the Docker compose file. Modify them if necessary to match your environment or leave them as is if they suit your needs.

### 4. Run Docker Compose

Navigate to the directory containing the `docker-compose.yml` file and run:

```bash
docker-compose up
```

Please wait around 15 seconds after the Docker containers are up to ensure all services have initialized correctly.

### 5. Check Environment Settings

Before running the client, ensure the environment settings inside `client` match the Docker compose settings for RabbitMQ. Modify them if necessary.

### 6. Run client.py

Install requirements.txt on yur local machine.
Navigate to the `client_example` directory:
You can change the requests data by using the provided `example_requests.json`. Once you're ready, execute:

```bash
python client.py
```
