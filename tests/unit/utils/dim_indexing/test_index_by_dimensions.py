"""Tests for class :class:`ncdata.utils.index_by_dimension`.

This is the more direct indexer approach.
"""

import numpy as np
import pytest
from ncdata.utils import dataset_differences, index_by_dimensions

from . import dims_test_data

_NUL = slice(None)
_SLICE_OPTS = {
    "empty": (_NUL, _NUL),
    "singleX": (1, _NUL),
    "singleY": (_NUL, 2),
    "rangeX": (slice(2, 4), _NUL),
    "rangeY": (_NUL, slice(1, 3)),
    "picked": ([0, 1, 3], _NUL),
    "openL": (slice(None, 3), _NUL),
    "openR": (slice(3, None), _NUL),
    "dual": (slice(1, 3), slice(3, None)),
    "minus": (2, slice(-2, None)),
}
_OPT_NAMES = list(_SLICE_OPTS.keys())
_OPT_VALUES = list(_SLICE_OPTS.values())


@pytest.fixture(params=_OPT_VALUES, ids=_OPT_NAMES)
def slices(request):
    return request.param


def data_1d(x):
    data = dims_test_data(x=x, y=1)
    # prune awway anything referring to
    del data.dimensions["Z"]
    for varname, var in list(data.variables.items()):
        if any(dim in var.dimensions for dim in ("Y", "Z")):
            data.variables.pop(varname)
    return data


# One-dimensional testcases
_1D_OPTS = {
    "empty": _NUL,
    "single": 1,
    "range": slice(2, 4),
    "picked": [0, 1, 3],
    "openL": slice(None, 3),
    "openR": slice(3, None),
    "minus": slice(-2, None),
}
_1D_OPT_NAMES = list(_1D_OPTS.keys())
_1D_OPT_VALUES = list(_1D_OPTS.values())


@pytest.fixture(params=_1D_OPT_VALUES, ids=_1D_OPT_NAMES)
def x_slices(request):
    return request.param


def test_1d_index(x_slices):
    x_base = np.arange(5.0)
    data = data_1d(x_base)
    result = index_by_dimensions(data, X=x_slices)

    expect_x = x_base[x_slices]
    expect_data = data_1d(expect_x)

    assert dataset_differences(result, expect_data) == []


def test_2d_index(slices):
    x_inds, y_inds = slices
    x_base, y_base = np.arange(5.0), np.arange(4.0)

    data = dims_test_data(x=x_base, y=y_base)
    result = index_by_dimensions(data, X=x_inds, Y=y_inds)

    expect_x = x_base[x_inds]
    expect_y = y_base[y_inds]
    expect_data = dims_test_data(expect_x, expect_y)

    assert dataset_differences(result, expect_data) == []
