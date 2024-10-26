import os
import subprocess

import docker
from dotenv import load_dotenv

load_dotenv()


class DockerHandler:
    def __init__(self):
        self.client = docker.from_env()
        self.project_env = os.getenv("PROJECTS_PATH", "")

    def get_projects_from_env(self):
        return [
            project
            for project in self.project_env.split(os.pathsep)
            if os.path.isfile(os.path.join(project, "docker-compose.yml"))
        ]

    def add_project(self, project_path: str):
        self.project_env = os.getenv("PROJECTS_PATH", "") + os.pathsep + project_path
        os.environ["PROJECTS_PATH"] = self.project_env

    def compose(self, project_path: str, command: str):
        os.chdir(project_path)
        if command == "up":
            result = subprocess.Popen(
                ["docker-compose", command, "-d"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        else:
            result = subprocess.Popen(
                ["docker-compose", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        return result

    def get_containers(self):
        containers = self.client.containers.list()
        # for container in containers:
        #     print(container.stats(stream=False))
        return [
            {
                "name": container.name,
                "id": container.id,
                "status": container.status,
                "health": container.health,
                "image": container.image,
                "ports": ", ".join(host for host, _ in container.ports.items()),
            }
            for container in containers
        ]

    def get_logs(self, container_id: str):
        return (
            self.client.containers.get(container_id)
            .logs(tail=100, stream=False, timestamps=True)
            .decode("utf-8")
        )

    def stream_logs(self, container_id: str):
        return self.client.containers.get(container_id).logs(
            stream=True, follow=True, tail=100, timestamps=True
        )

    def get_volumes(self):
        containers = self.client.containers.list()
        volume_containers = {
            container.name: {"name": volume["Name"], "mountpoint": volume["Source"]}
            for container in containers
            for volume in container.attrs["Mounts"]
            if volume["Type"] == "volume"
        }
        volumes = self.client.volumes.list()
        return_data = []
        for volume in volumes:
            if volume.attrs["Name"] in [
                volume_name["name"] for volume_name in volume_containers.values()
            ]:
                name = volume.attrs["Name"]
                driver = volume.attrs["Driver"]
                mountpoints = ", ".join(
                    [
                        volume_containers[container_name]["mountpoint"]
                        for container_name, volume_name in volume_containers.items()
                        if volume_name["name"] == name
                    ]
                )
                containers = ", ".join(
                    [
                        container_name
                        for container_name, volume_name in volume_containers.items()
                        if volume_name["name"] == name
                    ]
                )
                return_data.append(
                    {
                        "name": name,
                        "driver": driver,
                        "mountpoints": mountpoints,
                        "containers": containers,
                    }
                )
        return return_data

    def get_container_stats(self, container_id: str):
        return self.client.containers.get(container_id).stats(stream=False)


# docker_handler = DockerHandler()
# docker_handler.get_containers()
