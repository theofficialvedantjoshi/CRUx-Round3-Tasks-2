import time
import os
import blessed
from rich.console import Console
from rich.layout import ColumnSplitter, Layout, RowSplitter
from rich.panel import Panel
from rich.table import Table
from backend import DockerHandler
from rich import box


class TUI:
    def __init__(self):
        self.term = blessed.Terminal()
        self.keybinds = {
            "\x1b[A": self.handle_up,
            "\x1b[B": self.handle_down,
            "\x1b[C": self.handle_right,
            "\x1b[D": self.handle_left,
            "\t": self.handle_tab,
            "u": self.handle_u,
            "d": self.handle_d,
            "l": self.handle_l,
            "k": self.handle_page_up,
            "j": self.handle_page_down,
            "g": self.handle_home,
            "f": self.handle_end,
            "c": self.handle_c,
            "q": self.handle_q,
            "v": self.handle_v,
            "\x1b": self.handle_escape,
        }
        self.docker_handler = DockerHandler()
        self.projects = self.docker_handler.get_projects_from_env()
        self.containers = self.docker_handler.get_containers()
        self.volumes = self.docker_handler.get_volumes()
        self.console = Console(style="dark_blue")
        self.project_index = 0
        self.container_index = 0
        self.container_hindex = 0
        self.volume_index = 0
        self.volume_attrs = ["name", "driver", "mountpoints", "containers"]
        self.volumes_hindex = 0
        self.focused_panel = "left"
        self.right_panel = "containers"
        self.stdout = []
        self.max_stdout_lines = 20
        self.logs = None
        self.logs_offset = 0
        self.max_logs_display = 15

    def _stream_docker_compose(self, process):
        for stderr_line in iter(process.stderr.readline, ""):
            self.add_output(stderr_line.strip())
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
        return Panel(text, title="Stdout", height=10)

    def add_output(self, output):
        self.stdout.append(output)

    def render(self):
        self.console.clear()
        os.system("clear")
        left_panel = self._create_left_panel(100)
        right_panel = self._create_right_panel(100)
        stdout_panel = self._create_stdout_panel()
        top_layout = Layout()
        top_layout.split(left_panel, right_panel, splitter=RowSplitter())
        layout = Layout(
            name="Docker Compose TUI",
        )
        layout.split(top_layout, stdout_panel, splitter=ColumnSplitter())
        self.console.print(layout)

    def handle_up(self):
        if self.focused_panel == "left" and self.project_index > 0:
            self.project_index -= 1
        elif self.focused_panel == "right":
            if self.right_panel == "containers" and self.container_index > 0:
                self.container_hindex = 0
                self.container_index -= 1
            elif self.right_panel == "logs" and self.logs_offset > 0:
                self.logs_offset -= 1

    def handle_down(self):
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

    def handle_right(self):
        if self.focused_panel == "right":
            if self.right_panel == "containers":
                self.container_hindex += 1
            elif self.right_panel == "volumes":
                self.volumes_hindex = (self.volumes_hindex + 1) % len(self.volume_attrs)

    def handle_left(self):
        if self.focused_panel == "right":
            if self.right_panel == "containers" and self.container_hindex > 0:
                self.container_hindex -= 1
            elif self.right_panel == "volumes" and self.volumes_hindex > 0:
                self.volumes_hindex -= 1

    def handle_tab(self):
        self.focused_panel = "right" if self.focused_panel == "left" else "left"
        self.render()

    def handle_u(self):
        self.add_output("docker-compose up...")

        result = self.docker_handler.compose(self.projects[self.project_index], "up")
        self._stream_docker_compose(result)

    def handle_d(self):
        if self.focused_panel == "left":
            self.add_output("docker-compose down...")
            self.right_panel = "containers"

            result = self.docker_handler.compose(
                self.projects[self.project_index], "down"
            )
            self._stream_docker_compose(result)

    def handle_l(self):
        if self.right_panel == "containers" and len(self.containers) > 0:
            self.add_output(
                "Opening log Inspection for container "
                + self.containers[self.container_index].get("name")
                + "..."
            )
            self.right_panel = "logs"
            self.logs_offset = 0

    def handle_page_up(self):
        if self.right_panel == "logs" and self.logs_offset > 0:
            if self.logs_offset - self.max_logs_display > 0:
                self.logs_offset -= self.max_logs_display
            else:
                self.logs_offset = 0

    def handle_page_down(self):
        if self.right_panel == "logs":
            if self.logs_offset + self.max_logs_display < len(self.logs.split("\n")):
                self.logs_offset += self.max_logs_display
            else:
                self.logs_offset = len(self.logs.split("\n")) - self.max_logs_display

    def handle_home(self):
        self.logs_offset = 0

    def handle_end(self):
        self.logs_offset = len(self.logs.split("\n")) - self.max_logs_display

    def handle_c(self):
        self.right_panel = "containers"

    def handle_v(self):
        self.right_panel = "volumes"

    def handle_q(self):
        self.right_panel = "containers"

    def handle_escape(self):
        exit()

    def on_key(self):
        with self.term.cbreak(), self.term.hidden_cursor():
            while True:
                key = self.term.inkey(timeout=0.1)
                handler = self.keybinds.get(key, None)
                if handler:
                    self.projects = self.docker_handler.get_projects_from_env()
                    self.containers = self.docker_handler.get_containers()
                    if len(self.containers) > 0:
                        self.logs = self.docker_handler.get_logs(
                            self.containers[self.container_index].get("id")
                        )
                    handler()
                time.sleep(0.1)
                self.render()

    def run(self):
        self.render()
        try:
            self.on_key()
        except KeyboardInterrupt:
            pass
