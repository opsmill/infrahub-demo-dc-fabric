from __future__ import annotations

import jinja2
import pytest
import yaml

from rich.traceback import Frame, Traceback
from rich.console import Console
from infrahub_sdk.schema import InfrahubRepositoryRFileConfig


from .utils import identify_faulty_jinja_code
from .models import InfrahubTestFileV1, InfrahubTest, InfrahubTestExpectedResult
from .exceptions import RFileException, RFileUndefinedError


class InfrahubRFileItem(pytest.Item):

    def __init__(self, *args, resource_name: str, resource_config: InfrahubRepositoryRFileConfig, spec: InfrahubTest, **kwargs):
        super().__init__(*args, **kwargs)

        self.resource_name: str = resource_name
        self.resource_config: InfrahubRepositoryRFileConfig = resource_config
        spec.update_paths(base_dir=self.fspath.dirpath())
        self.spec: InfrahubTest = spec

    def runtest(self):
        templateLoader = jinja2.FileSystemLoader(searchpath=".")
        templateEnv = jinja2.Environment(loader=templateLoader, trim_blocks=True, lstrip_blocks=True)
        template = templateEnv.get_template(str(self.resource_config.template_path))

        input_data = yaml.safe_load(self.spec.input.read_text())

        try:
            rendered_tpl = template.render(data=input_data["data"])
        except jinja2.UndefinedError as exc:
            traceback = Traceback(show_locals=False)
            errors = identify_faulty_jinja_code(traceback=traceback)
            console = Console()
            with console.capture() as capture:
                console.print(f"An error occured while rendering the jinja template, RFile:{self.name!r}\n", soft_wrap=True)
                console.print(f"{exc.message}\n", soft_wrap=True)
                for frame, syntax in errors:
                    console.print(f"{frame.filename} on line {frame.lineno}\n", soft_wrap=True)
                    console.print(syntax, soft_wrap=True)
            str_output = capture.get()
            if self.spec.expect == InfrahubTestExpectedResult.PASS:
                raise RFileUndefinedError(name=self.name, message=str_output, rtb =traceback, errors=errors) from exc
            return

        if self.spec.output and rendered_tpl != self.spec.output.read_text():
            if self.spec.expect == InfrahubTestExpectedResult.PASS:
                raise RFileException(name=self.name, message="Output don't match")


    def repr_failure(self, excinfo):
        """Called when self.runtest() raises an exception."""

        if isinstance(excinfo.value, jinja2.TemplateSyntaxError):
            return "\n".join(
                [
                    "[red]Syntax Error detected on the template",
                    f"  [yellow]  {excinfo}"
                ]
            )

        if isinstance(excinfo.value, (RFileUndefinedError, RFileException)):
            return excinfo.value.message

    def reportinfo(self):
        return self.path, 0, f"resource: {self.name}"
