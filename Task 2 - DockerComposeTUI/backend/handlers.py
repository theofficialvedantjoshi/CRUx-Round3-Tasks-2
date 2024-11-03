import os
import subprocess

import docker
from dotenv import load_dotenv
from models.docker import Container, Volume

load_dotenv()


class DockerHandler:
    """
    Docker Handler class to interact with the Docker Engine."""

    def __init__(self):
        self.client = docker.from_env()
        self.project_env = os.getenv("PROJECTS_PATH", "")

    def get_projects_from_env(self) -> list[str]:
        """
        Get the list of projects from the environment variable.

        Returns:
        - list of project directories.
        """
        projects = []
        for project in self.project_env.split(os.pathsep):
            if os.path.isfile(os.path.join(project, "docker-compose.yml")):
                projects.append(project)
                if not os.path.isfile(os.path.join(project, "project.config.yaml")):
                    with open(
                        os.path.join(
                            os.path.dirname(os.path.dirname(__file__)),
                            "project.config.yaml",
                        )
                    ) as file:
                        with open(
                            os.path.join(project, "project.config.yaml"), "w"
                        ) as f:
                            f.write(file.read())
        return projects

    def compose(self, project_path: str, command: str) -> subprocess.Popen:
        """
        Run docker-compose commands.

        Args:
        - project_path: path to the project directory.
        - command: docker-compose command to run.

        Returns:
        - subprocess.Popen object.
        """
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

    def get_containers(self) -> list[Container]:
        """
        Get the list of containers.

        Returns:
        - list of Container objects.
        """
        containers = self.client.containers.list()
        return [
            Container(
                name=container.name,
                id=container.id,
                status=container.status,
                health=container.health,
                image=container.image,
                ports=", ".join(host for host, _ in container.ports.items()),
                project=container.attrs["Config"]["Labels"]
                .get("com.docker.compose.project.config_files")
                .split("docker-compose.yml")[0],
            )
            for container in containers
        ]

    def get_logs(self, container_id: str) -> str:
        """
        Get the logs of a container.

        Args:
        - container_id: ID of the container.

        Returns:
        - logs of the container.
        """
        return (
            self.client.containers.get(container_id)
            .logs(tail=100, stream=False, timestamps=True)
            .decode("utf-8")
        )

    def stream_logs(self, container_id: str) -> str:
        """
        Stream the logs of a container.

        Args:
        - container_id: ID of the container.

        Returns:
        - logs of the container.
        """
        return self.client.containers.get(container_id).logs(
            stream=True, follow=True, tail=100, timestamps=True
        )

    def get_volumes(self) -> list[Volume]:
        """
        Get the list of volumes.

        Returns:
        - list of Volume objects.
        """
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
                mountpoint = volume.attrs["Mountpoint"]
                containers = ", ".join(
                    [
                        container_name
                        for container_name, volume_name in volume_containers.items()
                        if volume_name["name"] == name
                    ]
                )
                return_data.append(
                    Volume(
                        name=name,
                        driver=driver,
                        mountpoint=mountpoint,
                        containers=containers,
                    )
                )
        return return_data

    def get_container_stats(self, container_id: str) -> dict:
        """
        Get the stats of a container.

        Args:
        - container_id: ID of the container.

        Returns:
        - stats of the container.
        """
        return self.client.containers.get(container_id).stats(stream=False)
