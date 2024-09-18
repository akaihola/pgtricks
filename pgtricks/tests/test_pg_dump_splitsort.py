from contextlib import nullcontext
from functools import cmp_to_key
from textwrap import dedent

import pytest

from pgtricks.pg_dump_splitsort import (
    COPY_RE,
    linecomp,
    memory_size,
    split_sql_file,
    try_float,
)


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        ("COPY table_name (column1, column2) FROM stdin;\n", True),
        ("COPY   table_name   (column1,   column2)   FROM   stdin;\n", True),
        ("COPY table_name FROM stdin;\n", True),
        ("COPY   table_name   FROM   stdin;\n", True),
        ("COPYtable_name FROM stdin;\n", False),  # No space after COPY
        ("COPY table_name FROMstdin;\n", False),  # No space before stdin
        ("COPY table_name FROM ;\n", False),  # Missing stdin
        ("COPY table_name stdin;\n", False),  # Missing FROM
        ("COPY FROM stdin;\n", False),  # Missing table name
    ],
)
def test_sql_copy_regular_expression(test_input, expected):
    """Test that `COPY_RE` matches/doesn't match the expected strings."""
    result = COPY_RE.match(test_input) is not None

    assert result == expected


@pytest.mark.parametrize(
    's1, s2, expect',
    [
        ("", "", ValueError),
        ("foo", "", ValueError),
        ("foo", "bar", ValueError),
        ("0", "1", (0.0, 1.0)),
        ("0", "one", ValueError),
        ("0.0", "0.0", (0.0, 0.0)),
        ("0.0", "one point zero", ValueError),
        ("0.", "1.", (0.0, 1.0)),
        ("0.", "one", ValueError),
        ("4.2", "0.42", (4.2, 0.42)),
        ("4.2", "four point two", ValueError),
        ("-.42", "-0.042", (-0.42, -0.042)),
        ("-.42", "minus something", ValueError),
        (r"\N", r"\N", ValueError),
        ("foo", r"\N", ValueError),
        ("-4.2", r"\N", ValueError),
    ],
)
def test_try_float(s1, s2, expect):
    with pytest.raises(expect) if expect is ValueError else nullcontext():

        result1, result2 = try_float(s1, s2)

        assert type(result1) is type(expect[0])
        assert type(result2) is type(expect[1])
        assert (result1, result2) == expect


@pytest.mark.parametrize(
    'l1, l2, expect',
    [
        ('', '', 0),
        ('a', 'b', -1),
        ('b', 'a', 1),
        ('0', '1', -1),
        ('1', '0', 1),
        ('0', '-1', 1),
        ('-1', '0', -1),
        ('0', '0', 0),
        ('-1', '-1', 0),
        ('0.42', '0.042', 1),
        ('4.2', '42.0', -1),
        ('-.42', '.42', -1),
        ('.42', '-.42', 1),
        ('"32.0"', '"4.20"', -1),
        ('foo\ta', 'bar\tb', 1),
        ('foo\tb', 'foo\ta', 1),
        ('foo\t0.42', 'foo\t4.2', -1),
        ('foo\tbar\t0.42424242424242\tbaz', 'foo\tbar\t0.42424242424242\tbaz', 0),
        ('foo', '0', 1),
        ('0', 'foo', -1),
        ('42', '', 1),
        ('', '42', -1),
        ('42', '42.0', 0),
        ('42', r'\N', -1),
        (r'\N', '42', 1),
        ('42', '42.0', 0),
        ('', r'\N', -1),
        (r'\N', '', 1),
        (r'\N', r'\N', 0),
    ],
)
def test_linecomp(l1, l2, expect):
    result = linecomp(l1, l2)
    assert result == expect


def test_linecomp_by_sorting():
    unsorted = [
        '\t'.join(line)
        for line in [
            [r'\N', r'\N', r'\N'],
            [r'\N', '', r'\N'],
            [r'\N', r'\N', ''],
            ['', r'\N', r'\N'],
            [r'\N', '-.52', 'baz'],
            [r'\N', '42', r'\N'],
            [r'\N', '.42', 'bar'],
            [r'\N', '-.4', 'foo'],
            [r'\N', 'foo', '.42'],
        ]
    ]
    sorted_lines = unsorted[:]
    sorted_lines.sort(key=cmp_to_key(linecomp))
    result = [s.split('\t') for s in sorted_lines]
    assert result == [
        ['', r'\N', r'\N'],
        [r'\N', '', r'\N'],
        [r'\N', '-.52', 'baz'],
        [r'\N', '-.4', 'foo'],
        [r'\N', '.42', 'bar'],
        [r'\N', '42', r'\N'],
        [r'\N', r'\N', ''],
        [r'\N', r'\N', r'\N'],
        [r'\N', 'foo', '.42'],
    ]


PROLOGUE = dedent(
    """

    --
    -- Name: table1; Type: TABLE; Schema: public; Owner:
    --

    (information for table1 goes here)
    """,
)

TABLE1_COPY = dedent(
    r"""

    -- Data for Name: table1; Type: TABLE DATA; Schema: public;

    COPY foo (id) FROM stdin;
    3
    1
    4
    1
    5
    9
    2
    6
    5
    3
    8
    4
    \.
    """,
)

TABLE1_COPY_SORTED = dedent(
    r"""

    -- Data for Name: table1; Type: TABLE DATA; Schema: public;

    COPY foo (id) FROM stdin;
    1
    1
    2
    3
    3
    4
    4
    5
    5
    6
    8
    9
    \.
    """,
)

EPILOGUE = dedent(
    """
    -- epilogue
    """,
)


def test_split_sql_file(tmpdir):
    """Test splitting a SQL file with COPY statements."""
    sql_file = tmpdir / "test.sql"
    sql_file.write(PROLOGUE + TABLE1_COPY + EPILOGUE)

    split_sql_file(sql_file, max_memory=190)

    split_files = sorted(path.relto(tmpdir) for path in tmpdir.listdir())
    assert split_files == [
        "0000_prologue.sql",
        "0001_public.table1.sql",
        "9999_epilogue.sql",
        "test.sql",
    ]
    assert (tmpdir / "0000_prologue.sql").read() == PROLOGUE
    assert (tmpdir / "0001_public.table1.sql").read() == TABLE1_COPY_SORTED
    assert (tmpdir / "9999_epilogue.sql").read() == EPILOGUE


@pytest.mark.parametrize(
    ("size", "expect"),
    [
        ("0", 0),
        ("1", 1),
        ("1k", 1024),
        ("1m", 1024**2),
        ("1g", 1024**3),
        ("100_000K", 102400000),
        ("1.5M", 1536 * 1024),
        ("1.5G", 1536 * 1024**2),
        ("1.5", 1),
        ("1.5 kibibytes", 1536),
        ("1.5 Megabytes", 1024 * 1536),
        ("1.5 Gigs", 1024**2 * 1536),
        ("1.5KB", 1536),
        (".5MB", 512 * 1024),
        ("20GB", 20 * 1024**3),
    ],
)
def test_memory_size(size, expect):
    """Test parsing human-readable memory sizes with `memory_size`."""
    result = memory_size(size)

    assert result == expect
