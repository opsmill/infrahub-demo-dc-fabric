from __future__ import annotations

from typing import Optional, List
from pathlib import Path

import glob
from enum import Enum
try:
    from pydantic import v1 as pydantic  # type: ignore[attr-defined]
except ImportError:
    import pydantic  # type: ignore[no-redef]

from .exceptions import DirectoryNotFoundError

class InfrahubTestExpectedResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class InfrahubTestResource(str, Enum):
    RFILE = "RFile"
    TRANSFORMPYTHON = "TransformPython"
    GRAPHQL = "GraphQLQuery"

class InfrahubTest(pydantic.BaseModel):
    name: str
    expect: InfrahubTestExpectedResult
    directory: Optional[Path] = None
    input: Optional[Path] = None
    output: Optional[Path] = None

    def update_paths(self, base_dir: Path):
        if self.directory and not self.directory.is_absolute() and not self.directory.is_dir():
            self.directory = base_dir / self.directory
            if not self.directory.isdir():
                raise DirectoryNotFoundError(name=self.directory)

        if (self.input and not self.input.is_file()) or not self.input:

            search_input = self.input or "input.*"
            results = glob.glob( str(self.directory / search_input))
            if not results:
                raise FileNotFoundError(name=self.input)
            elif len(results) != 1:
                raise FileNotFoundError(f"Too many files are mathing: {self.input}, please adjust the value to match only one file.")
            self.input = Path(results[0])

        if (self.output and not self.output.is_file()) or not self.output:

            search_input = self.output or "output.*"

            results = glob.glob( str(self.directory / search_input))
            if results and len(results) != 1:
                raise FileNotFoundError(f"Too many files are mathing: {self.output}, please adjust the value to match only one file.")
            if results:
                self.output = Path(results[0])

class InfrahubTestGroup(pydantic.BaseModel):
    resource: InfrahubTestResource
    resource_name: str
    tests: List[InfrahubTest]

class InfrahubTestFileV1(pydantic.BaseModel):
    version: Optional[str] = "1.0"
    infrahub_tests: List[InfrahubTestGroup]

    class Config:
        extra = pydantic.Extra.forbid