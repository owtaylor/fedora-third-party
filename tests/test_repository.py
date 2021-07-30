from configparser import ConfigParser

from fedora_third_party.repository import DnfRepository, FlatpakRepository


def test_dnf_repository(setup):
    parser = ConfigParser()
    parser.add_section('myrepo')
    parser.set('myrepo', 'type', 'dnf')
    parser.set('myrepo', 'repository', 'myrepo')
    repository = DnfRepository(setup.cfg, 'myrepo', parser)
    assert not repository.is_seen()
    repository.enable()
    repository.disable()
    assert setup.calls == [
        ['dnf', 'config-manager', '--set-enabled', 'myrepo'],
        ['dnf', 'config-manager', '--set-disabled', 'myrepo'],
    ]


def make_flatpak_repository(setup):
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
         str(setup.root / "usr/lib/fedora-third-party/conf.d/myrepo.flatpakrepo")],
    ]

    setup.set_flatpak_remotes({
        "myrepo": "/etc/myrepo.filter"
    })

    setup.calls = []
    repository.disable()
    assert setup.calls == [
        ['flatpak', 'remote-delete', 'myrepo'],
    ]


def test_flatpak_repository_existing(setup):
    repository = make_flatpak_repository(setup)

    setup.set_flatpak_remotes({
        "myrepo": "/etc/myrepo.filter"
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
         str(setup.root / "usr/lib/fedora-third-party/conf.d/myrepo.flatpakrepo")],
    ]

    setup.set_flatpak_remotes({
    })

    setup.calls = []
    repository.disable()
    assert setup.calls == [
    ]


def test_flatpak_repository_keep_unfiltered(setup):
    repository = make_flatpak_repository(setup)

    repository.enable()

    setup.set_flatpak_remotes({
        "myrepo": "-"
    })

    setup.calls = []
    repository.disable()
    assert setup.calls == [
    ]
