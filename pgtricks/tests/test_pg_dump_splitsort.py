import pytest

from pgtricks.pg_dump_splitsort import linecomp, try_float


@pytest.mark.parametrize(
    's, expect',
    [
        ('', ''),
        ('foo', 'foo'),
        ('0', 0.0),
        ('0.0', 0.0),
        ('0.', 0.0),
        ('4.2', 4.2),
        ('-.42', -0.42),
        (r'\N', r'\N'),
    ],
)
def test_try_float(s, expect):
    result = try_float(s)
    assert type(result) == type(expect)
    assert result == expect


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
        ('42', '', -1),
        ('', '42', 1),
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
