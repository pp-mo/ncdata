"""Tests for class :class:`ncdata.NcDimension`."""
from unittest import mock

import numpy as np
import pytest

from ncdata import NcDimension


class Test_NcDimension__init__:
    def test_simple(self):
        name = "dimname"
        # Use an array object for test size, just so we can check "is".
        # N.B. assumes the constructor copies the reference - which could change.
        size = np.array(4)
        sample = NcDimension(name, size)
        # No data, no dtype.  Variables don't have 'shape' anyway
        assert sample.name is name
        assert sample.size is size

    @pytest.mark.parametrize("size", [0, 2])
    @pytest.mark.parametrize(
        "unlim",
        [0, 1, False, True, "x"],
        ids=["unlim_0", "unlim_1", "unlim_F", "unlim_T", "unlim_x"],
    )
    def test_unlimited(self, size, unlim):
        name = "dimname"
        sample = NcDimension(name, size, unlimited=unlim)
        expected_unlim = bool(unlim) or size == 0
        assert isinstance(sample.unlimited, bool)
        assert sample.unlimited == expected_unlim
        # assert sample.isunlimited() == sample.unlimited


class Test_NcDimension__isunlimited:
    def test_isunlimited__is__implicit(self):
        sample = NcDimension("this", 0)
        assert sample.isunlimited()

    def test_isunlimited__is__explicit(self):
        sample = NcDimension("this", 2, unlimited=True)
        assert sample.isunlimited()

    def test_isunlimited__isnt(self):
        sample = NcDimension("this", 2)
        assert not sample.isunlimited()

    def test_isunlimited__equivalent_unlimited(self):
        # cheat: monkeypatch 'bool' in constructor to create distinct objects.
        with mock.patch('ncdata._core.bool', mock.Mock):
            sample = NcDimension("this", 2)
        assert (
           isinstance(sample.unlimited, mock.Mock)
           and not isinstance(sample.unlimited, bool)
        )
        # The isunlimited() call returns EXACTLY the unlimited
        assert sample.isunlimited() is sample.unlimited


class Test_NcDimension__str:
    @pytest.mark.parametrize("size", (0, 23))
    def test_str_sized(self, size):
        # In all cases, str == repr
        sample = NcDimension("this", size)
        result = str(sample)
        assert result == repr(sample)


class Test_NcDimension__repr:
    @pytest.mark.parametrize("size", (0, 23))
    @pytest.mark.parametrize("unlim_type", ("fixed", "unlimited"))
    def test_str_sized(self, size, unlim_type):
        kwargs = {}
        unlimited = unlim_type == "unlimited"
        if unlimited:
            kwargs["unlimited"] = True
        sample = NcDimension("this", size, **kwargs)
        result = repr(sample)
        expected = f"NcDimension('this', {size})"
        if size == 0 or unlimited:
            expected = expected[:-1] + ", unlimited=True)"
        assert result == expected
