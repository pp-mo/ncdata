NetCDF Thread Locking
=====================
Ncdata includes support for "unifying" the thread-safety mechanisms between
ncdata and the format packages it supports (Iris and Ncdata).

This concerns the safe use of the common NetCDF library by multiple threads.
Such multi-threaded access usually occurs when your code has Dask arrays
created from netcdf file data, which it is either computing or storing to an
output netcdf file.

The netCDF4 package (and the underlying C library) does not implement any
threadlock, neither is it thread-safe (re-entrant) by design.
Thus contention is possible unless controlled by the calling packages.
*Each* of the data-format packages (Ncdata, Iris and Xarray) defines its own
locking mechanism to prevent overlapping calls into the netcdf library.

All 3 data-format packages can map variable data into Dask lazy arrays.  Iris and
Xarray can also create delayed write operations (but ncdata currently does not).

However, those mechanisms cannot protect an operation of that package from
overlapping with one in *another* package.

The :mod:`ncdata.threadlock_sharing` module can ensure that all of the relevant
packages use the *same* thread lock,
so that they can safely co-operate in parallel operations.

sample code::

    from ncdata.threadlock_sharing import enable_lockshare, disable_lockshare
    from ncdata.xarray import from_xarray
    from ncdata.iris import from_iris
    from ncdata.netcdf4 import to_nc4

    enable_lockshare(iris=True, xarray=True)

    ds = from_xarray(xarray.open_dataset(file1))
    ds2 = from_iris(iris.load(file2))
    ds.variables['x'].data /= ds2.variables['acell'].data
    to_nc4(ds, output_filepath)

    disable_lockshare()

or::

    with lockshare_context(iris=True):
        ncdata = NcData(source_filepath)
        ncdata.variables['x'].attributes['units'] = 'K'
        cubes = ncdata.iris.to_iris(ncdata)
        iris.save(cubes, output_filepath)

