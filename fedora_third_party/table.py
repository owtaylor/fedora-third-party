import csv
from dataclasses import dataclass
import sys
from typing import Collection, Dict, List, Optional


@dataclass
class Column:
    id: str
    title: str
    attr: str

    def val(self, obj):
        return str(getattr(obj, self.attr))


class TableConfigError(Exception):
    pass


def pad(str, width):
    return str + " " * (width - len(str))


class Table:
    def __init__(self):
        self.columns: Dict[str, Column] = {}

    def add_column(self, id: str, title: str, attr: str):
        self.columns[id] = Column(id=id, title=title, attr=attr)

    def _dump_pretty(self, objects, cols: Collection[Column]):
        widths = [len(column.title) for column in cols]

        for obj in objects:
            for i, column in enumerate(cols):
                val = column.val(obj)
                widths[i] = max(widths[i], len(val))

        for i, column in enumerate(cols):
            if i != 0:
                print(" ", end="")
            print(column.title if i == len(cols) - 1 else pad(column.title, widths[i]), end="")
        print()

        for i, column in enumerate(cols):
            if i != 0:
                print(" ", end="")
            print("-" * widths[i], end="")
        print()

        for obj in objects:
            for i, column in enumerate(cols):
                if i != 0:
                    print(" ", end="")
                val = column.val(obj)
                print(val if i == len(cols) - 1 else pad(val, widths[i]), end="")
            print()

    def _dump_csv(self, objects, cols: Collection[Column]):
        writer = csv.writer(sys.stdout, lineterminator='\n')
        for obj in objects:
            writer.writerow(column.val(obj) for column in cols)

    def dump(
        self, objects, *, csv: bool = False, columns: Optional[List[str]] = None
    ):
        if columns is None:
            cols = self.columns.values()
        else:
            cols: Collection[Column] = []
            for id in columns:
                try:
                    cols.append(self.columns[id])
                except KeyError:
                    raise TableConfigError(f"Unknown column '{id}'")

        if csv:
            self._dump_csv(objects, cols)
        else:
            self._dump_pretty(objects, cols)
