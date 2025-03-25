import pytest
from pathlib import Path

from typing import Any
from infrahub_sdk.yaml import SchemaFile

CURRENT_DIRECTORY = Path(__file__).parent.resolve()


@pytest.fixture
def root_directory() -> Path:
    """
    Return the path of the root directory of the repository.
    This fixture need to be adjusted based on the layout of the project
    """
    return CURRENT_DIRECTORY.parent.parent


@pytest.fixture
def schemas_directory(root_directory: Path) -> Path:
    return root_directory / "models"


@pytest.fixture
def schemas(schemas_directory: Path) -> list[dict[str, Any]]:
    schema_files = SchemaFile.load_from_disk(paths=[schemas_directory])
    return [item.content for item in schema_files if item.content]
