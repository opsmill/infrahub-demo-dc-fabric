from __future__ import annotations

from typing import Iterable
import warnings
import yaml
import pytest
from pytest import Item

from .models import InfrahubTestFileV1, InfrahubTestResource
from .items import InfrahubRFileItem
from .utils import find_rfile_in_repository_config

MARKER_MAPPING = {
    "RFile": pytest.mark.infrahub_rfile
}

class InfrahubYamlFile(pytest.File):
    def collect(self) -> Iterable[Item]:
        raw = yaml.safe_load(self.path.open())

        if not "infrahub_tests" in raw:
           return

        content = InfrahubTestFileV1(**raw)

        for test_group in content.infrahub_tests:

            if test_group.resource == InfrahubTestResource.RFILE.value:
                item_class = InfrahubRFileItem
                marker = pytest.mark.infrahub_rfile

                try:
                    resource_config = find_rfile_in_repository_config(rfile=test_group.resource_name, repository_config=self.session.infrahub_repo_config)
                except ValueError as exc:
                    warnings.warn(Warning(f"Unable to find the rfile {test_group.resource_name!r} in the repository config file."))
                    continue

            for test in test_group.tests:
                name = f"{test_group.resource.value}::{test_group.resource_name}::{test.name}"
                item: pytest.Item = item_class.from_parent(
                    name=name,
                    parent=self,
                    resource_name=test_group.resource_name,
                    resource_config=resource_config,
                    spec=test)
                item.add_marker(marker, test_group.resource_name)
                yield item