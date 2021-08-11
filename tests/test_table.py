from dataclasses import dataclass
from textwrap import dedent

import pytest

from fedora_third_party.table import Table, TableConfigError


def test_table(capsys):
    @dataclass
    class TestObj:
        foo42: str
        bar42: int

    table = Table()
    table.add_column('foo', 'Foo', 'foo42')
    table.add_column('bar', 'Bar', 'bar42')

    objs = [
        TestObj(foo42="a", bar42=12),
        TestObj(foo42="book", bar42=34),
    ]

    table.dump(objs)
    assert capsys.readouterr().out == dedent("""\
        Foo  Bar
        ---- ---
        a    12
        book 34
    """)

    table.dump(objs, csv=True)
    assert capsys.readouterr().out == dedent("""\
        a,12
        book,34
    """)

    table.dump(objs, columns=["bar"])
    assert capsys.readouterr().out == dedent("""\
        Bar
        ---
        12
        34
    """)


def test_table_config_error():
    table = Table()
    table.add_column("foo", "Foo", "foo42")
    with pytest.raises(TableConfigError, match=r"Unknown column 'bar'"):
        table.dump([], columns=["bar"])
