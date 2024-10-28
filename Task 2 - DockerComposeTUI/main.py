import os
import subprocess

from backend import DockerHandler, DockerMonitor, get_config
from crontab import CronTab
from tui.tui import TUI

if __name__ == "__main__":
    default_config, project_configs = get_config(
        DockerHandler().get_projects_from_env(),
    )
    monitor = DockerMonitor(default_config, project_configs)
    if not monitor.check_monitor:
        venv = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv"
        )
        command = f"nohup {os.path.join(venv, 'bin', 'python3')} '{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service.py')}'"
        subprocess.Popen(command, shell=True)

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
    job.setall(f"{default_config.backup.CRON}")
    cron.write(user=True)
    cron.write()
    tui = TUI(default_config, project_configs)
    tui.run()
