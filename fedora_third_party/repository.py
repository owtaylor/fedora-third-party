from __future__ import annotations

from abc import ABC, abstractmethod
from configparser import ConfigParser
from dataclasses import dataclass
import functools
import logging
import os
import subprocess
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config


logger = logging.getLogger(__name__)


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

    def is_seen(self):
        return self.cfg.is_repository_seen(self)


class DnfRepository(Repository):
    def __init__(self, cfg: Config, name: str, parser: ConfigParser):
        super().__init__(cfg, name)
        self.repository = parser.get(name, 'repository')

    def run_dnf(self, args):
        command = ['dnf']
        command += args

        logger.info("Calling %s", " ".join(command))
        subprocess.check_call(command)

    def enable(self):
        self.run_dnf(['config-manager', '--set-enabled', self.repository])

    def disable(self):
        self.run_dnf(['config-manager', '--set-disabled', self.repository])


@dataclass
class FlatpakRemote:
    name: str
    filter: Optional[str]


@functools.cache
def get_flatpak_remotes():
    output = subprocess.check_output([
        "flatpak", "remotes", "--system", "--columns=name,filter"
    ], encoding="UTF-8")

    result: List[FlatpakRemote] = []
    for line in output.split("\n"):
        line = line.strip()
        if line == "":
            continue
        name, filter = line.split()
        if filter == "-":
            filter = None
        result.append(FlatpakRemote(name=name, filter=filter))

    return result


class FlatpakRepository(Repository):
    def __init__(self, cfg: Config, name: str, parser: ConfigParser):
        super().__init__(cfg, name)
        self.remote = parser.get(name, "remote")
        self.flatpakrepo = parser.get(name, "flatpakrepo")
        self.keep_unfiltered = parser.getboolean(name, "keep_unfiltered", fallback=False)
        if not os.path.isabs(self.flatpakrepo):
            self.flatpakrepo = str(self.cfg.libconfdir / self.flatpakrepo)

    def run_flatpak(self, args):
        command = ["flatpak"]
        command += args

        logger.info("Calling %s", " ".join(command))
        subprocess.check_call(command)

    def enable(self):
        remotes = get_flatpak_remotes()
        if not any(self.name == remote.name for remote in remotes):
            self.run_flatpak(['remote-add', '--from', self.remote, self.flatpakrepo])
            self.cfg.set_repository_added(self, True)

    def disable(self):
        # Only remove repositories we added ourself
        if not self.cfg.is_repository_added(self):
            return

        remote = next((r for r in get_flatpak_remotes() if r.name == self.name), None)
        if remote is None:
            return

        # For "keep_unfiltered" repositories, if the filter was removed
        # (typically, user installs the repository themself, removing the filter)
        # then we don't remove them on disable
        if self.keep_unfiltered:
            if remote.filter is None:
                return

        self.run_flatpak(['remote-delete', self.remote])
        self.cfg.set_repository_added(self, False)
