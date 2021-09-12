import sys
from heapq import merge
from tempfile import TemporaryFile
from typing import IO, Any, Callable, Iterable, Iterator, List, Optional, cast


class MergeSort(Iterable[str]):
    def __init__(
        self,
        key: Callable[[str], Any] = str,
        directory: str = ".",
        max_memory: int = 190,
    ) -> None:
        self._key = key
        self._directory = directory
        self._max_memory = max_memory
        self._partitions: List[IO[str]] = []
        self._iterating: Optional[Iterable[str]] = None
        self._buffer: List[str] = []
        self._memory_counter = 0
        self._flush()

    def append(self, line: str) -> None:
        if self._iterating:
            raise ValueError("Can't append lines after starting to sort")
        self._memory_counter -= sys.getsizeof(self._buffer)
        self._buffer.append(line)
        self._memory_counter += sys.getsizeof(self._buffer)
        self._memory_counter += sys.getsizeof(line)
        if self._memory_counter >= self._max_memory:
            self._flush()

    def _flush(self) -> None:
        if self._buffer:
            self._partitions.append(TemporaryFile(mode="w+", dir=self._directory))
            self._partitions[-1].writelines(sorted(self._buffer, key=self._key))
        self._buffer = []
        self._memory_counter = sys.getsizeof(self._buffer)

    def __next__(self) -> str:
        if not self._iterating:
            if self._partitions:
                # At least one partition has already been flushed to disk.
                # Iterate the merge sort for all partitions.
                self._flush()
                for partition in self._partitions:
                    partition.seek(0)
                self._iterating = merge(*self._partitions, key=self._key)
            else:
                # All lines fit in memory. Iterate the list of lines directly.
                self._iterating = iter(sorted(self._buffer))
        return next(cast(Iterator[str], self._iterating))

    def __iter__(self) -> Iterator[str]:
        return self
