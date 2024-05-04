"""Tests for the `pgtricks.mergesort` module."""

import functools
from types import GeneratorType
from typing import Iterable, cast

import pytest

from pgtricks.mergesort import MergeSort
from pgtricks.pg_dump_splitsort import linecomp

# This is the biggest amount of memory which can't hold two one-character lines on any
# platform. On Windows it's slightly smaller than on Unix.
JUST_BELOW_TWO_SHORT_LINES = 174


@pytest.mark.parametrize("lf", ["\n", "\r\n"])
def test_mergesort_append(tmpdir, lf):
    """Test appending lines to the merge sort object."""
    m = MergeSort(directory=tmpdir, max_memory=JUST_BELOW_TWO_SHORT_LINES)
    m.append(f"1{lf}")
    assert m._buffer == [f"1{lf}"]
    m.append(f"2{lf}")
    assert m._buffer == []
    m.append(f"3{lf}")
    assert m._buffer == [f"3{lf}"]
    assert len(m._partitions) == 1
    pos = m._partitions[0].tell()
    m._partitions[0].seek(0)
    assert m._partitions[0].read() == f"1{lf}2{lf}".encode()
    assert pos == len(f"1{lf}2{lf}")


@pytest.mark.parametrize("lf", ["\n", "\r\n"])
def test_mergesort_flush(tmpdir, lf):
    """Test flushing the buffer to disk."""
    m = MergeSort(directory=tmpdir, max_memory=JUST_BELOW_TWO_SHORT_LINES)
    for value in [1, 2, 3]:
        m.append(f"{value}{lf}")
    m._flush()
    assert len(m._partitions) == 2
    assert m._partitions[0].tell() == len(f"1{lf}2{lf}")
    m._partitions[0].seek(0)
    assert m._partitions[0].read() == f"1{lf}2{lf}".encode()
    pos = m._partitions[1].tell()
    m._partitions[1].seek(0)
    assert m._partitions[1].read() == f"3{lf}".encode()
    assert pos == len(f"3{lf}")


@pytest.mark.parametrize("lf", ["\n", "\r\n"])
def test_mergesort_iterate_disk(tmpdir, lf):
    """Test iterating over the sorted lines on disk."""
    m = MergeSort(directory=tmpdir, max_memory=JUST_BELOW_TWO_SHORT_LINES)
    for value in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 8, 4]:
        m.append(f"{value}{lf}")
    assert next(m) == f"1{lf}"
    assert isinstance(m._iterating, GeneratorType)
    assert next(m) == f"1{lf}"
    assert next(m) == f"2{lf}"
    assert next(m) == f"3{lf}"
    assert next(m) == f"3{lf}"
    assert next(m) == f"4{lf}"
    assert next(m) == f"4{lf}"
    assert next(m) == f"5{lf}"
    assert next(m) == f"5{lf}"
    assert next(m) == f"6{lf}"
    assert next(m) == f"8{lf}"
    assert next(m) == f"9{lf}"
    with pytest.raises(StopIteration):
        next(m)


@pytest.mark.parametrize("lf", ["\n", "\r\n"])
def test_mergesort_iterate_memory(tmpdir, lf):
    """Test iterating over the sorted lines when all lines fit in memory."""
    m = MergeSort(directory=tmpdir, max_memory=1000000)
    for value in [3, 1, 4, 1, 5, 9, 2, 10, 6, 5, 3, 8, 4]:
        m.append(f"{value}{lf}")
    assert next(m) == f"1{lf}"
    assert not isinstance(m._iterating, GeneratorType)
    assert iter(cast(Iterable[str], m._iterating)) is m._iterating
    assert next(m) == f"1{lf}"
    assert next(m) == f"2{lf}"
    assert next(m) == f"3{lf}"
    assert next(m) == f"3{lf}"
    assert next(m) == f"4{lf}"
    assert next(m) == f"4{lf}"
    assert next(m) == f"5{lf}"
    assert next(m) == f"5{lf}"
    assert next(m) == f"6{lf}"
    assert next(m) == f"8{lf}"
    assert next(m) == f"9{lf}"
    assert next(m) == f"10{lf}"
    with pytest.raises(StopIteration):
        next(m)


@pytest.mark.parametrize("lf", ["\n", "\r\n"])
def test_mergesort_key(tmpdir, lf):
    """Test sorting lines based on a key function."""
    m = MergeSort(directory=tmpdir)
    for value in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 8, 4]:
        m.append(f"{value}{lf}")
    result = "".join(value[0] for value in m)
    assert result == "986554433211"
