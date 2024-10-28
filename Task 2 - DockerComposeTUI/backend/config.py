import os

from models import Colors, Config, ProjectConfig
from yaml import Loader, load


def get_config(projects: list[str]):
    if not os.path.exists(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "dockertui.config.yaml"
        )
    ):
        return (Config(), ProjectConfig())
    try:
        with open(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "dockertui.config.yaml"
            )
        ) as file:
            default_config = Config().from_dict(load(file, Loader=Loader))
    except Exception as e:
        print("Invalid Default Config File.\nUsing default config.")
        default_config = Config()
    if default_config.colors != Colors():
        print("Invalid Default Config File.\nUsing default config.")
        default_config = Config()
    project_configs = {}
    for project in projects:
        if not os.path.exists(f"{project}/project.config.yaml"):
            project_configs[project] = ProjectConfig()
            continue
        try:
            with open(f"{project}/project.config.yaml") as file:
                project_configs[project] = ProjectConfig().from_dict(
                    load(file, Loader=Loader)
                )
        except Exception as e:
            print(f"Invalid Config File for {project}.\nUsing default config.")
            project_configs[project] = ProjectConfig()
    return (default_config, project_configs)
