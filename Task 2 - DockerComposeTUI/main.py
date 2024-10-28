import multiprocessing
import os
import subprocess

from backend import ConfigHandler, DockerMonitor
from crontab import CronTab
from tui.tui import TUI

if __name__ == "__main__":
    monitor = DockerMonitor()
    if not monitor.check_monitor:
        venv = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv"
        )
        command = f"nohup {os.path.join(venv, 'bin', 'python3')} '{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service.py')}'"
        subprocess.Popen(command, shell=True)
    config_handler = ConfigHandler()
    default_config, project_configs = config_handler.get_config(
        False,
        monitor.docker_handler.get_projects_from_env(),
    )
    result = config_handler.validate_config(default_config, project_configs)
    if result != "Success":
        print(result, "\nPlease check the format of your config file.")
        exit(1)
    cron = CronTab(user=True)
    for cron_job in cron:
        if cron_job.comment == "dockertui_backup":
            cron.remove(cron_job)
            break
    venv = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv"
    )
    job = cron.new(
        command=f"{os.path.join(venv, 'bin', 'python3')} '{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup.py')}'",
        comment="dockertui_backup",
    )
    job.setall(f"{default_config['backup']['CRON']}")
    cron.write(user=True)
    cron.write()
    tui = TUI()
    tui.run()
