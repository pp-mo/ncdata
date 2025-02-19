.. _thread-safety:

NetCDF Thread Locking
=====================
Ncdata provides the :mod:`ncdata.threadlock_sharing` module, which can ensure that all
multiple relevant data-format packages use a "unified" thread-safety mechanism to
prevent them disturbing each other.

This concerns the safe use of the common NetCDF library by multiple threads.
Such multi-threaded access usually occurs when your code has Dask arrays
created from netcdf file data, which it is either computing or storing to an
output netcdf file.

In short, this is not needed when all your data is loaded with only **one** of the data
packages (Iris, Xarray or ncdata).  The problem only occurs when you try to
realise/calculate/save results which combine data loaded from a mixture of sources.

sample code:

.. code-block:: python

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

... *or* ...

.. code-block:: python

    with lockshare_context(iris=True):
        ncdata = NcData(source_filepath)
        ncdata.variables['x'].attributes['units'] = 'K'
        cubes = ncdata.iris.to_iris(ncdata)
        iris.save(cubes, output_filepath)


Background
^^^^^^^^^^
In practice, Iris, Xarray and Ncdata are all capable of scanning netCDF files and interpreting their metadata, while
not reading all the core variable data contained in them.

This generates objects containing Dask :class:`~dask.array.Array`\s, which provide
deferred access to bulk data in files, with certain key benefits :

* no data loading or calculation happens until needed
*  the work is divided into sectional "tasks", of which only some may ultimately be needed
* it may be possible to perform multiple sections of calculation (including data fetch) in parallel
* it may be possible to localise operations (fetch or calculate) near to data distributed across a cluster

Usually, the most efficient parallelisation of array operations is by multi-threading, since that can use memory
sharing of large data arrays in memory.

However, the python netCDF4 library (and the underlying C library) is not threadsafe
(re-entrant) by design, neither does it implement any thread locking itself, therefore
the “netcdf fetch” call in each input operation must be guarded by a mutex.
Thus, contention is possible unless controlled by the calling packages.

Each of Xarray, Iris and ncdata create input data tasks to fetch sections of data from
the input files.  Each uses a mutex lock around netcdf accesses in those tasks, to stop
them accessing the netCDF4 interface at the same time as any of the others.

This works beautifully until ncdata connects (for example) lazy data loaded *with Iris*
with lazy data loaded *from Xarray*.  These would then unfortunately each be using their
own *separate* mutexes to protect the same netcdf library.  So, if we then attempt to
calculate or save the result, which combines data from both sources, we could get
sporadic and unpredictable system-level errors, even a core-dump type failure.

So, the function of :mod:`ncdata.threadlock_sharing` is to connect the thread-locking
schemes of the separate libraries, so that they cannot accidentally overlap an access
call in a different thread *from the other package*, just as they already cannot
overlap *one of their own*.
