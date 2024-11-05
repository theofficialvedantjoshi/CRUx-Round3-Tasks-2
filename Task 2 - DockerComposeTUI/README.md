# DockerComposeTUI

A TUI that wraps the Docker Compose CLI. It allows users to manage their Docker Compose projects using a simple and intuitive interface. Users can view containers, volumes, logs, monitor containers and get email alerts, and backup volumes locally.

## Features

1. Compose Projects: View all Docker Compose projects in the current directory and compose up/down.
2. Container Monitoring: Monitor containers in real-time. View container stats and logs.
3. Container Interactive shell: Open an interactive shell in a container.
4. Volume Inspection: View all volumes in a project and backup volumes locally.
5. Email Alerts: Get email alerts when a container stops unexpectedly.

## Installation

1. **Docker**: Install [Docker](https://docs.docker.com/get-docker/) on your system.
2. **Docker Compose**: Install [Docker Compose](https://docs.docker.com/compose/install/) on your system.
3. **Projects**: Create an env variable in the .env file with the path to your Docker Compose projects.

    ```ini
    DOCKER_COMPOSE_PROJECTS_PATH=/path/to/your/projects;
    ```

4. **Gmail app password**: Create a Gmail app password for sending email alerts. Follow the instructions [here](https://support.google.com/accounts/answer/185833?hl=en). Add the email and app password to the .env file.

    ```ini
    MAIL_APP_PASSWORD=your_app_password
    ```

"""

## Configuration

The application uses `dockertui.config.yaml` and `project.config.yaml` for customization.

- **Keybinds**: Default key bindings are provided in `dockertui.config.yaml` for navigating and managing containers, logs, and volumes. Users can view and modify these bindings in the config file.
- **Monitoring**: Set email alerts and monitoring thresholds in `dockertui.config.yaml`, with CPU and memory limits in each project's `project.config.yaml`.
- **Backups**: Schedule volume backups and define the backup directory in `dockertui.config.yaml`.

## Usage

- Make sure all required dependencies are installed.
- Run the application:

    ```bash
    python3 main.py
    ```

## Tools and Libraries

- **Docker SDK for Python**: Used to interact with Docker and Docker Compose.
- **Subprocess**: Used to run Docker and tmux commands in the terminal.
- **TMUX**: Used to create a split-screen container terminal interface.
- **Rich**: Used to create the frontend TUI interface.
- **SMTP**: Used to send email alerts.
- **CRON**: Used to schedule volume backups.
- **NoHup**: Used to run the docker monitor in the background.
- **Termios**: Used to capture keypress events in the TUI.

## Todos

- Add search functionality for logs.
- Make the container terminal inside of the TUI.
- Add more customization options for monitoring and alerts.
- Improve error handling and logging.
