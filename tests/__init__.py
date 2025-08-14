"""Tests for :mod:`ncdata`."""

from pathlib import Path

testdata_dir = Path(__file__).parent / "testdata"


class MonitoredArray:
    """
    An array wrapper for monitoring dask deferred accesses.

    Wraps a real array, and can be read (indexed), enabling it to be wrapped with
    dask.array_from_array.  It then records the read operations performed on it.
    """

    def __init__(self, data):
        """Create a MonitoredArray, containing a numpy array."""
        self.dtype = data.dtype
        self.shape = data.shape
        self.ndim = data.ndim
        self._data = data
        self._accesses = []

    def __getitem__(self, keys):
        """Fetch indexed data section."""
        self._accesses.append(keys)
        return self._data[keys]
