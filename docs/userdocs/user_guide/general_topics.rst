.. _common_operations:

Common Operations
=================
A group of common operations are available on all the core component types,
i.e. the operations of extract/remove/insert/rename/copy on the ``.datasets``, ``.groups``,
``.dimensions``, ``.variables`` and ``.attributes`` properties of the core objects.

Most of these are hopoefully "obvious" Pythonic methods of the container objects.

Extract and Remove
------------------
These are implemented as :meth:`~ncdata.NameMap.__delitem__` and :meth:`~ncdata.NameMap.pop`
methods, which work in the usual way.

Examples :

* ``var_x = dataset.variables.pop("x")``
* ``del data.variables["x"]``

Insert / Add
------------
A new content (component) can be added under its own name with the
:meth:`~ncdata.NameMap.add` method.

Example : ``dataset.variables.add(NcVariable("x", dimensions=["x"], data=my_data))``

An :meth:`~ncdata.NcAttribute` can also be added or set (if already present) with the special
:meth:`~ncdata.NameMap.set_attrval` method.

Example : ``dataset.variables["x"].set_attrval["units", "m s-1")``

Rename
------
A component can be renamed with the :meth:`~ncdata.NameMap.rename` method.  This changes
both the name in the container **and** the component's own name -- it is not recommended
ever to set ``component.name`` directly, as this obviously can become inconsistent.

Example : ``dataset.variables.rename("x", "y")``

.. warning::
    Renaming a dimension will not rename references to it (i.e. in variables), which
    obviously may cause problems.
    We may add a utility to do this safely this in future.

Copy
----
All core objects support a ``.copy()`` method, which however does not copy array content
(e.g. variable data or attribute arrays).  See for instance :meth:`ncdata.NcData.copy`.

There is also a utility function :func:`ncdata.utils.ncdata_copy`, this is effectively
the same as the NcData object copy.


Creation
--------
The constructors should allow reasonably readable inline creation of data.
See here : :ref:`data-constructors`

Ncdata is deliberately not very fussy about 'correctness', since it is not tied to an actual
dataset which must "make sense".   see : :ref:`correctness-checks` .

Hence, there is no great need to install things in the 'right' order (e.g. dimensions
before variables which need them).  You can create objects in one go, like this :

.. code-block::

    data = NcData(
        dimensions=[
            NcDimension("y", 2),
            NcDimension("x", 3),
        ],
        variables=[
            NcVariable("y", dimensions=["y"], data=[10, 11]),
            NcVariable("x", dimensions=["y"], data=[20, 21, 22]),
            NcVariable("dd", dimensions=["y", "x"], data=[[0, 1, 2], [3, 4, 5]])
        ]
    )


or iteratively, like this :

.. code-block::

    data = NcData()
    dims = [("y", 2), ("x", 3)]
    data.variables.addall([
        NcVariable(nn, dimensions=[nn], data=np.arange(ll))
        for ll, nn in dims
    ])
    data.variables.add(
        NcVariable("dd", dimensions=["y", "x"],
        data=np.arange(6).reshape(2,3))
    )
    data.dimensions.addall([NcDimension(nn, ll) for nn, ll in dims])

Note : here, the variables were created before the dimensions


Equality Checks
---------------
We provide a simple ``==`` check for all the core objects but this can be very costly,
at least for variables, because it will check all the data, even in lazy arrays (!).

You can use :func:`ncdata.utils.dataset_differences` for much more nuanced and controllable
checking.


Validity Checking
-----------------
See : :ref:`correctness-checks`

General Topics
==============
Odd discussion topics

.. _data-types:

Data Types (dtypes)
-------------------
:ref:`Variable data <variable-dtypes>` and :ref:`attribute values <attribute-dtypes>`
all use a subset of numpy **dtypes**, compatible with netcdf datatypes.
These are effectively those defined by `netcdf4-python <https://unidata.github.io/netcdf4-python/>`_, and this
therefore also effectively determines what we see in `dask arrays <https://docs.dask.org/en/stable/array.html>`_ .

However, at present ncdata directly supports only the `NetCDF Classic Data Model`_ (plus groups,
see : :ref:`data-model`).
So, this does ***not*** include the user-defined, enumerated or variable-length datatypes.

.. attention::

    In practice, we have found that at least variables of the variable-length "string" datatype do seem to function
    correctly at present, but this is not officially supported, and not currently tested.

    We hope to extend support to the more general `NetCDF Enhanced Data Model`_ in future.

As-of January 2025 there is

.. _NetCDF Classic Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#classic_model

.. _NetCDF Enhanced Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#enhanced_model


.. _character-data:

Character Data
--------------
NetCDF can can contain string and character data in at least 3 different contexts :

1. in variable data arrays
2. in attribute values
3. in names of components (i.e. dimensions / variables / attributes / groups )

The first case (3.) is, effectively, quite separate.
Since NetCDF version 4, the names of items within files are fully unicode compliant and can
use virtually ***any*** characters, with the exception of the forward slash "/"
( since in some technical cases a component name needs to specified as a "path-like" compound )

.. _thread-safety:

Thread Safety
-------------
In short, it turns out that thread safety can be an issue whenever "lazy" data is being read, which occurs whenever
data is being plotted, calculated or written to a new output file.

Whenever data is being "computed" (in Dask terms : see `Dask compute <dask-compute>`_), that was loaded using more than
one of the Iris, Xarray and ncdata.netcdf4 packages, then :mod:`ncdata.threadlock_sharing` must be used to avoid
possible errors.

A Fuller Explanation..
^^^^^^^^^^^^^^^^^^^^^^
In practice, Iris, Xarray and Ncdata are all capable of scanning netCDF files and interpreting
their metadata, while **not** reading all the core variable data contained in them.

The file load generates `Dask.arrray <dask-array>`_ objects representing sections of
variable data for calculation on later request, with certain key benefits :

1. no data loading or calculation happens until needed
2. the work is divided into sectional 'tasks', of which only some may ultimately be needed
3. it may be possible to perform multiple sections of calculation (including data fetch) in parallel
4. it may be possible to localise operations (fetch or calculate) near to data distributed across a cluster

Usually, the most efficient parallelisation of array operations is by multi-threading,
since that can use memory sharing of large data arrays in memory.  However, the python netCDF4 library is **not threadsafe**,
therefore the "netcdf fetch" call in each input operation must be guarded by a mutex.

So Xarray, Iris and ncdata all create data objects with Dask arrays, which reference input data chunks fetching sections
of the input files.  Each of those uses a mutex to stop it accessing the netCDF4 interface at the same time as
any of the others.

This works beautifully **until** ncdata connects lazy data loaded with Iris (say) with lazy data loaded from Xarray,
which unfortunately are using their own *separate* mutexes to protect the *same* netcdf library.  Then, when we attempt
to calculate or save this result, we may get sporadic and unpredictable system-level errors, even a core-dump.

So, the function of :mod:`ncdata.threadlock_sharing` is to **connect** the thread-locking schemes of the separate libraries,
so that they cannot accidentally overlap an access call from the other package in a different thread,
just as they already cannot overlap one of their own.

.. _dask-array: https://docs.dask.org/en/stable/array.html
.. _dask-compute: https://docs.dask.org/en/latest/generated/dask.array.Array.compute.html