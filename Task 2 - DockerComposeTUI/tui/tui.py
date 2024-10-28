import os
import subprocess
import sys
import termios
import tty

from backend import ConfigHandler, DockerHandler, DockerMonitor
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class TUI:
    def __init__(self):
        self.docker_monitor = DockerMonitor()
        self.docker_handler = DockerHandler()
        self.config_handler = ConfigHandler()
        self.config, self.projects_config = self.config_handler.get_config(
            default=False, projects=self.docker_handler.get_projects_from_env()
        )
        self.keybind_actions = {
            "MOVE_UP": self.handle_move_up,
            "MOVE_DOWN": self.handle_move_down,
            "MOVE_RIGHT": self.handle_move_right,
            "MOVE_LEFT": self.handle_move_left,
            "SWITCH_PANEL": self.handle_switch_panel,
            "COMPOSE_UP": self.handle_compose_up,
            "COMPOSE_DOWN": self.handle_compose_down,
            "VIEW_LOGS": self.handle_view_logs,
            "LOGS_PAGE_UP": self.handle_logs_page_up,
            "LOGS_PAGE_DOWN": self.handle_logs_page_down,
            "LOGS_HOME": self.handle_logs_home,
            "LOGS_END": self.handle_logs_end,
            "VIEW_CONTAINERS": self.handle_view_containers,
            "DEFAULT_VIEW": self.handle_default_view,
            "VIEW_VOLUMES": self.handle_view_volumes,
            "CONTAINER_TERMINAL": self.handle_container_terminal,
            "QUIT": self.handle_quit,
        }
        self.keybinds = {
            key: self.keybind_actions[action]
            for action, key in self.config["keybinds"].items()
        }
        self.projects = self.docker_handler.get_projects_from_env()
        self.containers = self.docker_handler.get_containers()
        self.volumes = self.docker_handler.get_volumes()
        self.console = Console(style="dark_blue")
        self.project_index = 0
        self.container_index = 0
        self.container_hindex = 0
        self.volume_index = 0
        self.volume_attrs = ["name", "driver", "mountpoint", "containers"]
        self.volumes_hindex = 0
        self.focused_panel = "left"
        self.right_panel = "containers"
        self.stdout = []
        self.max_stdout_lines = self.config["other"]["MAX_STDOUT_DISPLAY"]
        self.logs = None
        self.logs_offset = 0
        self.max_logs_display = self.config["other"]["MAX_LOGS_DISPLAY"]
        self.container_terminal = False

    def _stream_docker_compose(self, process):
        for stderr_line in iter(process.stderr.readline, ""):
            self.add_output(stderr_line.strip())
            self.render()
        self.render()
        process.stderr.close()
        process.stdout.close()
        process.wait()

    def _create_left_panel(self, width):
        table = Table(
            box=box.SQUARE,
            show_edge=False,
        )
        table.add_column("Projects", justify="left", width=width)
        if len(self.projects) == 0:
            table.add_row(
                "No projects found in PROJECTS_PATH. Edit PROJECTS_PATH in .env to add projects."
            )
        else:
            for i, project in enumerate(self.projects):
                if i == self.project_index and self.focused_panel == "left":
                    table.add_row("🗀 " + project, style="white", end_section=True)
                else:
                    table.add_row("🗀 " + project, end_section=True)
        return Panel(
            table,
            title="Projects",
            border_style="dark_blue" if self.focused_panel == "right" else "white",
            padding=(1, 1),
        )

    def _create_containter_panel(self, width):
        table = Table(box=box.SQUARE, show_edge=False)
        table.add_column("Containers", justify="left", width=width)
        if len(self.containers) == 0:
            table.add_row(
                "No containers found. Compose a project first by pressing 'u'"
            )
        else:
            for i, container in enumerate(self.containers):
                name = container.get("name", "N/A")
                status = container.get("status", "N/A")
                health = container.get("health", "N/A")
                ports = container.get("ports", "N/A")
                image = container.get("image", "N/A")
                container_info = f"❑ {name} | {status} | {health} | {image} | {ports}"
                max_visible_chars = width - 10
                if i == self.container_index:
                    if self.container_hindex < 0:
                        self.container_hindex = 0
                    if len(container_info) > max_visible_chars:
                        container_info = container_info[
                            self.container_hindex : self.container_hindex
                            + max_visible_chars
                        ]
                else:
                    container_info = container_info[:max_visible_chars]
                if i == self.container_index and self.focused_panel == "right":
                    table.add_row(container_info, style="white", end_section=True)
                else:
                    table.add_row(container_info, end_section=True)
        return Panel(
            table,
            title="Containers",
            border_style="dark_blue" if self.focused_panel == "left" else "white",
            padding=(1, 1),
        )

    def _create_volumes_panel(self, width):
        table = Table(box=box.SQUARE, show_edge=False)
        table.add_column("Volumes", justify="left", width=width)
        if len(self.volumes) == 0:
            table.add_row("No volumes found.")
        else:
            for i, volume in enumerate(self.volumes):
                if i == self.volume_index:
                    attr = self.volume_attrs[self.volumes_hindex]
                    value = volume.get(attr, "N/A")
                    volume_info = f"⊟ {attr} - {value}"
                else:
                    name = volume.get("name", "N/A")
                    volume_info = f"⊟ Name - {name}"
                if i == self.volume_index and self.focused_panel == "right":
                    table.add_row(volume_info, style="white", end_section=True)
                else:
                    table.add_row(volume_info, end_section=True)
        return Panel(
            table,
            title="Volumes",
            border_style="dark_blue" if self.focused_panel == "left" else "white",
        )

    def _create_logs_panel(self, width):
        if len(self.containers) == 0:
            self.right_panel = "containers"
            return self._create_right_panel(width)
        table = Table(box=box.SQUARE, show_edge=False)
        table.add_column("Logs", justify="left", width=width)
        log_lines = self.logs.split("\n")
        displayed_logs = log_lines[
            self.logs_offset : self.logs_offset + self.max_logs_display
        ]
        for i, log in enumerate(displayed_logs):
            table.add_row(f"{self.logs_offset + i + 1} | {log}")
        return Panel(
            table,
            title=f"Log Inspection ({self.logs_offset + 1}-{min(self.logs_offset + self.max_logs_display, len(log_lines))} of {len(log_lines)})",
            border_style="dark_blue" if self.focused_panel == "left" else "white",
        )

    def _create_right_panel(self, width):
        if self.right_panel == "containers":
            return self._create_containter_panel(width)
        elif self.right_panel == "logs":
            return self._create_logs_panel(width)
        elif self.right_panel == "volumes":
            return self._create_volumes_panel(width)

    def _create_stdout_panel(self):
        text = "\n".join(self.stdout[-self.max_stdout_lines :])
        return Panel(
            text,
            title="STDOUT",
            height=20,
            title_align="left",
            border_style="dark_blue",
        )

    def add_output(self, output):
        self.stdout.append(output)

    def render(self):
        os.system("clear")
        layout = Layout(name="root")
        layout.split(
            Layout(name="padding", size=2),
            Layout(name="header", size=2),
            Layout(name="body", size=30),
            Layout(name="footer", size=20),
        )
        layout["padding"].update(Text(""))
        layout["header"].update(
            Text(
                "Docker Compose TUI",
                justify="center",
                style="bold white",
            )
        )
        if not self.container_terminal:
            body = Layout()
            body.split_row(self._create_left_panel(100), self._create_right_panel(100))
            layout["body"].update(body)
        else:
            layout["body"].split_row(self._create_left_panel(100), Layout())
        layout["footer"].update(self._create_stdout_panel())
        self.console.print(layout)

    def handle_move_up(self):
        if self.focused_panel == "left" and self.project_index > 0:
            self.project_index -= 1
        elif self.focused_panel == "right":
            if self.right_panel == "containers" and self.container_index > 0:
                self.container_hindex = 0
                self.container_index -= 1
            elif self.right_panel == "logs" and self.logs_offset > 0:
                self.logs_offset -= 1
        self.render()

    def handle_move_down(self):
        if self.focused_panel == "left" and self.project_index < len(self.projects) - 1:
            self.project_index += 1
        elif self.focused_panel == "right":
            if (
                self.right_panel == "containers"
                and self.container_index < len(self.containers) - 1
            ):
                self.container_hindex = 0
                self.container_index += 1
            elif self.right_panel == "logs":
                log_lines = self.logs.split("\n")
                if self.logs_offset < len(log_lines) - self.max_logs_display:
                    self.logs_offset += 1
        self.render()

    def handle_move_right(self):
        if self.focused_panel == "right":
            if self.right_panel == "containers":
                self.container_hindex += 1
            elif self.right_panel == "volumes":
                self.volumes_hindex = (self.volumes_hindex + 1) % len(self.volume_attrs)
        self.render()

    def handle_move_left(self):
        if self.focused_panel == "right":
            if self.right_panel == "containers" and self.container_hindex > 0:
                self.container_hindex -= 1
            elif self.right_panel == "volumes" and self.volumes_hindex > 0:
                self.volumes_hindex -= 1
        self.render()

    def handle_switch_panel(self):
        self.focused_panel = "right" if self.focused_panel == "left" else "left"
        self.render()

    def handle_compose_up(self):
        self.add_output("docker-compose up...")

        result = self.docker_handler.compose(self.projects[self.project_index], "up")
        self._stream_docker_compose(result)
        self.render()

    def handle_compose_down(self):
        if self.focused_panel == "left":
            self.add_output("docker-compose down...")
            self.right_panel = "containers"

            result = self.docker_handler.compose(
                self.projects[self.project_index], "down"
            )
            self._stream_docker_compose(result)
        self.render()

    def handle_container_terminal(self):
        self.container_terminal = True
        self.render()
        if len(self.containers) == 0:
            return

        container_id = self.containers[self.container_index].get("id")
        try:
            subprocess.run(
                [
                    "tmux",
                    "split-window",
                    "-h",
                    f"docker exec -it {container_id} /bin/bash",
                ],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.add_output(f"Failed to open terminal: {str(e)}")
        self.render()

    def handle_view_logs(self):
        if self.right_panel == "containers" and len(self.containers) > 0:
            self.add_output(
                "Opening log Inspection for container "
                + self.containers[self.container_index].get("name")
                + "..."
            )
            self.right_panel = "logs"
            self.logs_offset = 0
        self.render()

    def handle_logs_page_up(self):
        if self.right_panel == "logs" and self.logs_offset > 0:
            if self.logs_offset - self.max_logs_display > 0:
                self.logs_offset -= self.max_logs_display
            else:
                self.logs_offset = 0
        else:
            self.docker_monitor.kill_monitor()
            self.stdout.append("Killed monitor")
        self.render()

    def handle_logs_page_down(self):
        if self.right_panel == "logs":
            if self.logs_offset + self.max_logs_display < len(self.logs.split("\n")):
                self.logs_offset += self.max_logs_display
            else:
                self.logs_offset = len(self.logs.split("\n")) - self.max_logs_display
        self.render()

    def handle_logs_home(self):
        self.logs_offset = 0
        self.render()

    def handle_logs_end(self):
        self.logs_offset = len(self.logs.split("\n")) - self.max_logs_display
        self.render()

    def handle_view_containers(self):
        self.right_panel = "containers"
        self.render()

    def handle_view_volumes(self):
        self.right_panel = "volumes"
        self.render()

    def handle_default_view(self):
        self.container_terminal = False
        self.right_panel = "containers"
        self.render()

    def handle_quit(self):
        subprocess.run(["tmux", "kill-session", "-t", "docker-tui"])

    def on_key(self):
        settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        try:
            while True:
                k = os.read(sys.stdin.fileno(), 1).decode()
                if k == "\x1b":
                    k += os.read(sys.stdin.fileno(), 2).decode()
                return self.keybinds.get(k, None)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

    def run(self):
        if "TMUX" not in os.environ:
            session_name = "docker-tui"
            subprocess.run(["tmux", "new", "-s", session_name, "python", "main.py"])
            subprocess.run(["tmux", "attach", "-t", session_name])
        else:
            self.render()
            try:
                while True:
                    handler = self.on_key()
                    if handler:
                        self.projects = self.docker_handler.get_projects_from_env()
                        self.containers = self.docker_handler.get_containers()
                        if len(self.containers) > 0:
                            self.logs = self.docker_handler.get_logs(
                                self.containers[self.container_index].get("id")
                            )
                        handler()
            except Exception as e:
                print(e)
                pass
