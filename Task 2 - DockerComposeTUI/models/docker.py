from dataclasses import dataclass


@dataclass
class Container:
    name: str
    id: str
    status: str
    health: str
    image: str
    ports: str
    project: str


@dataclass
class Volume:
    name: str
    driver: str
    mountpoint: str
    containers: str
