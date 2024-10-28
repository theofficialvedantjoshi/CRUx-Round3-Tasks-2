import multiprocessing

from backend import DockerHandler, DockerMonitor, get_config

if __name__ == "__main__":
    default_config, project_configs = get_config(
        DockerHandler().get_projects_from_env(),
    )
    monitor = DockerMonitor(default_config, project_configs)
    monitor_process = multiprocessing.Process(
        target=monitor.run, name="docker_monitor", daemon=False
    )
    monitor_process.start()
