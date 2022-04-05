from configparser import ConfigParser
from textwrap import dedent
from typing import Optional

from fedora_third_party.repository import DnfRepository, FlatpakRepository


def test_dnf_repository(setup):
    reposdir = setup.root / "etc/yum.repos.d"
    with open(reposdir / "myrepo.repo", "w") as f:
        f.write(dedent("""\
            [myrepo]
            name=My Repo
            enabled=0
        """))

    parser = ConfigParser()
    parser.add_section('myrepo')
    parser.set('myrepo', 'type', 'dnf')
    parser.set('myrepo', 'repository', 'myrepo')
    repository = DnfRepository(setup.cfg, 'myrepo', parser)
    assert not repository.is_seen()
    assert not repository.is_hidden()
    repository.enable()
    setup.cfg.dnf_config_editor.save()
    setup.assert_dnf_repo_status(repofile="myrepo.repo", enabled=True)
    repository.disable()
    setup.cfg.dnf_config_editor.save()
    setup.assert_dnf_repo_status(repofile="myrepo.repo", enabled=False)


def make_flatpak_repository(setup, title: Optional[str] = "My Repo"):
    libconfdir = setup.root / "usr/lib/fedora-third-party/conf.d"
    with open(libconfdir / "myrepo.flatpakrepo", "w") as f:
        f.write("[Flatpak Repo]\n")
        if title is not None:
            f.write(f"Title={title}\n")

    parser = ConfigParser()
    parser.add_section('myrepo')
    parser.set('myrepo', 'type', 'flatpak')
    parser.set('myrepo', 'remote', 'myrepo')
    parser.set('myrepo', 'flatpakrepo', 'myrepo.flatpakrepo')
    parser.set('myrepo', 'keep_unfiltered', 'yes')
    return FlatpakRepository(setup.cfg, 'myrepo', parser)


def test_flatpak_repository(setup):
    repository = make_flatpak_repository(setup)

    setup.calls = []
    repository.enable()
    assert setup.calls == [
        ['flatpak', 'remote-add', '--from', 'myrepo',
         str(setup.root / "usr/lib/fedora-third-party/conf.d/myrepo.flatpakrepo"),
         '--title', 'My Repo'],
    ]

    setup.set_flatpak_remotes({
        "myrepo": ("/etc/myrepo.filter", False)
    })

    setup.calls = []
    repository.disable()
    assert setup.calls == [
        ['flatpak', 'remote-modify', 'myrepo', '--disable'],
    ]

    setup.set_flatpak_remotes({
        "myrepo": ("/etc/myrepo.filter", True)
    })

    setup.calls = []
    repository.enable()
    assert setup.calls == [
        ['flatpak', 'remote-modify', 'myrepo', '--enable'],
    ]


def test_flatpak_repository_enable_no_title(setup):
    repository = make_flatpak_repository(setup, title=None)

    setup.calls = []
    repository.enable()
    assert setup.calls == [
        ['flatpak', 'remote-add', '--from', 'myrepo',
         str(setup.root / "usr/lib/fedora-third-party/conf.d/myrepo.flatpakrepo")],
    ]


def test_flatpak_repository_existing(setup):
    repository = make_flatpak_repository(setup)

    setup.set_flatpak_remotes({
        "myrepo": ("/etc/myrepo.filter", False)
    })

    setup.calls = []
    repository.enable()
    assert setup.calls == [
    ]

    setup.calls = []
    repository.disable()
    assert setup.calls == [
    ]


def test_flatpak_repository_was_removed(setup):
    repository = make_flatpak_repository(setup)

    setup.calls = []
    repository.enable()
    assert setup.calls == [
        ['flatpak', 'remote-add', '--from', 'myrepo',
         str(setup.root / "usr/lib/fedora-third-party/conf.d/myrepo.flatpakrepo"),
         '--title', 'My Repo'],
    ]

    setup.set_flatpak_remotes({
    })

    setup.calls = []
    repository.disable()
    assert setup.calls == [
    ]


def test_flatpak_repository_not_added_is_unseen(setup):
    repository = make_flatpak_repository(setup)

    repository.cfg.update_seen_repositories()
    assert not repository.is_seen()


def test_flatpak_repository_keep_unfiltered(setup):
    repository = make_flatpak_repository(setup)

    repository.enable()

    setup.set_flatpak_remotes({
        "myrepo": ("-", False)
    })

    setup.calls = []
    repository.disable()
    assert setup.calls == [
    ]


def test_flatpak_repository_hide_unfiltered(setup):
    repository = make_flatpak_repository(setup)

    repository.enable()

    assert not repository.is_hidden()

    setup.set_flatpak_remotes({
        "myrepo": ("-", False)
    })

    assert repository.is_hidden()
