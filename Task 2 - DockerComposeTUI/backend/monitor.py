import os
import smtplib
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psutil
from backend import ConfigHandler, DockerHandler
from dotenv import load_dotenv

load_dotenv()


class DockerMonitor:
    def __init__(self):
        self.running = True
        self.docker_handler = DockerHandler()
        self.config_handler = ConfigHandler()
        self.default_config, self.projects_config = self.config_handler.get_config(
            False, self.docker_handler.get_projects_from_env()
        )
        validation = self.config_handler.validate_config(
            self.default_config, self.projects_config
        )
        if validation != "Success":
            sys.exit(1)
        self.email = self.default_config["monitor"]["EMAIL"]
        self.max_emails = self.default_config["monitor"]["MAX_EMAILS"]
        self.email_interval = self.default_config["monitor"]["EMAIL_INTERVAL"]
        self.check_interval = self.default_config["monitor"]["CHECK_INTERVAL"]
        self.email_count = 0
        self.last_sent_email = time.time()
        self.status = {}
        self.health = {}
        self.email_subject = "Container Health Alert!"
        self.email_body = ""

    def monitor(self):
        containers = self.docker_handler.get_containers()

        for container in containers:
            container_id = container["id"]
            container_name = container["name"]
            container_project = container["project"]

            if container_id not in self.status:
                self.status[container_id] = container["status"]
                self.health[container_id] = container["health"]

            if container["status"] != self.status[container_id]:
                self.status[container_id] = container["status"]
                self.email_body += f"The status of container {container_name} has changed to {container['status']}.\n"

            if (
                container["health"] != self.health[container_id]
                and container["health"] != "unknown"
            ):
                self.health[container_id] = container["health"]
                self.email_body += f"The health of container {container_name} has changed to {container['health']}.\n"

            if container["status"] == "running":
                stats = self.docker_handler.get_container_stats(container_id)
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
                    > self.projects_config[container_project]["monitor"][
                        "CPU_THRESHOLD"
                    ]
                ):
                    self.email_body += f"The CPU usage of container {container_name} has exceeded the threshold.\n"
                if (
                    memory_percent
                    > self.projects_config[container_project]["monitor"][
                        "MEMORY_THRESHOLD"
                    ]
                ):
                    self.email_body += f"The memory usage of container {container_name} has exceeded the threshold.\n"

        self.send_update()

    def update_container(self):
        containers = self.docker_handler.get_containers()
        for container_id in list(self.status.keys()):
            if container_id not in [container["id"] for container in containers]:
                self.email_body += f"Container {container_id} has been stopped.\n"
                del self.status[container_id]
                del self.health[container_id]
        self.send_update()
        self.email_body = ""

    def send_update(self):
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

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
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
