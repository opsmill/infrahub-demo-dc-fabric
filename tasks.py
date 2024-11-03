import os

from pathlib import Path

from invoke import task, Context  # type: ignore

MAIN_DIRECTORY_PATH = Path(__file__).parent

DATA_GENERATORS = [
    "create_basic.py",
    "create_location.py",
    "create_topology.py",
    "create_security_nodes.py"
]

# If no version is indicated, we will take the latest
VERSION = os.getenv("INFRAHUB_VERSION", None)
COMPOSE_COMMAND = f"curl https://infrahub.opsmill.io/{VERSION if VERSION else ''} | docker compose -f -"
COMPOSE_COMMAND_LOCAL = "docker compose"


def has_local_docker_file() -> bool:
    file_path = Path(MAIN_DIRECTORY_PATH, "docker-compose.yml")
    return file_path.is_file()


def get_docker_command() -> str:
    if has_local_docker_file():
        return COMPOSE_COMMAND_LOCAL
    return COMPOSE_COMMAND


@task
def start(context: Context) -> None:
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(f"{get_docker_command()} up -d")

@task
def load_schema(context: Context, schema: Path=Path("./models/*.yml")) -> None:
    context.run(f"infrahubctl schema load {schema} --wait 30")

@task
def load_data(context: Context) -> None:
    with context.cd(MAIN_DIRECTORY_PATH):
        for generator in DATA_GENERATORS:
            context.run(f"infrahubctl run generators/{generator}")

@task
def destroy(context: Context) -> None:
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(f"{get_docker_command()} down -v")

@task
def stop(context: Context) -> None:
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(f"{get_docker_command()} down")

@task
def restart(context: Context, component: str="")-> None:
    with context.cd(MAIN_DIRECTORY_PATH):
        if component:
            context.run(f"{get_docker_command()} restart {component}")
            return

        context.run(f"{get_docker_command()} restart")


@task
def format(context: Context) -> None:
    """Run RUFF to format all Python files."""

    exec_cmds = ["ruff format .", "ruff check . --fix"]
    with context.cd(MAIN_DIRECTORY_PATH):
        for cmd in exec_cmds:
            context.run(cmd)


@task
def lint_yaml(context: Context) -> None:
    """Run Linter to check all Python files."""
    print(" - Check code with yamllint")
    exec_cmd = "yamllint ."
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task
def lint_mypy(context: Context) -> None:
    """Run Linter to check all Python files."""
    print(" - Check code with mypy")
    exec_cmd = "mypy --show-error-codes infrahub_sdk"
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task
def lint_ruff(context: Context) -> None:
    """Run Linter to check all Python files."""
    print(" - Check code with ruff")
    exec_cmd = "ruff check ."
    with context.cd(MAIN_DIRECTORY_PATH):
        context.run(exec_cmd)


@task(name="lint")
def lint_all(context: Context) -> None:
    """Run all linters."""
    lint_yaml(context)
    lint_ruff(context)
    lint_mypy(context)