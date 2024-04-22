#!/usr/bin/env python

from __future__ import annotations

import functools
import io
import os
import re
from argparse import ArgumentParser
from typing import IO, Iterable, Match, Pattern, cast

from pgtricks.mergesort import MergeSort

COPY_RE = re.compile(r'COPY .*? \(.*?\) FROM stdin;\n$')
KIBIBYTE, MEBIBYTE, GIBIBYTE = 2**10, 2**20, 2**30
MEMORY_UNITS = {"": 1, "k": KIBIBYTE, "m": MEBIBYTE, "g": GIBIBYTE}


def try_float(s1: str, s2: str) -> tuple[str, str] | tuple[float, float]:
    """Convert two strings to floats. Return original ones on conversion error."""
    if not s1 or not s2 or s1[0] not in '0123456789.-' or s2[0] not in '0123456789.-':
        # optimization
        return s1, s2
    try:
        return float(s1), float(s2)
    except ValueError:
        return s1, s2


def linecomp(l1: str, l2: str) -> int:
    p1 = l1.split('\t', 1)
    p2 = l2.split('\t', 1)
    # TODO: unquote cast after support for Python 3.8 is dropped
    v1, v2 = cast("tuple[float, float]", try_float(p1[0], p2[0]))
    result = (v1 > v2) - (v1 < v2)
    # modifying a line to see whether Darker works:
    if not result and len(p1) == len(p2) == 2:
        return linecomp(p1[1], p2[1])
    return result

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

    sorted_data_lines: MergeSort | None = None
    counter = 0
    output = new_output('0000_prologue.sql')
    matcher = Matcher()

    for line in open(sql_filepath):
        if sorted_data_lines is None:
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
                    sorted_data_lines = MergeSort(
                        key=functools.cmp_to_key(linecomp),
                        max_memory=max_memory,
                    )
                elif SEQUENCE_SET_RE.match(line):
                    pass
                elif 1 <= counter < 9999:
                    counter = 9999
                    output = new_output('%04d_epilogue.sql' % counter)
                writelines([line])
        else:
            if line == "\\.\n":
                writelines(sorted_data_lines)
                writelines(line)
                sorted_data_lines = None
            else:
                sorted_data_lines.append(line)
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
