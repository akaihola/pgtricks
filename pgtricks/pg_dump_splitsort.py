#!/usr/bin/env python

from __future__ import annotations

import io
import os
import re
from argparse import ArgumentParser
from typing import IO, Iterable, Match, Pattern

from pgtricks._tsv_sort import sort_file_lines

COPY_RE = re.compile(r"COPY\s+\S+\s+(\(.*?\)\s+)?FROM\s+stdin;\n$")
KIBIBYTE, MEBIBYTE, GIBIBYTE = 2**10, 2**20, 2**30
MEMORY_UNITS = {"": 1, "k": KIBIBYTE, "m": MEBIBYTE, "g": GIBIBYTE}
DATA_COMMENT_RE = re.compile('-- Data for Name: (?P<table>.*?); '
                             'Type: TABLE DATA; '
                             'Schema: (?P<schema>.*?);')
SEQUENCE_SET_RE = re.compile(r'-- Name: .+; Type: SEQUENCE SET; Schema: |'
                             r"SELECT pg_catalog\.setval\('")

class Matcher(object):
    def __init__(self) -> None:
        self._match: Match[str] | None = None

    def match(self, pattern: Pattern[str], data: str) -> Match[str] | None:
        """Match the regular expression pattern against the data."""
        self._match = pattern.match(data)
        return self._match

    def group(self, group1: str) -> str:
        if not self._match:
            raise ValueError('Pattern did not match')
        return self._match.group(group1)


def split_sql_file(  # noqa: C901  too complex
    sql_filepath: str,
    max_memory: int = 100 * MEBIBYTE,
) -> None:
    """Split a SQL file so that each COPY statement is in its own file."""
    directory = os.path.dirname(sql_filepath)

    # `output` needs to be instantiated before the inner functions are defined.
    # Assign it a dummy string I/O object so type checking is happy.
    # This will be replaced with the prologue SQL file object.
    output: IO[str] = io.StringIO()
    buf: list[str] = []

    def flush() -> None:
        output.writelines(buf)
        buf[:] = []

    def writelines(lines: Iterable[str]) -> None:
        if buf:
            flush()
        output.writelines(lines)

    def new_output(filename: str) -> IO[str]:
        if output:
            output.close()
        return open(os.path.join(directory, filename), 'w')

    inside_sql_copy: bool = False
    counter = 0
    output = new_output('0000_prologue.sql')
    matcher = Matcher()

    position = 0
    with open(sql_filepath) as sql_file:
        while True:
            line = sql_file.readline()
            if not line:
                break
            if not inside_sql_copy:
                if line in ('\n', '--\n'):
                    buf.append(line)
                elif line.startswith('SET search_path = '):
                    writelines([line])
                else:
                    if matcher.match(DATA_COMMENT_RE, line):
                        counter += 1
                        output = new_output(
                            '{counter:04}_{schema}.{table}.sql'.format(
                                counter=counter,
                                schema=matcher.group('schema'),
                                table=matcher.group('table')))
                    elif COPY_RE.match(line):
                        inside_sql_copy = True
                    elif SEQUENCE_SET_RE.match(line):
                        pass
                    elif 1 <= counter < 9999:
                        counter = 9999
                        output = new_output('%04d_epilogue.sql' % counter)
                    writelines([line])
            else:
                if line != "\\.\n":  # don't bother with empty COPY statements
                    output.close()
                    position_after_sql_copy = sort_file_lines(sql_filepath, output.name, position)
                    # print(f"sort_file_lines({sql_filepath!r}, {output.name!r}, {position}) == {new_position}")
                    sql_file.seek(position_after_sql_copy)
                    output = open(output.name, "a")
                inside_sql_copy = False
            position = sql_file.tell()
    flush()


def memory_size(size: str) -> int:
    """Parse a human-readable memory size.

    :param size: The memory size to parse, e.g. "100MB".
    :return: The memory size in bytes.
    :raise ValueError: If the memory size is invalid.

    """
    match = re.match(r"([\d._]+)\s*([kmg]?)b?", size.lower().strip())
    if not match:
        message = f"Invalid memory size: {size}"
        raise ValueError(message)
    return int(float(match.group(1)) * MEMORY_UNITS[match.group(2)])


def main() -> None:
    parser = ArgumentParser(description="Split a SQL file into smaller files.")
    parser.add_argument("sql_filepath", help="The SQL file to split.")
    parser.add_argument(
        "-m",
        "--max-memory",
        default=100 * MEBIBYTE,
        type=memory_size,
        help="Max memory to use, e.g. 50_000, 200000000, 100kb, 100MB (default), 2Gig.",
    )
    args = parser.parse_args()

    split_sql_file(args.sql_filepath, args.max_memory)


if __name__ == '__main__':
    main()
