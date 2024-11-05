from dataclasses import dataclass

from rich import color


@dataclass
class KeyBinds:
    MOVE_UP: str = "\x1b[A"
    MOVE_DOWN: str = "\x1b[B"
    MOVE_LEFT: str = "\x1b[D"
    MOVE_RIGHT: str = "\x1b[C"
    SWITCH_PANEL: str = "\t"
    COMPOSE_UP: str = "u"
    COMPOSE_DOWN: str = "d"
    VIEW_LOGS: str = "l"
    LOGS_PAGE_UP: str = "k"
    LOGS_PAGE_DOWN: str = "j"
    LOGS_HOME: str = "g"
    LOGS_END: str = "f"
    VIEW_CONTAINERS: str = "c"
    VIEW_VOLUMES: str = "v"
    DEFAULT_VIEW: str = "q"
    CONTAINER_TERMINAL: str = "t"
    QUIT: str = "e"


@dataclass
class Colors:
    CONSOLE: str = "dark_blue"

    def __eq__(self, other):
        if isinstance(other, Colors):
            return all(
                [
                    getattr(self, key) in color.ANSI_COLOR_NAMES.keys()
                    for key in self.__annotations__.keys()
                ]
            )
        return False


@dataclass
class Others:
    LOG_TAIL: int = 100
    MAX_LOGS_DISPLAY: int = 100
    MAX_STDOUT_DISPLAY: int = 100


@dataclass
class DockerMonitor:
    EMAIL: str = ""
    MAX_EMAILS: int = 5
    EMAIL_INTERVAL: int = 30
    CHECK_INTERVAL: int = 30


@dataclass
class ProjectMonitor:
    CPU_THRESHOLD: float = 80.0
    MEM_THRESHOLD: float = 80.0


@dataclass
class Backup:
    CRON: str = "*/1 * * * *"
    BACKUP_DIR: str = "/backups"


@dataclass
class Config:
    keybinds: KeyBinds = KeyBinds()
    colors: Colors = Colors()
    other: Others = Others()
    monitor: DockerMonitor = DockerMonitor()
    backup: Backup = Backup()

    def __eq__(self, other):
        if isinstance(other, Config):
            return all(
                [
                    getattr(self, key) == getattr(other, key)
                    for key in self.__annotations__.keys()
                ]
            )
        return False

    def from_dict(self, data: dict):
        return Config(
            keybinds=KeyBinds(**data["keybinds"]),
            colors=Colors(**data["colors"]),
            other=Others(**data["other"]),
            monitor=DockerMonitor(**data["monitor"]),
            backup=Backup(**data["backup"]),
        )


@dataclass
class ProjectConfig:
    monitor: ProjectMonitor = ProjectMonitor()

    def from_dict(self, data: dict):
        return ProjectConfig(**data)

    def __eq__(self, other):
        if isinstance(other, ProjectConfig):
            return all(
                [
                    getattr(self, key) == getattr(other, key)
                    for key in self.__annotations__.keys()
                ]
            )
        return False
