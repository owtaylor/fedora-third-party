import click
import logging
import os
import sys

from . import config


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
def enable(cfg: config.Config):
    """Enable third-party repositories"""
    assert_root()

    cfg.enable()

    for repository in cfg.list_repositories():
        repository.enable()

    cfg.update_seen_repositories()


@cli.command()
@pass_config
def disable(cfg: config.Config):
    """Disable third-party repositories"""
    assert_root()

    cfg.disable()

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
        sys.exit(0 if cfg.is_enabled() else 1)
    else:
        print("yes" if cfg.is_enabled() else "no")


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
