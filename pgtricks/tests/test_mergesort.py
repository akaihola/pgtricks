from types import GeneratorType
from typing import cast, Iterable

import pytest

from pgtricks.mergesort import MergeSort


def test_mergesort_append(tmpdir):
    m = MergeSort(directory=tmpdir, max_memory=190)
    m.append('1\n')
    assert m._buffer == ['1\n']
    m.append('2\n')
    assert m._buffer == []
    m.append('3\n')
    assert m._buffer == ['3\n']
    assert len(m._partitions) == 1
    assert m._partitions[0].tell() == 4
    m._partitions[0].seek(0)
    assert m._partitions[0].read() == '1\n2\n'


def test_mergesort_flush(tmpdir):
    m = MergeSort(directory=tmpdir, max_memory=190)
    for value in [1, 2, 3]:
        m.append(f'{value}\n')
    m._flush()
    assert len(m._partitions) == 2
    assert m._partitions[0].tell() == 4
    m._partitions[0].seek(0)
    assert m._partitions[0].read() == '1\n2\n'
    assert m._partitions[1].tell() == 2
    m._partitions[1].seek(0)
    assert m._partitions[1].read() == '3\n'


def test_mergesort_iterate_disk(tmpdir):
    m = MergeSort(directory=tmpdir, max_memory=190)
    for value in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 8, 4]:
        m.append(f'{value}\n')
    assert next(m) == '1\n'
    assert isinstance(m._iterating, GeneratorType)
    assert next(m) == '1\n'
    assert next(m) == '2\n'
    assert next(m) == '3\n'
    assert next(m) == '3\n'
    assert next(m) == '4\n'
    assert next(m) == '4\n'
    assert next(m) == '5\n'
    assert next(m) == '5\n'
    assert next(m) == '6\n'
    assert next(m) == '8\n'
    assert next(m) == '9\n'
    with pytest.raises(StopIteration):
        next(m)


def test_mergesort_iterate_memory(tmpdir):
    m = MergeSort(directory=tmpdir, max_memory=1000000)
    for value in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 8, 4]:
        m.append(f'{value}\n')
    assert next(m) == '1\n'
    assert not isinstance(m._iterating, GeneratorType)
    assert iter(cast(Iterable[str], m._iterating)) is m._iterating
    assert next(m) == '1\n'
    assert next(m) == '2\n'
    assert next(m) == '3\n'
    assert next(m) == '3\n'
    assert next(m) == '4\n'
    assert next(m) == '4\n'
    assert next(m) == '5\n'
    assert next(m) == '5\n'
    assert next(m) == '6\n'
    assert next(m) == '8\n'
    assert next(m) == '9\n'
    with pytest.raises(StopIteration):
        next(m)
