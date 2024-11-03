import os
import smtplib
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psutil
from backend import DockerHandler
from dotenv import load_dotenv

load_dotenv()


class DockerMonitor:
    """
    Monitor class to check the health of containers and send alerts."""

    def __init__(self, default_config, projects_config):
        self.running = True
        self.docker_handler = DockerHandler()
        self.default_config = default_config
        self.projects_config = projects_config
        self.email = self.default_config.monitor.EMAIL
        self.max_emails = self.default_config.monitor.MAX_EMAILS
        self.email_interval = self.default_config.monitor.EMAIL_INTERVAL
        self.check_interval = self.default_config.monitor.CHECK_INTERVAL
        self.email_count = 0
        self.last_sent_email = time.time()
        self.status = {}
        self.health = {}
        self.email_subject = "Container Health Alert!"
        self.email_body = ""

    def monitor(self) -> None:
        """
        Monitor the health of containers and send alerts.
        """
        containers = self.docker_handler.get_containers()

        for container in containers:
            if container.id not in self.status:
                self.status[container.id] = container.status
                self.health[container.id] = container.health

            if container.status != self.status[container.id]:
                self.status[container.id] = container.status
                self.email_body += f"The status of container {container.name} has changed to {container.status}.\n"

            if (
                container.health != self.health[container.id]
                and container.health != "unknown"
            ):
                self.health[container.id] = container.health
                self.email_body += f"The health of container {container.name} has changed to {container.health}.\n"

            if container.status == "running":
                stats = self.docker_handler.get_container_stats(container.id)
                cpu_delta = (
                    stats["cpu_stats"]["cpu_usage"]["total_usage"]
                    - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                )
                system_cpu_delta = (
                    stats["cpu_stats"]["system_cpu_usage"]
                    - stats["precpu_stats"]["system_cpu_usage"]
                )
                cpu_percent = (
                    (cpu_delta / system_cpu_delta)
                    * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
                    * 100
                )
                memory_usage = stats["memory_stats"]["usage"]
                memory_limit = stats["memory_stats"]["limit"]
                memory_percent = (memory_usage / memory_limit) * 100

                if (
                    cpu_percent
                    > self.projects_config[container.project].monitor.CPU_THRESHOLD
                ):
                    self.email_body += f"The CPU usage of container {container.name} has exceeded the threshold.\n"
                if (
                    memory_percent
                    > self.projects_config[container.project].monitor.MEMORY_THRESHOLD
                ):
                    self.email_body += f"The memory usage of container {container.name} has exceeded the threshold.\n"

        self.send_update()

    def update_container(self) -> None:
        """
        Update the container status and health."""
        containers = self.docker_handler.get_containers()
        for container_id in list(self.status.keys()):
            if container_id not in [container.id for container in containers]:
                self.email_body += f"Container {container_id} has been stopped.\n"
                del self.status[container_id]
                del self.health[container_id]
        self.send_update()
        self.email_body = ""

    def send_update(self) -> None:
        """
        Send email alerts."""
        if not self.email_body:
            return
        if (
            self.last_sent_email
            and time.time() - self.last_sent_email < self.email_interval
        ):
            return

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                msg = MIMEMultipart()
                msg["From"] = "dockertui@gmail.com"
                msg["To"] = self.email
                msg["Subject"] = self.email_subject
                msg.attach(MIMEText(self.email_body, "plain"))
                server.login("dockertui@gmail.com", os.getenv("MAIL_APP_PASSWORD"))
                server.send_message(msg)
                self.email_count += 1
                self.last_sent_email = time.time()
                self.email_body = ""
                print("Mail sent successfully")
        except Exception as e:
            print(e)

    def run(self) -> None:
        """
        Run the monitor."""
        while True:
            self.monitor()
            if self.email_count >= self.max_emails:
                self.last_sent_email = time.time()
                self.email_count = 0
            self.update_container()
            time.sleep(self.check_interval)

    def kill_monitor(self):
        for process in psutil.process_iter(["pid", "name"]):
            try:
                if process.info["name"] == "docker_monitor":
                    process.terminate()
                    return
            except psutil.NoSuchProcess:
                pass

    def check_monitor(self):
        for process in psutil.process_iter(["pid", "name"]):
            try:
                if process.info["name"] == "docker_monitor":
                    return True
            except psutil.NoSuchProcess:
                pass
        return False
