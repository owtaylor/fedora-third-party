import click
import logging
import os
import sys

from . import config
from .repository import ModificationFailedError
from .table import Table


pass_config = click.make_pass_decorator(config.Config, ensure=True)


def assert_root():
    if os.geteuid() != 0:
        click.echo("fedora-third-party must be run as root.")
        sys.exit(1)


class ClickHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord):
        if self.formatter:
            context = click.get_current_context()
            output = self.formatter.format(record)
            click.echo(
                context.command_path + ":" +
                click.style(record.levelname, fg="red", bold=True) +
                ": " + output,
                err=True
            )


@click.group()
@click.option("-v", "--verbose", is_flag=True,
              help="Show verbose debugging output")
@pass_config
def cli(cfg: config.Config, verbose: bool):
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING,
                            handlers=[ClickHandler()],
                            format="%(message)s")


@cli.command()
@pass_config
@click.option("--config-only", is_flag=True,
              help="Don't change existing repositories")
def enable(cfg: config.Config, config_only: bool):
    """Enable third-party repositories"""
    assert_root()

    cfg.enable()

    if not config_only:
        retry_repositories = set()
        for repository in cfg.list_repositories():
            try:
                repository.enable()
            except ModificationFailedError:
                retry_repositories.add(repository)

        cfg.update_seen_repositories(retry_repositories=retry_repositories)
        cfg.dnf_config_editor.save()


def do_disable(cfg: config.Config, config_only: bool):
    assert_root()

    cfg.disable()

    if not config_only:
        retry_repositories = set()
        for repository in cfg.list_repositories():
            try:
                repository.disable()
            except ModificationFailedError:
                retry_repositories.add(repository)

        cfg.update_seen_repositories(retry_repositories=retry_repositories)
        cfg.dnf_config_editor.save()


@cli.command()
@click.option("--config-only", is_flag=True,
              help="Don't change existing repositories")
@pass_config
def disable(cfg: config.Config, config_only: bool):
    """Disable third-party repositories"""
    do_disable(cfg, config_only)


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
@click.option("-a", "--all", is_flag=True,
              help="Show repositories even if they are replaced by a system repository")
@click.option("--csv", is_flag=True,
              help="Print output in csv form")
@click.option("--columns",
              help="Comma separated list of columns [name,type]",
              default="name,type")
@pass_config
def list(cfg: config.Config, all: bool, csv: bool, columns: str):
    """List currently configured repositories"""

    table = Table()
    table.add_column("name", "Name", "name")
    table.add_column("type", "Type", "type")

    repositories = cfg.list_repositories()
    if not all:
        repositories = [r for r in cfg.list_repositories() if not r.is_hidden()]

    repositories = sorted(repositories, key=lambda x: x.name)
    table.dump(repositories, csv=csv, columns=[x.strip() for x in columns.split(",")])


@cli.command()
@pass_config
def refresh(cfg: config.Config):
    """Apply system policy to newly-installed third-party repositories"""

    assert_root()

    if not cfg.is_enabled_set():
        return

    unseen = [r for r in cfg.list_repositories() if not r.is_seen()]
    if len(unseen) == 0:
        return

    retry_repositories = []
    for repository in unseen:
        try:
            if cfg.is_enabled():
                repository.enable()
            else:
                repository.disable()
        except ModificationFailedError:
            retry_repositories.append(repository)

    cfg.update_seen_repositories(retry_repositories=retry_repositories)
    cfg.dnf_config_editor.save()


def opt_out():
    """Single-purpose script to allow more liberal polkit rules"""

    assert_root()

    cfg = config.Config()
    if cfg.is_enabled_set():
        print("Use 'fedora-third-party disable' to change the existing status.", file=sys.stderr)
        sys.exit(1)

    # We invoke the full disable mechanism to make sure that we add flatpak repositories disabled
    do_disable(cfg, False)
