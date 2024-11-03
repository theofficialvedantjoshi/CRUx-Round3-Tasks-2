import os
import subprocess
import sys
import termios
import tty
from dataclasses import asdict

from backend import DockerHandler, DockerMonitor
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class TUI:
    """Text-based user interface for Docker Compose TUI."""

    def __init__(self, default_config, projects_config):
        self.docker_monitor = DockerMonitor(default_config, projects_config)
        self.docker_handler = DockerHandler()
        self.config = default_config
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
            for action, key in asdict(self.config.keybinds).items()
        }
        self.projects = self.docker_handler.get_projects_from_env()
        self.containers = self.docker_handler.get_containers()
        self.volumes = self.docker_handler.get_volumes()
        self.console = Console(style=self.config.colors.CONSOLE)
        self.project_index = 0
        self.container_index = 0
        self.container_hindex = 0
        self.volume_index = 0
        self.volume_attrs = ["name", "driver", "mountpoint", "containers"]
        self.volumes_hindex = 0
        self.focused_panel = "left"
        self.right_panel = "containers"
        self.stdout = []
        self.max_stdout_lines = self.config.other.MAX_STDOUT_DISPLAY
        self.logs = None
        self.logs_offset = 0
        self.max_logs_display = self.config.other.MAX_LOGS_DISPLAY
        self.container_terminal = False

    def _stream_docker_compose(self, process: subprocess.Popen) -> None:
        """
        Stream the output of a docker-compose command to the console.
        Args:
            process (subprocess.Popen): The process to stream the output from.
        Returns:
            None
        """
        for stderr_line in iter(process.stderr.readline, ""):
            self._add_output(stderr_line.strip())
            self._render()
        self._render()
        process.stderr.close()
        process.stdout.close()
        process.wait()

    def _create_left_panel(self, width: int) -> Panel:
        """Create the left panel of the TUI.
        Args:
            width (int): The width of the panel.
        Returns:
            Panel: The left panel of the TUI."""
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
                    table.add_row(
                        "🗀 " + project,
                        style=self.config.colors.PANEL_FOCUS,
                        end_section=True,
                    )
                else:
                    table.add_row("🗀 " + project, end_section=True)
        return Panel(
            table,
            title="Projects",
            border_style=(
                self.config.colors.CONSOLE
                if self.focused_panel == "right"
                else self.config.colors.PANEL_FOCUS
            ),
            padding=(1, 1),
        )

    def _create_containter_panel(self, width: int) -> Panel:
        """Create the container panel of the TUI.
        Args:
            width (int): The width of the panel.
        Returns:
            Panel: The container panel of the TUI."""
        table = Table(box=box.SQUARE, show_edge=False)
        table.add_column("Containers", justify="left", width=width)
        if len(self.containers) == 0:
            table.add_row(
                "No containers found. Compose a project first by pressing 'u'"
            )
        else:
            for i, container in enumerate(self.containers):
                name = container.name
                status = container.status
                health = container.health
                ports = container.ports
                image = container.image
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
                    table.add_row(
                        container_info,
                        style=self.config.colors.PANEL_FOCUS,
                        end_section=True,
                    )
                else:
                    table.add_row(container_info, end_section=True)
        return Panel(
            table,
            title="Containers",
            border_style=(
                self.config.colors.CONSOLE
                if self.focused_panel == "left"
                else self.config.colors.PANEL_FOCUS
            ),
            padding=(1, 1),
        )

    def _create_volumes_panel(self, width: int) -> Panel:
        """Create the volumes panel of the TUI.
        Args:
            width (int): The width of the panel.
        Returns:
            Panel: The volumes panel of the TUI."""
        table = Table(box=box.SQUARE, show_edge=False)
        table.add_column("Volumes", justify="left", width=width)
        if len(self.volumes) == 0:
            table.add_row("No volumes found.")
        else:
            for i, volume in enumerate(self.volumes):
                if i == self.volume_index:
                    attr = self.volume_attrs[self.volumes_hindex]
                    value = asdict(volume).get(attr)
                    volume_info = f"⊟ {attr} - {value}"
                else:
                    volume_info = f"⊟ Name - {volume.name}"
                if i == self.volume_index and self.focused_panel == "right":
                    table.add_row(
                        volume_info,
                        style=self.config.colors.PANEL_FOCUS,
                        end_section=True,
                    )
                else:
                    table.add_row(volume_info, end_section=True)
        return Panel(
            table,
            title="Volumes",
            border_style=(
                self.config.colors.CONSOLE
                if self.focused_panel == "left"
                else self.config.colors.PANEL_FOCUS
            ),
        )

    def _create_logs_panel(self, width: int) -> Panel:
        """Create the logs panel of the TUI.
        Args:
            width (int): The width of the panel.
        Returns:
            Panel: The logs panel of the TUI."""
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
            border_style=(
                self.config.colors.CONSOLE
                if self.focused_panel == "left"
                else self.config.colors.PANEL_FOCUS
            ),
        )

    def _create_right_panel(self, width: int) -> Panel:
        """Create the right panel of the TUI.
        Args:
            width (int): The width of the panel.
        Returns:
            Panel: The right panel of the TUI."""
        if self.right_panel == "containers":
            return self._create_containter_panel(width)
        elif self.right_panel == "logs":
            return self._create_logs_panel(width)
        elif self.right_panel == "volumes":
            return self._create_volumes_panel(width)

    def _create_stdout_panel(self) -> Panel:
        """Create the stdout panel of the TUI.
        Returns:
            Panel: The stdout panel of the TUI."""
        text = "\n".join(self.stdout[-self.max_stdout_lines :])
        return Panel(
            text,
            title="STDOUT",
            height=20,
            title_align="left",
            border_style=self.config.colors.CONSOLE,
        )

    def _add_output(self, output: str) -> None:
        """Add output to the stdout panel.
        Args:
            output (str): The output to add.
        Returns:
            None
        """
        self.stdout.append(output)

    def _render(self) -> None:
        """Render the TUI."""
        self.containers = self.docker_handler.get_containers()
        self.volumes = self.docker_handler.get_volumes()
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
        """Handle moving up in the TUI."""
        if self.focused_panel == "left" and self.project_index > 0:
            self.project_index -= 1
        elif self.focused_panel == "right":
            if self.right_panel == "containers" and self.container_index > 0:
                self.container_hindex = 0
                self.container_index -= 1
            elif self.right_panel == "logs" and self.logs_offset > 0:
                self.logs_offset -= 1
        self._render()

    def handle_move_down(self):
        """Handle moving down in the TUI."""
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
        self._render()

    def handle_move_right(self):
        """Handle moving right in the TUI."""
        if self.focused_panel == "right":
            if self.right_panel == "containers":
                self.container_hindex += 1
            elif self.right_panel == "volumes":
                self.volumes_hindex = (self.volumes_hindex + 1) % len(self.volume_attrs)
        self._render()

    def handle_move_left(self):
        """Handle moving left in the TUI."""
        if self.focused_panel == "right":
            if self.right_panel == "containers" and self.container_hindex > 0:
                self.container_hindex -= 1
            elif self.right_panel == "volumes" and self.volumes_hindex > 0:
                self.volumes_hindex -= 1
        self._render()

    def handle_switch_panel(self):
        """Handle switching the focused panel in the TUI."""
        self.focused_panel = "right" if self.focused_panel == "left" else "left"
        self._render()

    def handle_compose_up(self):
        """Handle running 'docker-compose up'."""
        self._add_output("docker-compose up...")

        result = self.docker_handler.compose(self.projects[self.project_index], "up")
        self._stream_docker_compose(result)
        self._render()

    def handle_compose_down(self):
        """Handle running 'docker-compose down'."""
        if self.focused_panel == "left":
            self._add_output("docker-compose down...")
            self.right_panel = "containers"

            result = self.docker_handler.compose(
                self.projects[self.project_index], "down"
            )
            self._stream_docker_compose(result)
        self._render()

    def handle_container_terminal(self):
        """Handle opening a terminal in a container."""
        self.container_terminal = True
        self._render()
        if len(self.containers) == 0:
            return
        container_id = self.containers[self.container_index].id
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
            self._add_output(f"Failed to open terminal: {str(e)}")
        self._render()

    def handle_view_logs(self):
        """Handle opening the logs panel."""
        if self.right_panel == "containers" and len(self.containers) > 0:
            self._add_output(
                "Opening log Inspection for container "
                + self.containers[self.container_index].name
                + "..."
            )
            self.right_panel = "logs"
            self.logs_offset = 0
        self._render()

    def handle_logs_page_up(self):
        """Handle scrolling up in the logs panel."""
        if self.right_panel == "logs" and self.logs_offset > 0:
            if self.logs_offset - self.max_logs_display > 0:
                self.logs_offset -= self.max_logs_display
            else:
                self.logs_offset = 0
        else:
            self.docker_monitor.kill_monitor()
            self.stdout.append("Killed monitor")
        self._render()

    def handle_logs_page_down(self):
        """Handle scrolling down in the logs panel."""
        if self.right_panel == "logs":
            if self.logs_offset + self.max_logs_display < len(self.logs.split("\n")):
                self.logs_offset += self.max_logs_display
            else:
                self.logs_offset = len(self.logs.split("\n")) - self.max_logs_display
        self._render()

    def handle_logs_home(self):
        """Handle scrolling to the top of the logs panel."""
        self.logs_offset = 0
        self._render()

    def handle_logs_end(self):
        """Handle scrolling to the bottom of the logs panel."""
        self.logs_offset = len(self.logs.split("\n")) - self.max_logs_display
        self._render()

    def handle_view_containers(self):
        """Handle opening the containers panel."""
        self.right_panel = "containers"
        self._render()

    def handle_view_volumes(self):
        """Handle opening the volumes panel."""
        self.right_panel = "volumes"
        self._render()

    def handle_default_view(self):
        """Handle returning to the default view."""
        self.container_terminal = False
        self.right_panel = "containers"
        self._render()

    def handle_quit(self):
        """Handle quitting the TUI."""
        subprocess.run(["tmux", "kill-session", "-t", "docker-tui"])

    def on_key(self):
        """Handle key presses in the TUI.
        Uses raw input for non-blocking key presses.
        Returns the handler for the key press."""
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
        """Run the TUI."""
        if "TMUX" not in os.environ:
            session_name = "docker-tui"
            subprocess.run(["tmux", "new", "-s", session_name, "python", "main.py"])
            subprocess.run(["tmux", "attach", "-t", session_name])
        else:
            self._render()
            try:
                while True:
                    handler = self.on_key()
                    if handler:
                        self.projects = self.docker_handler.get_projects_from_env()
                        self.containers = self.docker_handler.get_containers()
                        if len(self.containers) > 0:
                            self.logs = self.docker_handler.get_logs(
                                self.containers[self.container_index].id
                            )
                        handler()
            except Exception as e:
                print(e)
                pass
