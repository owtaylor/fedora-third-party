from unittest.mock import patch
from textwrap import dedent

from click.testing import CliRunner
import pytest

from fedora_third_party.dnf_config_editor import DnfConfigEditor
from fedora_third_party.cli import cli, opt_out


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
        ['flatpak', 'remote-add', '--from', 'flathub',
         str(setup.root / "usr/lib/fedora-third-party/conf.d/flathub.flatpakrepo")],
    ])
    setup.assert_dnf_repo_status(enabled=True)

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
        ['flatpak', 'remote-delete', 'flathub'],
    ])
    setup.assert_dnf_repo_status(enabled=False)

    result = runner.invoke(cli, ['query'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == 'Third-party repositories are disabled.\n'

    result = runner.invoke(cli, ['query', '-q'], obj=setup.cfg)
    assert result.exit_code == 1
    assert result.output == ''


def test_cli_config_only(setup):
    runner = CliRunner()
    result = runner.invoke(cli, ['enable', '--config-only'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''
    setup.assert_dnf_repo_status(enabled=False)

    setup.reload_config()
    result = runner.invoke(cli, ['query', '-q'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''

    # Simulate manually changing the override status of the rpmfusion repo
    editor = DnfConfigEditor(root=setup.root)
    editor.set_enabled("rpmfusion-nonfree-nvidia-driver", True)
    editor.save()

    runner = CliRunner()
    result = runner.invoke(cli, ['disable', '--config-only'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''
    setup.assert_dnf_repo_status(enabled=True)

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

    # Simulate manually changing the override status of the rpmfusion repo
    editor = DnfConfigEditor(root=setup.root)
    editor.set_enabled("rpmfusion-nonfree-nvidia-driver", not enabled)
    editor.save()

    libconfdir = setup.root / "usr/lib/fedora-third-party/conf.d"
    with open(libconfdir / "myrepo.conf", "w") as f:
        f.write(dedent("""\
            [myrepo]
            type=dnf
        """))

    reposdir = setup.root / "etc/yum.repos.d"
    with open(reposdir / "myrepo.repo", "w") as f:
        f.write(dedent("""\
            [myrepo]
            name=My Repo
            enabled=42  # neither enabled or disabled
        """))

    setup.reload_config()

    result = runner.invoke(cli, ['refresh'], obj=setup.cfg)
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == ''

    # Check that the rpm fusion repo is unchanged
    setup.assert_dnf_repo_status(enabled=not enabled)
    # But the new repo is enabled
    setup.assert_dnf_repo_status(repofile="myrepo.repo", enabled=enabled)


def test_cli_opt_out(setup):
    with patch("fedora_third_party.config.Config", return_value=setup.cfg):
        opt_out()

    runner = CliRunner()

    setup.reload_config()
    result = runner.invoke(cli, ['query'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == 'Third-party repositories are disabled.\n'


def test_cli_opt_out_later(setup, capsys):
    runner = CliRunner()

    result = runner.invoke(cli, ['enable'], obj=setup.cfg)
    assert result.exit_code == 0
    assert result.output == ''

    with patch("fedora_third_party.config.Config", return_value=setup.cfg), \
         patch("sys.exit", return_value=None) as mock_exit:
        opt_out()

    assert mock_exit.call_args == ((1,),)

    assert capsys.readouterr().err == \
        "Use 'fedora-third-party disable' to change the existing status.\n"
