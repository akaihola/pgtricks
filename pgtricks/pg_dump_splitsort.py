#!/usr/bin/env python

from __future__ import annotations

import functools
import io
import os
import re
import sys
from typing import IO, Match, Pattern, cast

from pgtricks.mergesort import MergeSort

COPY_RE = re.compile(r'COPY .*? \(.*?\) FROM stdin;\n$')


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
    v1, v2 = cast(tuple[float, float], try_float(p1[0], p2[0]))
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


def split_sql_file(  # noqa: PLR0912, C901  many branches, too complex
    sql_filepath: str,
    max_memory: int = 10**8,
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

    def writeline(line_: str) -> None:
        if buf:
            flush()
        output.write(line_)

    def new_output(filename: str) -> IO[str]:
        if output:
            output.close()
        return open(os.path.join(directory, filename), 'w')

    copy_lines: MergeSort | None = None
    counter = 0
    output = new_output('0000_prologue.sql')
    matcher = Matcher()

    for line in open(sql_filepath):
        if copy_lines is None:
            if line in ('\n', '--\n'):
                buf.append(line)
            elif line.startswith('SET search_path = '):
                writeline(line)
            else:
                if matcher.match(DATA_COMMENT_RE, line):
                    counter += 1
                    output = new_output(
                        '{counter:04}_{schema}.{table}.sql'.format(
                            counter=counter,
                            schema=matcher.group('schema'),
                            table=matcher.group('table')))
                elif COPY_RE.match(line):
                    copy_lines = MergeSort(
                        key=functools.cmp_to_key(linecomp),
                        max_memory=max_memory,
                    )
                elif SEQUENCE_SET_RE.match(line):
                    pass
                elif 1 <= counter < 9999:
                    counter = 9999
                    output = new_output('%04d_epilogue.sql' % counter)
                writeline(line)
        else:
            if line == "\\.\n":
                for copy_line in copy_lines:
                    writeline(copy_line)
                writeline(line)
                copy_lines = None
            else:
                copy_lines.append(line)
    flush()


def main() -> None:
    split_sql_file(sys.argv[1])


if __name__ == '__main__':
    main()
