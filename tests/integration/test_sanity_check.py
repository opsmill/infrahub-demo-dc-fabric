from pathlib import Path
import pytest
from infrahub_sdk import InfrahubClient
from infrahub_sdk.protocols import CoreGenericRepository
from infrahub_sdk.testing.docker import TestInfrahubDockerClient
from infrahub_sdk.testing.repository import GitRepo
from infrahub_sdk.testing.schemas.car_person import (
    SchemaCarPerson,
)

DATA_GENERATORS = [
    "create_basic.py",
    "create_location.py",
    "create_topology.py",
    "create_security_nodes.py",
]


class TestProposeChangeRepository(TestInfrahubDockerClient, SchemaCarPerson):
    @pytest.fixture(scope="class")
    def infrahub_version(self) -> str:
        """For now, the version of infrahub can be defined using this fixture,
        To use a local build, set the value to `local`

        Mostlikely this will change in the future release of infrahub-testcontainers,
        """
        return "1.1.2"

    @pytest.fixture(scope="class")
    def infrahub_address(self, infrahub_port: int) -> str:
        return f"http://localhost:{infrahub_port}"

    @pytest.mark.asyncio
    async def test_load_schema(
        self,
        default_branch: str,
        client: InfrahubClient,
        schemas,
    ) -> None:
        """Load the schemas from the local repository in infrahub and validate that no error have been reported"""
        await client.schema.wait_until_converged(branch=default_branch)

        resp = await client.schema.load(
            schemas=schemas, branch=default_branch, wait_until_converged=True
        )
        assert resp.errors == {}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("generator", DATA_GENERATORS)
    async def test_load_initial_data(
        self, infrahub_address: str, generator: str
    ) -> None:
        """Execute data loader scripts using the `infrahubctl run` command"""
        self.execute_ctl_run(address=infrahub_address, script=f"bootstrap/{generator}")

    @pytest.mark.asyncio
    async def test_generate_topology(
        self,
        infrahub_address: str,
    ) -> None:
        self.execute_ctl_run(
            address=infrahub_address,
            script="bootstrap/generate_topology.py topology=fra05-pod1",
        )

    @pytest.mark.asyncio
    async def test_load_repository(
        self,
        client: InfrahubClient,
        default_branch: str,
        remote_repos_dir: Path,
        root_directory: Path,
    ) -> None:
        """Add the local directory as a repository in Infrahub and wait for the import to be complete"""

        repo = GitRepo(
            name="local-repository",
            src_directory=root_directory,
            dst_directory=remote_repos_dir,
        )
        await repo.add_to_infrahub(client=client)
        in_sync = await repo.wait_for_sync_to_complete(client=client)
        assert in_sync

        repos = await client.all(kind=CoreGenericRepository)
        assert repos
