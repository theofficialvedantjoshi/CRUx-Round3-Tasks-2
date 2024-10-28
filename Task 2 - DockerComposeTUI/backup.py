from backend import DockerHandler, ConfigHandler
import os


def backup():
    docker_handler = DockerHandler()
    config_handler = ConfigHandler()
    default_config, _ = config_handler.get_config(
        False, docker_handler.get_projects_from_env()
    )
    backup_dir = (
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        + default_config["backup"]["BACKUP_DIR"]
    )
    volumes = docker_handler.get_volumes()

    for volume in volumes:
        volume_name = volume["name"]
        volume_containers = volume["containers"]

        for container in volume_containers.split(", "):
            container_backup_dir = f"{backup_dir}/{volume_name}/{container}"
            os.makedirs(container_backup_dir, exist_ok=True)
            try:
                docker_handler.client.containers.run(
                    image="busybox",
                    command=f"tar -zcvf /backup/{volume_name}.tar.gz /backup-volume",
                    volumes={
                        volume_name: {"bind": "/backup-volume", "mode": "ro"},
                        container_backup_dir: {"bind": "/backup", "mode": "rw"},
                    },
                    remove=True,
                )

                print(
                    f"Created backup for volume {volume_name} associated with container {container}"
                )

            except Exception as e:
                print(
                    f"Error backing up volume {volume_name} for container {container}: {str(e)}"
                )
                continue


if __name__ == "__main__":
    backup()
