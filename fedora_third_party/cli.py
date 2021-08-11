import click
import logging
import os
import sys

from . import config
from .table import Table


pass_config = click.make_pass_decorator(config.Config, ensure=True)


def assert_root():
    if os.geteuid() != 0:
        click.echo("fedora-third-party must be run as root.")
        sys.exit(1)


@click.group()
@click.option("-v", "--verbose", is_flag=True,
              help="Show verbose debugging output")
@pass_config
def cli(cfg: config.Config, verbose: bool):
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


@cli.command()
@pass_config
@click.option("--config-only", is_flag=True,
              help="Don't change existing repositories")
def enable(cfg: config.Config, config_only: bool):
    """Enable third-party repositories"""
    assert_root()

    cfg.enable()

    if not config_only:
        for repository in cfg.list_repositories():
            repository.enable()

        cfg.update_seen_repositories()


@cli.command()
@click.option("--config-only", is_flag=True,
              help="Don't change existing repositories")
@pass_config
def disable(cfg: config.Config, config_only: bool):
    """Disable third-party repositories"""
    assert_root()

    cfg.disable()

    if not config_only:
        for repository in cfg.list_repositories():
            repository.disable()

        cfg.update_seen_repositories()


@cli.command()
@click.option("-q", "--quiet", is_flag=True,
              help="Don't print anything to stdout")
@pass_config
def query(cfg: config.Config, quiet: bool):
    """Query the current status"""
    if quiet:
        sys.exit(0 if cfg.is_enabled() else 1 if cfg.is_enabled_set() else 2)
    else:
        if cfg.is_enabled():
            print("Third-party repositories are enabled.")
        elif cfg.is_enabled_set():
            print("Third-party repositories are disabled.")
        else:
            print("Third-party repositories are disabled (no selection has been made).")


@cli.command()
@click.option("--csv", is_flag=True,
              help="Print output in csv form")
@click.option("--columns",
              help="Comma separated list of columns [name,type]",
              default="name,type")
@pass_config
def list(cfg: config.Config, csv: bool, columns: str):
    """List currently configured repositories"""

    table = Table()
    table.add_column("name", "Name", "name")
    table.add_column("type", "Type", "type")

    repositories = sorted(cfg.list_repositories(), key=lambda x: x.name)
    table.dump(repositories, csv=csv, columns=[x.strip() for x in columns.split(",")])


@cli.command()
@pass_config
def refresh(cfg: config.Config):
    """Apply system policy to newly-installed third-party repositories"""

    assert_root()

    for repository in cfg.list_repositories():
        if not repository.is_seen():
            if cfg.is_enabled():
                repository.enable()
            else:
                repository.disable()

    cfg.update_seen_repositories()
