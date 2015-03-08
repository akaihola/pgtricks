#!/usr/bin/env python

import sys
import re


COPY_RE = re.compile(r'COPY .*? \(.*?\) FROM stdin;\n$')


def try_float(s):
    if not s or s[0] not in '0123456789.-':
        # optimization
        return s
    try:
        return float(s)
    except ValueError:
        return s


def linecomp(l1, l2):
    p1 = l1.split('\t', 1)
    p2 = l2.split('\t', 1)
    result = cmp(try_float(p1[0]), try_float(p2[0]))
    if not result and len(p1) == len(p2) == 2:
        return linecomp(p1[1], p2[1])
    return result

DATA_COMMENT_RE = re.compile('-- Data for Name: (?P<table>.*?); '
                             'Type: TABLE DATA; '
                             'Schema: (?P<schema>.*?);')
SEQUENCE_SET_RE = re.compile(r'-- Name: .+; Type: SEQUENCE SET; Schema: |'
                             r"SELECT pg_catalog\.setval\('")

class Matcher(object):
    def __init__(self):
        self._match = None

    def match(self, pattern, data):
        self._match = pattern.match(data)
        return self._match

    def __getattr__(self, attname):
        if not self._match:
            raise ValueError('Pattern did not match')
        return getattr(self._match, attname)


def split_sql_file(sql_filepath):

    output = None
    buf = []

    def flush():
        output.writelines(buf)
        buf[:] = []

    def new_output(path):
        if output:
            output.close()
        return file(path, 'w')

    copy_lines = None
    counter = 0
    output = new_output('0000_prologue.sql')
    matcher = Matcher()

    for line in file(sql_filepath):
        if copy_lines is None:
            if line in ('\n', '--\n'):
                buf.append(line)
            elif line.startswith('SET search_path = '):
                flush()
                buf.append(line)
            else:
                if matcher.match(DATA_COMMENT_RE, line):
                    counter += 1
                    output = new_output(
                        '{counter:04}_{schema}.{table}.sql'.format(
                            counter=counter,
                            schema=matcher.group('schema'),
                            table=matcher.group('table')))
                elif COPY_RE.match(line):
                    copy_lines = []
                elif SEQUENCE_SET_RE.match(line):
                    pass
                elif 1 <= counter < 9999:
                    counter = 9999
                    output = new_output('%04d_epilogue.sql' % counter)
                buf.append(line)
                flush()
        else:
            if line == '\\.\n':
                copy_lines.sort(cmp=linecomp)
                buf.extend(copy_lines)
                buf.append(line)
                flush()
                copy_lines = None
            else:
                copy_lines.append(line)


if __name__ == '__main__':
    split_sql_file(sys.argv[1])
