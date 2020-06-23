#!/usr/bin/env python3

"""Split the output of ``pg_dump -s`` into a directory of SQL scripts

Each script is named after the object whose SQL statements it contains.

The ``search_path`` setting is initialized in each script according to the
value which was active in the original dump at that point.

Usage::

    pg_dump -s -f my_schema_dump.sql my_database_name
    pg_split_schema_dump my_schema_dump.sql /my/dump/directory

"""

import os
import re
import sys

SPLIT_RE = re.compile(
    r'''

--
-- '''
)


IDENTIFY_RE = re.compile(
    r'''

--
-- Name: ([^\n;]+?)(?:\([^)]*\))?; Type: ([^\n;]+); Schema: ([^\n;]+?); Owner:[^\n]*
--

''',
    re.DOTALL | re.MULTILINE,
)

SEARCH_PATH_RE = re.compile(r'SET search_path = [^\n;]+;')


def split_sql_file(sqlpath, target_directory):
    if not os.path.isdir(target_directory):
        os.mkdir(target_directory)

    sql = open(sqlpath).read()

    search_path = "SET search_path = public;"

    parts = [match.start() for match in SPLIT_RE.finditer(sql)] + [len(sql)]
    for start, end in zip(parts[:-1], parts[1:]):
        part = sql[start:end]
        match = IDENTIFY_RE.match(part)
        if not match:
            print(part)
            sys.exit(0)
        name = match.group(1).replace(" ", "_")
        type_ = match.group(2).replace(" ", "_")
        schema = match.group(3)
        if schema == "-":
            schema = "no_schema"
        if name == "id":
            continue
        dump_filename = "{}.{}.{}".format(schema, name, type_)
        dump_filepath = os.path.join(target_directory, dump_filename)
        open(dump_filepath, "w").write("{}\n\n{}".format(search_path, part))
        search_path_match = SEARCH_PATH_RE.search(part)
        if search_path_match:
            search_path = search_path_match.group()


def main(args=None):
    sqlpath, target_directory = sys.argv[1:] if args is None else args
    split_sql_file(sqlpath, target_directory)


if __name__ == "__main__":
    main()
