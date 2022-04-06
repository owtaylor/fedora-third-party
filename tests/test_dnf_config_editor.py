import os
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

from fedora_third_party.dnf_config_editor import DnfConfigEditor


@pytest.fixture
def reposdir(tmpdir):
    yield Path(tmpdir / "etc/yum.repos.d")


@pytest.fixture
def editor(tmpdir, reposdir):
    editor = DnfConfigEditor(root=str(tmpdir))
    os.makedirs(reposdir, exist_ok=True)
    yield editor


def test_basic(editor: DnfConfigEditor, reposdir: Path):
    repofile = reposdir / "fedora.repo"

    repofile.write_text(dedent("""\
        [fedora]
        name=Fedora $releasever - $basearch
        metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-$releasever&arch=$basearch
        enabled=1
        gpgcheck=1
        gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-$basearch
    """))

    editor.set_enabled("fedora", False)
    editor.save()

    assert repofile.read_text() == dedent("""\
        [fedora]
        name=Fedora $releasever - $basearch
        metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-$releasever&arch=$basearch
        enabled=0
        gpgcheck=1
        gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-$basearch
    """)


def test_section_encoding(editor: DnfConfigEditor, reposdir: Path):
    repofile = reposdir / "foo.repo"
    repofile.write_bytes(b"""\
\xef\xbb\xbf [section1]   # bom is allowed at start of file
enabled=0

[\xffsection2]   # invalid UTF-8 names are skipped
enabled=0

[\xc3\x87a va?]  # section with non-ascii name
enabled=0
""")

    editor.set_enabled("section1", True)
    editor.set_enabled("\u00c7a va?", True)
    editor.save()

    assert repofile.read_bytes() == b"""\
\xef\xbb\xbf [section1]   # bom is allowed at start of file
enabled=1

[\xffsection2]   # invalid UTF-8 names are skipped
enabled=0

[\xc3\x87a va?]  # section with non-ascii name
enabled=1
"""


def test_editor_error_handling(editor: DnfConfigEditor, reposdir: Path, caplog):
    repofile = reposdir / "foo.repo"

    repofile.write_text(dedent("""\
        [fedora]
        enabled=1

        [skeleton]
        name=Skeleton
    """))

    caplog.clear()
    editor.set_enabled("missing", True)
    assert "DNF repository [missing] not found" in caplog.text

    caplog.clear()
    editor.set_enabled("skeleton", True)
    assert "DNF repository [skeleton] has no enabled= key." in caplog.text


def test_editor_cleanup(editor: DnfConfigEditor, reposdir: Path):
    repofile = reposdir / "fedora.repo"

    repofile.write_text(dedent("""\
        [fedora]
        enabled=1
    """))

    editor.set_enabled("fedora", False)
    with patch("os.rename", side_effect=RuntimeError("MyFailure")):
        with pytest.raises(RuntimeError, match=r"MyFailure"):
            editor.save()
        assert os.listdir(reposdir) == ["fedora.repo"]
