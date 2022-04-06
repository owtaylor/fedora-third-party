from __future__ import annotations

from abc import ABC, abstractmethod
from configparser import ConfigParser
from dataclasses import dataclass
import functools
import logging
import os
import subprocess
from typing import List, Optional, TYPE_CHECKING

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib  # noqa: E402


if TYPE_CHECKING:
    from .config import Config


logger = logging.getLogger(__name__)


class ModificationFailedError(Exception):
    """Couldn't modify the repository for some (retryable) error"""
    pass


class Repository(ABC):
    def __init__(self, cfg: Config, name: str):
        self.cfg = cfg
        self.name = name

    @abstractmethod
    def enable(self):
        pass

    @abstractmethod
    def disable(self):
        pass

    def is_hidden(self):
        return False

    def is_seen(self):
        return self.cfg.is_repository_seen(self)


class DnfRepository(Repository):
    type = 'dnf'

    def __init__(self, cfg: Config, name: str, parser: ConfigParser):
        super().__init__(cfg, name)

    def enable(self):
        self.cfg.dnf_config_editor.set_enabled(self.name, True)

    def disable(self):
        self.cfg.dnf_config_editor.set_enabled(self.name, False)


@dataclass
class FlatpakRemote:
    name: str
    filter: Optional[str]
    disabled: bool


@functools.cache
def get_flatpak_remotes():
    try:
        output = subprocess.check_output([
            "flatpak", "remotes", "--system", "--show-disabled", "--columns=name,filter,options"
        ], encoding="UTF-8")
    except subprocess.CalledProcessError as e:
        logger.warning(
            "Command '%s' failed, exit status=%s", " ".join(e.cmd), e.returncode
        )
        return None
    except FileNotFoundError:
        logger.warning("Cannot list Flatpak remotes: flatpak command not found")
        return None

    result: List[FlatpakRemote] = []
    for line in output.split("\n"):
        if line == "":
            continue
        columns = line.split("\t")
        name = columns[0]
        filter = columns[1] if columns[1] != "-" else None
        options = columns[2] if len(columns) > 2 else ""
        result.append(FlatpakRemote(name=name, filter=filter, disabled="disabled" in options))

    return result


class FlatpakRepository(Repository):
    type = 'flatpak'

    def __init__(self, cfg: Config, name: str, parser: ConfigParser):
        super().__init__(cfg, name)
        self.flatpakrepo = parser.get(name, "flatpakrepo")
        self.keep_unfiltered = parser.getboolean(name, "keep_unfiltered", fallback=False)
        if not os.path.isabs(self.flatpakrepo):
            self.flatpakrepo = str(self.cfg.libconfdir / self.flatpakrepo)

    def get_existing_remote(self, allow_broken_installation=False):
        remotes = get_flatpak_remotes()
        if remotes is None:
            if allow_broken_installation:
                return None
            else:
                raise ModificationFailedError()
        else:
            return next((r for r in remotes if r.name == self.name), None)

    def is_hidden(self):
        if self.keep_unfiltered:
            remote = self.get_existing_remote(allow_broken_installation=True)
            if remote and remote.filter is None:
                return True

        return False

    def is_seen(self):
        # Before version 0.9, we didn't add repositories if they were disabled; to
        # fix up old systems on "fedora-third-party refresh", we treat "never added"
        # as "never seen."
        if not self.cfg.is_repository_added(self):
            return False

        return super().is_seen()

    def run_flatpak(self, args):
        command = ["flatpak"]
        command += args

        logger.info("Calling '%s'", " ".join(command))
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as e:
            logger.warning("Command '%s' failed, exit status=%s", " ".join(e.cmd), e.returncode)
            raise ModificationFailedError()

    def get_flatpakrepo_param(self, key):
        key_file = GLib.KeyFile.new()
        key_file.load_from_file(self.flatpakrepo, GLib.KeyFileFlags.NONE)

        try:
            return key_file.get_locale_string('Flatpak Repo', key)
        except GLib.Error as e:
            assert (e.matches(GLib.key_file_error_quark(), GLib.KeyFileError.GROUP_NOT_FOUND) or
                    e.matches(GLib.key_file_error_quark(), GLib.KeyFileError.KEY_NOT_FOUND))
            return None

    def add_repo(self, disabled):
        # Avoid fighting the user - if they removed a repository we added, let that standx
        if self.cfg.is_repository_added(self):
            return

        args = ['remote-add', '--from', self.name, self.flatpakrepo]

        # Priority is:
        #  - title, etc. from command line
        #  - title, etc. from downloaded remote metadata
        #  - title, etc. from flatpakrepo file
        #
        # But we want to be able to override the parameters from the remote, so we force the
        # title, etc. from the flatpakrepo file into the command line
        for key in ('Title', 'Comment', 'Description'):
            value = self.get_flatpakrepo_param(key)
            if value:
                option = '--' + key.lower()
                args += [option, value]

        if disabled:
            args += ['--disable']
        self.run_flatpak(args)
        self.cfg.set_repository_added(self, True)

    def enable(self):
        remote = self.get_existing_remote()
        if not remote:
            self.add_repo(disabled=False)
            return

        # Only modify repositories we added ourself
        if not self.cfg.is_repository_added(self):
            return

        if remote.disabled:
            self.run_flatpak(['remote-modify', self.name, '--enable'])

    def disable(self):
        remote = self.get_existing_remote()
        if remote is None:
            self.add_repo(disabled=True)
            return

        # Only modify repositories we added ourself
        if not self.cfg.is_repository_added(self):
            return

        # For "keep_unfiltered" repositories, if the filter was removed
        # (typically, user installs the repository themself, removing the filter)
        # then we don't remove them on disable
        if self.keep_unfiltered:
            if remote.filter is None:
                return

        if not remote.disabled:
            self.run_flatpak(['remote-modify', self.name, '--disable'])
