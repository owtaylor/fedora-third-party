from unittest.mock import patch
from textwrap import dedent

from click.testing import CliRunner
import pytest

from fedora_third_party.cli import cli


def test_cli(setup):
    runner = CliRunner()
    result = runner.invoke(cli, ['query'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == 'Third-party repositories are disabled (no selection has been made).\n'

    result = runner.invoke(cli, ['query', '-q'], obj=setup.cfg)
    assert result.exit_code == 2
    assert result.output == ''

    setup.calls = []
    result = runner.invoke(cli, ['enable'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''
    assert sorted(setup.calls) == sorted([
        ['dnf', 'config-manager', '--set-enabled', 'rpmfusion-nonfree-nvidia-driver'],
        ['flatpak', 'remote-add', '--from', 'flathub',
         str(setup.root / "usr/lib/fedora-third-party/conf.d/flathub.flatpakrepo")],
    ])

    result = runner.invoke(cli, ['query'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == 'Third-party repositories are enabled.\n'

    result = runner.invoke(cli, ['query', '-q'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''

    setup.set_flatpak_remotes({
        "flathub": "/etc/fedora-flathub.filter",
    })

    setup.calls = []
    result = runner.invoke(cli, ['disable'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''
    assert sorted(setup.calls) == sorted([
        ['dnf', 'config-manager', '--set-disabled', 'rpmfusion-nonfree-nvidia-driver'],
        ['flatpak', 'remote-delete', 'flathub'],
    ])

    result = runner.invoke(cli, ['query'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == 'Third-party repositories are disabled.\n'

    result = runner.invoke(cli, ['query', '-q'], obj=setup.cfg)
    assert result.exit_code == 1
    assert result.output == ''


def test_cli_config_only(setup):
    runner = CliRunner()
    setup.calls = []
    result = runner.invoke(cli, ['enable', '--config-only'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''
    assert setup.calls == []

    setup.reload_config()
    result = runner.invoke(cli, ['query', '-q'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''

    runner = CliRunner()
    setup.calls = []
    result = runner.invoke(cli, ['disable', '--config-only'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''
    assert setup.calls == []

    setup.reload_config()
    result = runner.invoke(cli, ['query', '-q'], obj=setup.cfg)
    assert result.exit_code == 1
    assert result.output == ''


def test_cli_nonroot(setup):
    runner = CliRunner()
    with patch("os.geteuid", return_value=1000):
        result = runner.invoke(cli, ['enable'], obj=setup.cfg)
        assert result.exit_code == 1
        assert result.output == "fedora-third-party must be run as root.\n"


def test_cli_verbose(setup):
    runner = CliRunner()
    result = runner.invoke(cli, ['-v', 'query', '-q'], obj=setup.cfg)
    assert result.exit_code == 2
    assert result.output == ''


def test_cli_list(setup):
    runner = CliRunner()
    result = runner.invoke(cli, ['list'], obj=setup.cfg)
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == dedent("""\
        Name                            Type
        ------------------------------- -------
        flathub                         flatpak
        rpmfusion-nonfree-nvidia-driver dnf
    """)


def test_cli_list_csv(setup):
    runner = CliRunner()
    result = runner.invoke(cli, ['list', '--csv'], obj=setup.cfg)
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == dedent("""\
        flathub,flatpak
        rpmfusion-nonfree-nvidia-driver,dnf
    """)


def test_cli_list_columns(setup):
    runner = CliRunner()
    result = runner.invoke(cli, ['list', '--csv', '--columns=type'], obj=setup.cfg)
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == dedent("""\
        flatpak
        dnf
    """)


@pytest.mark.parametrize("enabled", [False, True])
def test_cli_refresh(setup, enabled):
    runner = CliRunner()

    if enabled:
        result = runner.invoke(cli, ['enable'], obj=setup.cfg)
        assert result.exit_code == 0
        assert result.output == ''
    else:
        result = runner.invoke(cli, ['disable'], obj=setup.cfg)
        assert result.exit_code == 0
        assert result.output == ''

    libconfdir = setup.root / "usr/lib/fedora-third-party/conf.d"
    with open(libconfdir / "myrepo.conf", "w") as f:
        f.write(dedent("""\
            [myrepo]
            type=dnf
        """))

    setup.reload_config()

    setup.calls = []
    result = runner.invoke(cli, ['refresh'], obj=setup.cfg)
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == ''

    if enabled:
        assert setup.calls == [
            ['dnf', 'config-manager', '--set-enabled', 'myrepo']
        ]
    else:
        assert setup.calls == [
            ['dnf', 'config-manager', '--set-disabled', 'myrepo']
        ]
