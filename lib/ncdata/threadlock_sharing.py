r"""
Support for "unifying" the thread-safety mechanisms between ncdata and other packages.

Each of the data-format packages (ncdata, iris and xarray) uses its own locking
mechanism to prevent overlapping calls into the netcdf library when called by
multi-threaded code.

Most commonly, this occurs when netcdf file data is read to
compute a Dask array, or written in a Dask delayed write operation.

All 3 data-format packages can map variable data into Dask lazy arrays.  Iris and
Xarray can also create delayed write operations (but ncdata currently does not).

However, those mechanisms cannot protect an operation of that package from
overlapping with one in *another* package.

This module can ensure that all of the enabled packages use the *same* thread lock,
so that any and all of them can safely co-operate in parallel operations.

sample code::

    from ncdata.threadlock_sharing import enable_sharing, disable_sharing
    from ncdata.xarray import from_xarray
    from ncdata.iris import from_iris
    from ncdata.netcdf4 import to_nc4

    enable_sharing(iris=True, xarray=True)

    ds = from_xarray(xarray.open_dataset(file1))
    ds2 = from_iris(iris.load(file2))
    ds.variables['x'].data /= ds2.variables['acell'].data
    to_nc4(ds, output_filepath)

    disable_sharing()

or::

    with sharing_context(iris=True):
        ncdata = NcData(source_filepath)
        ncdata.variables['x'].attributes['units'] = 'K'
        cubes = ncdata.iris.to_iris(ncdata)
        iris.save(cubes, output_filepath)

"""
from contextlib import contextmanager
from unittest import mock

_SHARE_PATCHES = []


# Patch targets in ncdata and iris.
# N.B. we don't ever patch xarray, we only *copy* that lock tp the others.
_IRIS_TARGET = "iris.fileformats.netcdf._thread_safe_nc._GLOBAL_NETCDF4_LOCK"
_NCDATA_TARGET = "ncdata.netcdf4._GLOBAL_NETCDF4_LIBRARY_THREADLOCK"


def enable_sharing(iris: bool = False, xarray: bool = False):
    """
    Begin lock-sharing between ncdata and the requested other packages.

    Does nothing if an existing sharing is already in place.

    Parameters
    ----------
    iris : bool, default False
        make ncdata use the same netcdf lock as iris
    xarray : bool, default False
        make ncdata use the same netcdf lock as xarray

    Notes
    -----
    If an 'enable_sharing' call was already established, the function does nothing,
    i.e. it is not possible to modify an existing share.  Instead, you must call
    :func:`disable_sharing` to cancel the current sharing, before you can establish
    a new one.

    While sharing with *both* iris and xarray, iris is modified to use the same netcdf
    lock as xarray.

    """
    global _SHARE_PATCHES
    # N.B. implement sharing *only if* none already exists
    if not _SHARE_PATCHES and (iris or xarray):
        if iris and not xarray:
            # set ncdata to use the Iris lock
            from iris.fileformats.netcdf._thread_safe_nc import (
                _GLOBAL_NETCDF4_LOCK as IRIS_LOCK,
            )

            patches = [mock.patch(_NCDATA_TARGET, new=IRIS_LOCK)]
        elif xarray and not iris:
            # set ncdata to use the Xarray lock
            from xarray.backends.netCDF4_ import (
                NETCDF4_PYTHON_LOCK as XARRAY_LOCK,
            )

            patches = [mock.patch(_NCDATA_TARGET, new=XARRAY_LOCK)]
        else:
            assert iris and xarray
            # set both ncdata AND Iris to use the Xarray lock
            from xarray.backends.netCDF4_ import (
                NETCDF4_PYTHON_LOCK as XARRAY_LOCK,
            )

            patches = [
                mock.patch(_NCDATA_TARGET, new=XARRAY_LOCK),
                mock.patch(_IRIS_TARGET, new=XARRAY_LOCK),
            ]

        for patch in patches:
            patch.start()
        _SHARE_PATCHES = patches


def disable_sharing():
    """
    Remove any enabled lock-sharing.

    Does nothing if no lock share is in operation.
    """
    global _SHARE_PATCHES
    for patch in _SHARE_PATCHES:
        patch.stop()
    _SHARE_PATCHES = []


@contextmanager
def sharing_context(iris: bool = False, xarray: bool = False):
    """
    Make a context with lock-sharing between the ncdata and the requested packages.

    This allows safe netcdf access when using a combination of ncdata/iris/xarray
    packages.

    """
    try:
        enable_sharing(iris=iris, xarray=xarray)
        yield
    finally:
        disable_sharing()
