import multiprocessing

from backend import DockerMonitor

if __name__ == "__main__":
    monitor = DockerMonitor()
    monitor_process = multiprocessing.Process(
        target=monitor.run, name="docker_monitor", daemon=False
    )
    monitor_process.start()
