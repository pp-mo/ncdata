.. _ncdata-introduction:

This page presents a first-look overview of NcData features.
A lot of this is presented as code examples.


Working with NcData objects
===========================
In NcData, netcdf data structures are represented as Python objects in a
relatively natural way.

Objects can be freely created, displayed, modified and combined.
The following code snippets demonstrate the absolute basics.

.. warning::

    NcData code currently prioritises flexibility over correctness.
    As a result, the NcData object classes do not currently control what
    type of data is assigned, so it is possible to make a mess when creating or
    modifying objects.

    Likewise, internal consistency is not checked, so it is possible to create
    data that cannot be stored in an actual file.
    See :func:`ncdata.utils.save_errors`.

    We may revisit this in later releases to make data manipulation "safer".


Simple data creation
^^^^^^^^^^^^^^^^^^^^
The :class:`ncdata.NcData` object is the basic container, representing
a dataset or group.  It contains :attr:`~ncdata.NcData.dimensions`,
:attr:`~ncdata.NcData.variables`, :attr:`~ncdata.NcData.groups`,
and :attr:`~ncdata.NcData.attributes`::

    >>> from ncdata import NcData, NcDimension, NcVariable
    >>> data = NcData("myname")
    >>> data
    <ncdata._core.NcData object at 0x7f88118dd700>
    >>> print(data)
    <NcData: myname
    >

    >>> dim = NcDimension("x", 3)
    >>> data.dimensions.add(dim)
    >>> print(data)
    <NcData: myname
        dimensions:
            x = 3
    >

    >>> data.dimensions['x'] is dim
    True


Getting data to+from files
^^^^^^^^^^^^^^^^^^^^^^^^^^
The :mod:`ncdata.netcdf4` module provides simple means of reading and writing
NetCDF files via the `netcdf4-python package <http://unidata.github.io/netcdf4-python/>`_.

Simple example::

    >>> from ncdata.netcdf4 import to_nc4, from_nc4

    >>> filepath = "./tmp.nc"
    >>> to_nc4(data, filepath)

    >>> from subprocess import check_output
    >>> print(check_output('ncdump -h tmp.nc', shell=True).decode())
    netcdf tmp {
    dimensions:
        x = 3 ;
    }

    >>> data2 = from_nc4(filepath)
    >>> print(data2)
    <NcData: /
        dimensions:
            x = 3
    >

Please see `Converting between data formats`_ for more details.


Variables
^^^^^^^^^
Variables live in a :attr:`ncdata.NcData.variables` attribute,
which behaves like a dictionary::

    >>> var = NcVariable("vx", dimensions=["x"], dtype=float)
    >>> data.variables.add(var)

    >>> data.variables
    {'vx': <ncdata._core.NcVariable object at ... >}

    >>> data.variables['vx'] is var
    True

    >>> print(data)
    <NcData: myname
        dimensions:
            x = 3

        variables:
            <NcVariable(float64): vx(x)>
    >


Attributes
^^^^^^^^^^
Variables live in the ``attributes`` property of a :class:`~ncdata.NcData`
or :class:`~ncdata.Variable`::

    >>> var.set_attrval('a', 1)
    NcAttribute('a', 1)
    >>> var.set_attrval('b', 'this')
    NcAttribute('b', 'this')

    >>> print(var)
    <NcVariable(float64): vx(x)
        vx:a = 1
        vx:b = 'this'
    >

    >>> print(var.attributes)
    {'a': NcAttribute('a', 1), 'b': NcAttribute('b', 'this')}

    >>> print(data)
    <NcData: myname
        dimensions:
            x = 3

        variables:
            <NcVariable(float64): vx(x)
                vx:a = 1
                vx:b = 'this'
            >
    >

For technical reasons, each attribute is represented as an independent python
:class:`ncdata.NcAttribute` object, i.e. they are *not* simply stored as a
values in a name/value map.

Attribute values are actually :mod:`numpy.ndarray`, and hence have a ``dtype``.
To make this easier, you can use regular python numbers and strings with
:meth:`ncdata.NcAttribute.as_python_value` and the
:meth:`~ncdata.NcVariable.set_attrval`
and :meth:`~ncdata.NcVariable.get_attrval` of NcData/NcVariable.


Deletion and Renaming
^^^^^^^^^^^^^^^^^^^^^
Use python 'del' operation to remove::

    >>> del var.attributes['a']
    >>> print(var)
    <NcVariable(float64): vx(x)
        vx:b = 'this'
    >

There is also a 'rename' method of variables/attributes/groups::

    >>> var.attributes.rename("b", "qq")
    >>> print(var)
    <NcVariable(float64): vx(x)
        vx:qq = 'this'
    >

    >>> print(data)
    <NcData: myname
        dimensions:
            x = 3

        variables:
            <NcVariable(float64): vx(x)
                vx:qq = 'this'
            >
    >

.. warning::

    Renaming a :class:`~ncdata.NcDimension` within a :class:`~ncdata.NcData`
    does *not* adjust the variables which reference it, since a variables'
    :attr:`~ncdata.NcVariable.dimensions` is a simple list of names.
    See : `renaming_dimensions`_ , also :func:`ncdata.utils.save_errors`.


Converting between data formats
===============================
NcData is designed for easy + fast data conversion to and from other formats.
It currently supports *three* other data formats :

* netcdf data files (see : :mod:`ncdata.netcdf4`)
* Iris cubes (see : :mod:`ncdata.iris`)
* Xarray datasets (see : :mod:`ncdata.xarray`)

There are also convenience functions to convert *directly* between Iris and
Xarray : see `Converting between Iris and Xarray`_.

The details of feature support for each of the formats is discussed
at :ref:`interface_support`.

.. note::

    It is a key design principle of NcData that variable data arrays
    are handled efficiently.  This means that it passes data freely between
    NcData, Iris  and Xarray without copying it
    (when "real" i.e. :class:`numpy.ndarray`), or fetching it
    (when "lazy", i.e. :class:`dask.array.Array`).

    Another key principle is that data format conversion via ncdata should be
    equivalent to loading and saving via files.

    See `Design Principles <../user_guide/design_principles.html#design-principles>`_.


Example code snippets :

    >>> from ndata.threadlock_sharing import enable_lockshare
    >>> enable_lockshare(iris=True, xarray=True)

    >>> from ncdata.netcdf import from_nc4
    >>> ncdata = from_nc4("datapath.nc")

    >>> from ncdata.iris import to_iris, from_iris
    >>> xx, yy =  to_iris(ncdata, ['x_wind', 'y_wind'])
    >>> vv = (xx * xx + yy * yy) ** 0.5
    >>> vv.units = xx.units

    >>> from ncdata.xarray import to_xarray
    >>> xrds = to_xarray(from_iris(vv))
    >>> xrds.to_zarr(out_path)

    >>> from ncdata.iris_xarray import cubes_from_xarray
    >>> vv2 = cubes_from_xarray(xrds)
    >>> assert vv2 == vv


Thread safety
^^^^^^^^^^^^^
.. warning::

    When working with data from NetCDF files in conjunction with either Iris or
    Xarray, it is usually necessary to couple their thread safety schemes to
    prevent possible errors when computing or saving lazy data.
    For example:

        >>> from ndata.threadlock_sharing import enable_lockshare
        >>> enable_lockshare(iris=True, xarray=True)

    See details at :mod:`ncdata.threadlock_sharing`


Working with NetCDF files
^^^^^^^^^^^^^^^^^^^^^^^^^
There are conversion functions to and from NetCDF datafiles
in :mod:`ncdata.netcdf4`

* :func:`ncdata.netcdf4.from_nc4`
* :func:`ncdata.netcdf4.to_nc4`


Working with Iris
^^^^^^^^^^^^^^^^^
There are conversion functions to and from Iris :class:`~iris.cube.Cube`
in :mod:`ncdata.iris`

* :func:`ncdata.iris.from_iris`
* :func:`ncdata.iris.to_iris`


Working with Xarray
^^^^^^^^^^^^^^^^^^^
There are conversion functions to and from Xarray :class:`~xarray.Dataset`
in :mod:`ncdata.xarray`

* :func:`ncdata.xarray.from_xarray`
* :func:`ncdata.xarray.to_xarray`


Converting between Iris and Xarray
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
There is also a :mod:`ncdata.iris_xarray` module which provides direct
conversion between Iris and Xarray.

This is really just a convenience,
as naturally it does use Ncdata objects as the intermediate.

* :func:`ncdata.iris_xarray.cubes_to_xarray`
* :func:`ncdata.iris_xarray.cubes_from_xarray`
