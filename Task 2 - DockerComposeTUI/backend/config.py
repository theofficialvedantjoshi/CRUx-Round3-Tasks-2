import os

from rich import color
from yaml import Loader, load


class ConfigHandler:
    def __init__(self):
        self.keybinds = [
            "MOVE_UP",
            "MOVE_DOWN",
            "MOVE_LEFT",
            "MOVE_RIGHT",
            "SWITCH_PANEL",
            "COMPOSE_UP",
            "COMPOSE_DOWN",
            "VIEW_LOGS",
            "LOGS_PAGE_UP",
            "LOGS_PAGE_DOWN",
            "LOGS_HOME",
            "LOGS_END",
            "VIEW_CONTAINERS",
            "VIEW_VOLUMES",
            "DEFAULT_VIEW",
            "CONTAINER_TERMINAL",
            "QUIT",
        ]
        self.default_monitor = [
            "EMAIL",
            "MAX_EMAILS",
            "EMAIL_INTERVAL",
            "CHECK_INTERVAL",
        ]
        self.monitor = [
            "CPU_THRESHOLD",
            "MEMORY_THRESHOLD",
        ]
        self.backup = ["CRON", "BACKUP_DIR"]

    def get_config(self, default=True, projects=None):
        with open(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "dockertui.config.yaml"
            )
        ) as file:
            default_config = load(file, Loader=Loader)
        if default:
            default_config, None
        else:
            project_configs = {}
            for project in projects:
                with open(f"{project}/project.config.yaml") as file:
                    project_configs[project] = load(file, Loader=Loader)
            return default_config, project_configs

    def validate_config(self, default_config, project_configs):
        keybinds = list(default_config["keybinds"].keys())
        if keybinds != self.keybinds:
            return "Invalid keybinds"
        colors = list(default_config["colors"].values())
        for color_choice in colors:
            if color_choice not in list(color.ANSI_COLOR_NAMES.keys()):
                return "Invalid color"
        other = default_config["other"]
        if other["MAX_LOGS_DISPLAY"] < 1 or other["MAX_LOGS_DISPLAY"] > 50:
            return "Invalid MAX_LOGS_DISPLAY value"
        if list(default_config["monitor"].keys()) != self.default_monitor:
            return "Invalid monitor config"
        for project, project_config in project_configs.items():
            if list(project_config["monitor"].keys()) != self.monitor:
                return f"Invalid monitor config for {project}"
        backup = default_config["backup"]
        if list(backup.keys()) != self.backup:
            return "Invalid backup config"
        return "Success"
