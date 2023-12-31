import os
from typing import Optional

import click

from exasol.ds.sandbox.cli.cli import cli
from exasol.ds.sandbox.cli.common import add_options
from exasol.ds.sandbox.cli.options.aws_options import aws_options
from exasol.ds.sandbox.cli.options.logging import logging_options
from exasol.ds.sandbox.lib.aws_access.aws_access import AwsAccess
from exasol.ds.sandbox.lib.config import default_config_object
from exasol.ds.sandbox.lib.logging import set_log_level
from exasol.ds.sandbox.lib.release_build.run_release_build import run_start_release_build


@cli.command()
@add_options(aws_options)
@add_options(logging_options)
@click.option('--upload-url', type=str, required=False,
              help="""The URL of the Github release where artifacts will be stored.""")
@click.option('--branch', type=str, required=True,
              help="""The branch of the repository which will be used.""")
def start_release_build(
        aws_profile: Optional[str],
        log_level: str,
        upload_url: str,
        branch: str):
    """
    This command  triggers the AWS release Codebuild to generate a new sandbox version.
    """
    set_log_level(log_level)
    run_start_release_build(AwsAccess(aws_profile), default_config_object,
                            upload_url, branch, os.getenv("GITHUB_TOKEN"))
