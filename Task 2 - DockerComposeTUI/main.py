from tui.tui import TUI
from backend import ConfigHandler, DockerMonitor

if __name__ == "__main__":
    monitor = DockerMonitor()
    config_handler = ConfigHandler()
    result = config_handler.validate_config()
    if result != "Success":
        print(result, "\nPlease check the format of your config file.")
        exit(1)
    tui = TUI()
    tui.run()
