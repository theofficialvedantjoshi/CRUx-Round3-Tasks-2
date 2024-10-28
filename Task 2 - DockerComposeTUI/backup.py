import os

from backend import DockerHandler, get_config


def backup(default_config):
    docker_handler = DockerHandler()
    default_config, _ = get_config(False, docker_handler.get_projects_from_env())
    backup_dir = (
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        + default_config.backup.BACKUP_DIR
    )
    volumes = docker_handler.get_volumes()

    for volume in volumes:
        volume_containers = volume.containers

        for container in volume_containers.split(", "):
            container_backup_dir = f"{backup_dir}/{volume.name}/{container}"
            os.makedirs(container_backup_dir, exist_ok=True)
            try:
                docker_handler.client.containers.run(
                    image="busybox",
                    command=f"tar -zcvf /backup/{volume.name}.tar.gz /backup-volume",
                    volumes={
                        volume.name: {"bind": "/backup-volume", "mode": "ro"},
                        container_backup_dir: {"bind": "/backup", "mode": "rw"},
                    },
                    remove=True,
                )

                print(
                    f"Created backup for volume {volume.name} associated with container {container}"
                )

            except Exception as e:
                print(
                    f"Error backing up volume {volume.name} for container {container}: {str(e)}"
                )
                continue


if __name__ == "__main__":
    backup()
