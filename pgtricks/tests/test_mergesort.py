"""Tests for the `pgtricks.mergesort` module."""

import os
from types import GeneratorType
from typing import Iterable, cast

import pytest

from pgtricks.mergesort import MergeSort

LF = os.linesep


def test_mergesort_append(tmpdir):
    """Test appending lines to the merge sort object."""
    m = MergeSort(directory=tmpdir, max_memory=190)
    m.append(f"1{LF}")
    assert m._buffer == [f"1{LF}"]
    m.append(f"2{LF}")
    assert m._buffer == []
    m.append(f"3{LF}")
    assert m._buffer == [f"3{LF}"]
    assert len(m._partitions) == 1
    assert m._partitions[0].tell() == len(f"1{LF}2{LF}")
    m._partitions[0].seek(0)
    assert m._partitions[0].read() == f"1{LF}2{LF}"


def test_mergesort_flush(tmpdir):
    """Test flushing the buffer to disk."""
    m = MergeSort(directory=tmpdir, max_memory=190)
    for value in [1, 2, 3]:
        m.append(f"{value}{LF}")
    m._flush()
    assert len(m._partitions) == 2
    assert m._partitions[0].tell() == len(f"1{LF}2{LF}")
    m._partitions[0].seek(0)
    assert m._partitions[0].read() == f"1{LF}2{LF}"
    assert m._partitions[1].tell() == len(f"3{LF}")
    m._partitions[1].seek(0)
    assert m._partitions[1].read() == f"3{LF}"


def test_mergesort_iterate_disk(tmpdir):
    """Test iterating over the sorted lines on disk."""
    m = MergeSort(directory=tmpdir, max_memory=190)
    for value in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 8, 4]:
        m.append(f"{value}{LF}")
    assert next(m) == f"1{LF}"
    assert isinstance(m._iterating, GeneratorType)
    assert next(m) == f"1{LF}"
    assert next(m) == f"2{LF}"
    assert next(m) == f"3{LF}"
    assert next(m) == f"3{LF}"
    assert next(m) == f"4{LF}"
    assert next(m) == f"4{LF}"
    assert next(m) == f"5{LF}"
    assert next(m) == f"5{LF}"
    assert next(m) == f"6{LF}"
    assert next(m) == f"8{LF}"
    assert next(m) == f"9{LF}"
    with pytest.raises(StopIteration):
        next(m)


def test_mergesort_iterate_memory(tmpdir):
    """Test iterating over the sorted lines when all lines fit in memory."""
    m = MergeSort(directory=tmpdir, max_memory=1000000)
    for value in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 8, 4]:
        m.append(f"{value}{LF}")
    assert next(m) == f"1{LF}"
    assert not isinstance(m._iterating, GeneratorType)
    assert iter(cast(Iterable[str], m._iterating)) is m._iterating
    assert next(m) == f"1{LF}"
    assert next(m) == f"2{LF}"
    assert next(m) == f"3{LF}"
    assert next(m) == f"3{LF}"
    assert next(m) == f"4{LF}"
    assert next(m) == f"4{LF}"
    assert next(m) == f"5{LF}"
    assert next(m) == f"5{LF}"
    assert next(m) == f"6{LF}"
    assert next(m) == f"8{LF}"
    assert next(m) == f"9{LF}"
    with pytest.raises(StopIteration):
        next(m)


def test_mergesort_key(tmpdir):
    """Test sorting lines based on a key function."""
    m = MergeSort(directory=tmpdir, key=lambda line: -int(line[0]))
    for value in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 8, 4]:
        m.append(f"{value}{LF}")
    result = "".join(value[0] for value in m)
    assert result == "986554433211"
