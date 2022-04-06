from pathlib import Path
from subprocess import check_call
from textwrap import dedent
from typing import Dict, Tuple
from unittest import mock

import pytest

from fedora_third_party.config import Config
from fedora_third_party.repository import get_flatpak_remotes


class TestSetup:
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.calls = []
        self.exceptions = {}
        self.root = Path(self.tmpdir) / "root"
        self.set_flatpak_remotes({})

    def _maybe_raise(self, args):
        if args[0] == "flatpak" and args[1] in self.exceptions:
            raise self.exceptions[args[1]]

    def _check_call(self, args):
        self._maybe_raise(args)
        if args[0] == 'flatpak':
            self.calls.append(args)
        else:
            check_call(args)

    def _check_output(self, args, encoding=None):
        assert encoding == "UTF-8"
        assert args == [
            "flatpak", "remotes", "--system", "--show-disabled", "--columns=name,filter,options"
        ]
        self._maybe_raise(args)
        output = ""
        for name, (filter, disabled) in self.flatpak_remotes.items():
            if disabled:
                output += f"{name}\t{filter}\tdisabled"
            else:
                # No trailing \t - https://github.com/flatpak/flatpak/pull/2189
                output += f"{name}\t{filter}"
        return output

    def set_flatpak_remotes(self, flatpak_remotes: Dict[str, Tuple[str, bool]]):
        self.flatpak_remotes = flatpak_remotes
        get_flatpak_remotes.cache_clear()

    def reload_config(self):
        self.cfg = Config(root=self.root)

    def assert_dnf_repo_status(self, *, enabled, repofile="rpmfusion-nonfree-nvidia-driver.repo"):
        yumreposdir = self.root / "etc/yum.repos.d"
        contents = (yumreposdir / repofile).read_text()
        if enabled:
            assert "enabled=1" in contents
        else:
            assert "enabled=0" in contents

    def run(self):
        self.root.mkdir()

        yumreposdir = self.root / "etc/yum.repos.d"
        yumreposdir.mkdir(parents=True)
        with open(yumreposdir / "rpmfusion-nonfree-nvidia-driver.repo", "w") as f:
            f.write(dedent("""\
                [rpmfusion-nonfree-nvidia-driver]
                name=RPM Fusion for Fedora $releasever - Nonfree - NVIDIA Driver
                #baseurl=http://download1.rpmfusion.org/nonfree/fedora/nvidia-driver/$releasever/$basearch/
                metalink=https://mirrors.rpmfusion.org/metalink?repo=nonfree-fedora-nvidia-driver-$releasever&arch=$basearch
                enabled=0
                enabled_metadata=1
                type=rpm-md
                gpgcheck=1
                repo_gpgcheck=0
                gpgkey=file:///usr/share/distribution-gpg-keys/rpmfusion/RPM-GPG-KEY-rpmfusion-nonfree-fedora-$releasever
                skip_if_unavailable=True
            """))

        libconfdir = self.root / "usr/lib/fedora-third-party/conf.d"
        libconfdir.mkdir(parents=True)

        with open(libconfdir / "rpmfusion-nonfree-nvidia-driver.conf", "w") as f:
            f.write(dedent("""\
                [rpmfusion-nonfree-nvidia-driver]
                type=dnf
            """))

        with open(libconfdir / "flathub.conf", "w") as f:
            f.write(dedent("""\
                [flathub]
                type=flatpak
                flatpakrepo=flathub.flatpakrepo
                keep_unfiltered=yes
            """))

        with open(libconfdir / "flathub.flatpakrepo", "w") as f:
            f.write(dedent("""\
                [Flatpak Repo]
                Title=Fedora Flathub Selection
                Url=https://dl.flathub.org/repo/
                Homepage=https://flathub.org/
                Comment=Selected applications from Flathub
                Description=Selected applications from Flathub (https://flathub.org)
                Icon=https://dl.flathub.org/repo/logo.svg
                Filter=/etc/fedora-flathub.filter
            """))

        statedir = self.root / "var/lib/fedora-third-party"
        statedir.mkdir(parents=True)

        self.reload_config()
        with mock.patch("os.geteuid", return_value=0), \
             mock.patch("subprocess.check_call", side_effect=self._check_call), \
             mock.patch("subprocess.check_output", side_effect=self._check_output):
            yield self


@pytest.fixture
def setup(tmpdir):
    result = TestSetup(tmpdir)
    yield from result.run()
