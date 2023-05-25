"""Tests for class :class:`ncdata.NcDimension`."""
import numpy as np
import pytest

from ncdata import NcDimension


class Test_NcDimension__init__:
    def test_simple(self):
        # We can create a variable with no args.
        name = "dimname"
        # Use an array object for test size, just so we can check "is".
        # N.B. assumes the constructor copies the reference - which could change.
        size = np.array(4)
        sample = NcDimension(name, size)
        # No data, no dtype.  Variables don't have 'shape' anyway
        assert sample.name is name
        assert sample.size is size


class Test_NcDimension__isunlimited:
    def test_isunlimited__is(self):
        sample = NcDimension("this", 0)
        assert sample.isunlimited()

    def test_isunlimited__isnt(self):
        sample = NcDimension("this", 2)
        assert not sample.isunlimited()


class Test_NcDimension__str:
    @pytest.mark.parametrize("size", (0, 23))
    def test_str_sized(self, size):
        # In all cases, str == repr
        sample = NcDimension("this", size)
        result = str(sample)
        assert result == repr(sample)


class Test_NcDimension__repr:
    @pytest.mark.parametrize("size", (0, 23))
    def test_str_sized(self, size):
        sample = NcDimension("this", size)
        result = repr(sample)
        assert result == f"NcDimension('this', {size})"
