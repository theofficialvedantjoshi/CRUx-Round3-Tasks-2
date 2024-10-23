from rich import color
from yaml import load, Loader


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

    def get_config(self, default=True):
        with open(".example.config.yaml") as file:
            return load(file, Loader=Loader)

    def validate_config(self):
        keybinds = list(self.get_config()["keybinds"].keys())
        if keybinds != self.keybinds:
            return "Invalid keybinds"
        colors = list(self.get_config()["colors"].values())
        for color_choice in colors:
            if color_choice not in list(color.ANSI_COLOR_NAMES.keys()):
                return "Invalid color"
        other = self.get_config()["other"]
        if other["MAX_LOGS_DISPLAY"] < 1 or other["MAX_LOGS_DISPLAY"] > 50:
            return "Invalid MAX_LOGS_DISPLAY value"
        return "Success"
