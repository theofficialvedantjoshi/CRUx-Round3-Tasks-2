# CRUx-Round3-Tasks-2

**This repository contains my submissions for the CRUx Dev Inductions Round 3 tasks 2024-25 Sem 1.**

## Task 1 - Chessify

A Chess Discord Bot integrated with Lichess API that allows users to play chess games, stream games, challenge ai and other users, create gifs of games, and more.

## Task 2 - DockerComposeTUI

A TUI that wraps the Docker Compose CLI. It allows users to manage their Docker Compose projects using a simple and intuitive interface. Users can view containers, volumes, logs, monitor containers and get email alerts, and backup volumes locally.

### Usage

- Python 3.9+ and a unix-based system is required to run the tasks.
- Each task is in a separate directory.
- Clone the repository.
- Create a virtual environment using `python -m venv .venv`
- Activate the virtual environment using `source .venv/bin/activate`
- Install the required packages using `pip install -r requirements.txt`
- `cd` into the directory containing the task you want to run.
  - For Task 1: `cd 'Task 1 - LichessDiscordBot'`
  - For Task 2: `cd 'Task 2 - DockerComposeTUI'`
- Follow other instructions in the README of the task directory.

### Notes

- None of the projects have been hosted on a server. They are all run locally.
- The required API keys are mentioned in the `.env.example` file. The user needs to create a .env file and add these keys.
- Instructions for setting up the developer keys are in the README of each task directory.
