from tui.tui import TUI
from backend.config import ConfigHandler

if __name__ == "__main__":
    config_handler = ConfigHandler()
    result = config_handler.validate_config()
    if result != "Success":
        print(result, "\nPlease check the format of your config file.")
        exit(1)
    tui = TUI()
    tui.run()
