import logging
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Optional, Set, Tuple


SECTION_ITER_RE = re.compile(rb"^(?:\xef\xbb\xbf)?[ \t]*\[([^]]+)\].*$\n?", re.MULTILINE)
ENABLED_RE = re.compile(rb"^[ \t]*enabled[ \t]*=[ \t]*(\d+)", re.MULTILINE)


logger = logging.getLogger(__name__)


class DnfConfigEditor:
    # Simple editor to change enabled keys in /etc/yum.repos.d/*.conf
    #
    # We can't use 'dnf config-manager' because rpm-ostree systems consume the
    # the repositories directory without having DNF at all.
    #
    # This doesn't use ConfigParser to avoid running into differences between
    # that and the DNF repository parsing code, and to make sure that we
    # preserve comments and formatting exactly.

    def __init__(self, root: str = "/"):
        self.root = Path(root)

        self.loaded = False

        # Map from path to file contents
        self.files: Dict[Path, bytes] = {}
        # Map from section name to the file and byte range
        self.repos: Dict[str, Tuple[Path, int, int]] = {}
        # Which files have been edited
        self.edited: Set[Path] = set()

    def _add_repo(self, namebytes, repopath, start, end):
        try:
            name = namebytes.decode("UTF-8")
        except UnicodeDecodeError:
            return

        self.repos[name] = (repopath, start, end)

    def _load_repo(self, repopath: Path):
        with open(repopath, 'rb') as f:
            contents = f.read()

        self.files[repopath] = contents

        # Identify the bounds of each section in the file
        last: Optional[re.Match] = None
        for m in SECTION_ITER_RE.finditer(contents):
            if last:
                self._add_repo(last.group(1), repopath, last.end(), m.start())
            last = m
        if last:
            self._add_repo(last.group(1), repopath, last.end(), len(contents))

    def _load(self):
        if self.loaded:
            return

        reposdir = self.root / "etc/yum.repos.d"
        for repopath in reposdir.iterdir():
            if repopath.suffix == ".repo":
                self._load_repo(repopath)

        self.loaded = True

    def set_enabled(self, repo: str, enabled: bool):
        self._load()

        try:
            repopath, start, end = self.repos[repo]
        except KeyError:
            logging.warning("DNF repository [%s] not found.", repo)
            return

        value = b"1" if enabled else b"0"
        contents = self.files[repopath]
        section = self.files[repopath][start:end]
        m = ENABLED_RE.search(section)
        if not m:
            logging.warning("DNF repository [%s] has no enabled= key.", repo)
            return

        if m.group(1) != value:
            new_section = section[0:m.start(1)] + value + section[m.end(1):]
            new_contents = contents[0:start] + new_section + contents[end:]
            self.files[repopath] = new_contents
            logging.info("Setting enabled=%s in %s [%s]", value, repopath, repo)
            self.edited.add(repopath)

    def save(self):
        for repopath in self.edited:
            with NamedTemporaryFile(
                prefix=repopath.name + ".", dir=repopath.parent, delete=False
            ) as temp:
                success = False
                try:
                    temp.write(self.files[repopath])
                    # propagate permissions to the new file
                    os.chmod(temp.name, repopath.stat().st_mode)
                    os.rename(temp.name, repopath)
                    success = True
                finally:
                    if not success:
                        os.unlink(temp.name)
