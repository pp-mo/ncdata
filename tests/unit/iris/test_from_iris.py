"""
Tests for :func:`ncdata.iris.from_iris`.

Most practical behaviours relating to different types of dataset content are tested in
:mod:`tests/integration/test_roundtrips_iris`.  For example, different datatypes,
the use of groups, passing of data arrays and attributes.

This module only tests some specific API and behaviours of the top-level function, not
covered by the generic 'roundtrip' testcases.
"""
import dask.array as da
import numpy as np
import pytest

from iris.coords import DimCoord
from iris.cube import Cube

from ncdata.iris import from_iris


class MonitoredArray:
    """
    An array wrapper for monitoring dask deferred accesses.

    Wraps a real array, and can be read (indexed), enabling it to be wrapped with
    dask.array_from_array.  It then records the read operations performed on it.
    """

    def __init__(self, data):
        self.dtype = data.dtype
        self.shape = data.shape
        self.ndim = data.ndim
        self._data = data
        self._accesses = []

    def __getitem__(self, keys):
        self._accesses.append(keys)
        return self._data[keys]


def sample_cube(data_array=None):
    """
    Create a basic test-cube.

    It always has a first dimension of 3, and a matching "time" dim-coord.
    You can pass in a different data array with more dims, but first dim must be 3.
    """
    if data_array is None:
        data_array = np.arange(3.0)
    time_co = DimCoord(
        [0.0, 1, 2], standard_name="time", units="days since 2001-01-01"
    )
    cube = Cube(data_array, standard_name="air_temperature", units="K")
    cube.add_dim_coord(time_co, 0)
    return cube


def test_single_cube():
    """
    Check that we can convert a single Iris cube to ncdata.

    We also check that no lazy data is fetched, as expected.
    """
    monitored_array = MonitoredArray(np.arange(6.0).reshape((3, 2)))
    dask_array = da.from_array(monitored_array, chunks=(3, 1), meta=np.ndarray)
    cube = sample_cube(dask_array)
    assert cube.has_lazy_data()
    assert len(monitored_array._accesses) == 0

    ncdata = from_iris(cube)

    # make basic tests on the result
    assert list(ncdata.dimensions.keys()) == ["time", "dim1"]
    assert all(not dim.unlimited for dim in ncdata.dimensions.values())
    assert list(ncdata.variables.keys()) == ["air_temperature", "time"]

    # check that the wrapped data array has still not been read (i.e. no compute)
    assert len(monitored_array._accesses) == 0

    # Check that the variable data matches the cube data ..
    sameness = da.all(
        ncdata.variables["air_temperature"].data == cube.core_data()
    )
    sameness = sameness.compute()
    assert sameness == np.array(True)

    # Check that the original data *has* now been accessed, in 2 chunks ..
    assert len(monitored_array._accesses) == 2
    # .. but the cube itself has still not been realised
    assert cube.has_lazy_data()


def test_multiple_cubes():
    """Check that we can pass multiple cubes to the conversion."""
    cube1 = sample_cube()
    cube2 = cube1.copy()
    cube2.rename("cube2")

    # convert 2 cubes at once
    ncdata = from_iris([cube1, cube2])

    # the result should now have 3 data variables: time, air_temperature and 'cube2'
    # N.B. this means the two cubes share a 'time' variable, as it should be.
    assert list(ncdata.variables.keys()) == [
        "air_temperature",
        "time",
        "cube2",
    ]


@pytest.mark.skip("'from_iris' not yet working with unlimited dimensions.")
def test_kwargs_unlimited():
    """Check iris-save kwargs control : make the time dimension unlimited."""
    cube = sample_cube()
    kwargs = dict(unlimited_dimensions=["time"])

    ncdata = from_iris(cube, **kwargs)

    assert ncdata.dimensions["time"].unlimited is True


def test_kwargs_fill_value():
    """Check iris-save kwargs control : save with a user fill-value."""
    data = np.ma.masked_array([0.0, 1.0, 2.0], mask=[False, True, False])
    cube = sample_cube(data)

    # Save with afil-value keyword.
    kwargs = dict(fill_value=-999.0)
    ncdata = from_iris(cube, **kwargs)

    # Check that the resulting variable has the expected attribute + (raw) data values
    ncdata_var = ncdata.variables["air_temperature"]
    assert ncdata_var.attributes["_FillValue"].as_python_value() == -999.0
    assert np.all(ncdata_var.data == [0.0, -999, 2])


def test_kwargs_packing():
    """Check iris-save kwargs control : scale+offset packing into a smaller dtype."""
    data = np.array([0.0, 1.0, 2.0])
    cube = sample_cube(data)

    # Save with packing controls in a 'packing' keyword.
    kwargs = dict(
        packing=dict(dtype=np.int16, scale_factor=0.1, add_offset=-5.3)
    )
    ncdata = from_iris(cube, **kwargs)

    # Check that the resulting variable has the expected dtype and (raw) data values
    var_data = ncdata.variables["air_temperature"].data
    assert var_data.dtype == np.dtype(np.int16)
    assert isinstance(var_data, da.Array)
    real_data = var_data.compute()
    assert np.all(real_data == [53, 63, 73])
