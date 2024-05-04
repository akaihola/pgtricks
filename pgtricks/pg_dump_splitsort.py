#!/usr/bin/env python

from __future__ import annotations

import io
import os
import re
from argparse import ArgumentParser
from typing import IO, Iterable, Match, Pattern

from pgtricks.mergesort import MergeSort
from pgtricks._tsv_sort import sort_file_lines

COPY_RE = re.compile(r"COPY\s+\S+\s+(\(.*?\)\s+)?FROM\s+stdin;\n$")
KIBIBYTE, MEBIBYTE, GIBIBYTE = 2**10, 2**20, 2**30
MEMORY_UNITS = {"": 1, "k": KIBIBYTE, "m": MEBIBYTE, "g": GIBIBYTE}


def linecomp(l1: str, l2: str) -> int:
    p1 = 0
    p2 = 0
    prev_p1 = None
    prev_p2 = None
    while True:
        if p1 == prev_p1 and p2 == prev_p2:
            raise RuntimeError("Infinite loop in linecomp")
        prev_p1 = p1
        prev_p2 = p2
        if p1 >= len(l1):
            return 0 if p2 >= len(l2) else -1
        if p2 >= len(l2):
            return 1
        l1_larger = 1
        if l1[p1] == "-":
            if l2[p2] != "-":
                # l1 is negative, l2 is positive, so l1 < l2
                return -1
            # both are negative, skip the minus sign, remember to reverse the result
            p1 += 1
            p2 += 1
            l1_larger = -1
        elif l2[p2] == "-":
            # l2 is negative, l1 is positive, so l1 > l2
            return 1
        while p1 < len(l1) and l1[p1] == "0":
            # skip leading zeros in l1
            p1 += 1
        while p2 < len(l2) and l2[p2] == "0":
            # skip leading zeros in l2
            p2 += 1
        d1 = p1
        for d1 in range(p1, len(l1)):
            # find the next non-digit character in l1
            if l1[d1] not in '0123456789':
                break
        d2 = p2
        for d2 in range(p2, len(l2)):
            # find the next non-digit character in l2
            if l2[d2] not in '0123456789':
                break
        if d1 - p1 > d2 - p2:
            # l1 has more integer digits than l2, so |l1| > |l2|
            return l1_larger
        if d1 - p1 < d2 - p2:
            # l1 has fewer integer digits than l2, so |l1| < |l2|
            return -l1_larger
        if l1[p1:d1] > l2[p2:d2]:
            # l1 has the same number of integer digits as l2, but |l1| > |l2|
            return l1_larger
        if l1[p1:d1] < l2[p2:d2]:
            # l1 has the same number of integer digits as l2, but |l1| < |l2|
            return -l1_larger
        if d1 >= len(l1):
            return 0 if d2 >= len(l2) else -l1_larger
        if d2 >= len(l2):
            return l1_larger
        if l1[d1] > l2[d2]:
            # a different non-digit character follows identical digits in l1 and l2
            # and it sorts l1 after l2
            return l1_larger
        if l1[d1] < l2[d2]:
            # a different non-digit character follows identical digits in l1 and l2
            # and it sorts l1 before l2
            return -l1_larger
        if l1[d1] != ".":
            # the non-digit characters are not a decimal point, continue comparison
            # after it
            p1 = d1 + 1
            p2 = d2 + 1
            continue
        # l1 and l2 have the same integer part, compare the fractional part
        p1 = d1 + 1
        p2 = d2 + 1
        next_field = False
        while not next_field and p1 < len(l1) and p2 < len(l2):
            if l1[p1] == "\t":
                if l2[p2] == "\t":
                    # l1 and l2 have the same fractional part, they are equal
                    p1 += 1
                    p2 += 1
                    next_field = True
                    continue
                # l1 has fewer fractional digits than l2, so |l1| < |l2|
                return -l1_larger
            if l2[p2] == "\t":
                # l1 has more fractional digits than l2, so |l1| > |l2|
                return l1_larger
            if l1[p1] > l2[p2]:
                # fractional part of l1 is greater than that of l2, so |l1| > |l2|
                return l1_larger
            if l1[p1] < l2[p2]:
                # fractional part of l1 is less than that of l2, so |l1| < |l2|
                return -l1_larger
            # l1 and l2 have the same fractional part up to here, continue comparison
            p1 += 1
            p2 += 1


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

    position = 0
    with open(sql_filepath) as sql_file:
        while True:
            line = sql_file.readline()
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
                        sorted_data_lines = MergeSort(max_memory=max_memory)
                    elif SEQUENCE_SET_RE.match(line):
                        pass
                    elif 1 <= counter < 9999:
                        counter = 9999
                        output = new_output('%04d_epilogue.sql' % counter)
                    writelines([line])
            else:
                if line != "\\.\n":
                    output.close()
                    new_position = sort_file_lines(sql_filepath, output.name, position, r"\.")
                    print(f"sort_file_lines({sql_filepath!r}, {output.name!r}, {position}, r\"\\.\") == {new_position}")
                    sql_file.seek(new_position)
                    output = open(output.name, "a")
                sorted_data_lines = None
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
