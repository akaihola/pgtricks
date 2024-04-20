"""Merge sort implementation to handle large files by sorting them in partitions."""

from __future__ import annotations

import sys
from heapq import merge
from tempfile import TemporaryFile
from typing import IO, Any, Callable, Iterable, Iterator, cast


class MergeSort(Iterable[str]):
    """Merge sort implementation to handle large files by sorting them in partitions."""

    def __init__(
        self,
        key: Callable[[str], Any] = str,
        directory: str = ".",
        max_memory: int = 190,
    ) -> None:
        """Initialize the merge sort object."""
        self._key = key
        self._directory = directory
        self._max_memory = max_memory
        # Use binary mode to avoid newline conversion on Windows.
        self._partitions: list[IO[bytes]] = []
        self._iterating: Iterable[str] | None = None
        self._buffer: list[str] = []
        self._memory_counter = 0
        self._flush()

    def append(self, line: str) -> None:
        """Append a line to the set of lines to be sorted."""
        if self._iterating:
            message = "Can't append lines after starting to sort"
            raise ValueError(message)
        self._memory_counter -= sys.getsizeof(self._buffer)
        self._buffer.append(line)
        self._memory_counter += sys.getsizeof(self._buffer)
        self._memory_counter += sys.getsizeof(line)
        if self._memory_counter >= self._max_memory:
            self._flush()

    def _flush(self) -> None:
        if self._buffer:
            # Use binary mode to avoid newline conversion on Windows.
            self._partitions.append(TemporaryFile(mode="w+b", dir=self._directory))
            self._partitions[-1].writelines(
                line.encode("UTF-8") for line in sorted(self._buffer, key=self._key)
            )
        self._buffer = []
        self._memory_counter = sys.getsizeof(self._buffer)

    def __next__(self) -> str:
        """Return the next line in the sorted list of lines."""
        if not self._iterating:
            if self._partitions:
                # At least one partition has already been flushed to disk.
                # Iterate the merge sort for all partitions.
                self._flush()
                for partition in self._partitions:
                    partition.seek(0)
                self._iterating = merge(
                    *[
                        (line.decode("UTF-8") for line in partition)
                        for partition in self._partitions
                    ],
                    key=self._key,
                )
            else:
                # All lines fit in memory. Iterate the list of lines directly.
                self._iterating = iter(sorted(self._buffer))
        return next(cast(Iterator[str], self._iterating))

    def __iter__(self) -> Iterator[str]:
        """Return the iterator object for the sorted list of lines."""
        return self
