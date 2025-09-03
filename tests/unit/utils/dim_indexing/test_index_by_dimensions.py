"""Tests for class :class:`ncdata.utils.index_by_dimension`.

This is the more direct indexer approach.
"""

import numpy as np

from ncdata.utils import dataset_differences, index_by_dimensions

from . import (  # noqa: F401
    make_dims_testdata,
    make_dims_testdata_1d,
    x_slices,
    xy_slices,
)


def test_1d_index(x_slices):  # noqa: F811
    x_base = np.arange(5.0)
    data = make_dims_testdata_1d(x_base)
    result = index_by_dimensions(data, X=x_slices)

    # Make an expected result from an array indexed with *numpy*, to check equivalence.
    expect_x = x_base[x_slices]
    expect_data = make_dims_testdata_1d(expect_x)

    assert dataset_differences(result, expect_data) == []


def test_2d_index(xy_slices):  # noqa: F811
    x_inds, y_inds = xy_slices
    x_base, y_base = np.arange(5.0), np.arange(4.0)

    data = make_dims_testdata(x=x_base, y=y_base)
    result = index_by_dimensions(data, X=x_inds, Y=y_inds)

    expect_x = x_base[x_inds]
    expect_y = y_base[y_inds]
    expect_data = make_dims_testdata(expect_x, expect_y)

    assert dataset_differences(result, expect_data) == []
