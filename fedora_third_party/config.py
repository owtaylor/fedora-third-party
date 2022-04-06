from configparser import ConfigParser
from functools import cached_property
from pathlib import Path
from typing import Collection, Optional

from .dnf_config_editor import DnfConfigEditor
from .repository import DnfRepository, FlatpakRepository, Repository


class Config:
    def __init__(self, root='/'):
        self.root = Path(root)
        self.libconfdir = self.root / "usr/lib/fedora-third-party/conf.d"
        self.state_path = self.root / "var/lib/fedora-third-party/state"

        self.state_parser = ConfigParser(interpolation=None, comment_prefixes="#")
        self.state_parser.add_section("main")
        self.state_parser.read(self.state_path)

        section_parser = ConfigParser(interpolation=None, comment_prefixes="#")
        for p in self.libconfdir.iterdir():
            if p.suffix == ".conf":
                section_parser.read(p)

        self.repositories = []
        for section_name in section_parser.sections():
            if section_name != 'main':
                section = section_parser[section_name]
                repo_type = section.get('type')
                if repo_type == 'dnf':
                    self.repositories.append(DnfRepository(self, section_name, section_parser))
                elif repo_type == 'flatpak':
                    self.repositories.append(FlatpakRepository(self, section_name, section_parser))

    def is_enabled(self):
        return self.state_parser.getboolean('main', 'enabled', fallback=False)

    def is_enabled_set(self):
        return self.state_parser.getboolean('main', 'enabled', fallback=None) is not None

    def is_repository_seen(self, repository: Repository):
        return self.state_parser.getboolean(repository.name, 'seen', fallback=False)

    def _write_state(self):
        with open(self.state_path, 'w') as f:
            self.state_parser.write(f)

    def update_seen_repositories(self, retry_repositories: Optional[Collection] = None):
        for repository in sorted(self.repositories, key=lambda r: r.name):
            if retry_repositories is not None and repository in retry_repositories:
                continue

            if not self.state_parser.has_section(repository.name):
                self.state_parser.add_section(repository.name)
            self.state_parser.set(repository.name, 'seen', 'yes')

        self._write_state()

    def is_repository_added(self, repository: Repository):
        return self.state_parser.getboolean(repository.name, 'added', fallback=False)

    def set_repository_added(self, repository: Repository, added: bool):
        if not self.state_parser.has_section(repository.name):
            self.state_parser.add_section(repository.name)
        self.state_parser.set(repository.name, 'added', 'yes' if added else 'no')
        self._write_state()

    def enable(self):
        self.state_parser.set('main', 'enabled', 'yes')
        self._write_state()

    def disable(self):
        self.state_parser.set('main', 'enabled', 'no')
        self._write_state()

    def list_repositories(self):
        return self.repositories

    @cached_property
    def dnf_config_editor(self):
        return DnfConfigEditor(root=str(self.root))
