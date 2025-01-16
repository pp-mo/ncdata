.. _interface_support:

Support for Interface Packages
==============================

NetCDF4 Compatibility
---------------------
NcData supports netCDF4-python package versions >= 1.6.5,
which implies the NetCDF4 library version >= 4.9.

The `Continuous Integration testing on GitHub`_ tests against the latest version compatible with Iris and Xarray.

Datatypes
^^^^^^^^^
Ncdata supports all the regular datatypes of netcdf, but *not* the
variable-length and user-defined datatypes.

This means, notably, that all string variables will have the basic numpy type
'S1', equivalent to netcdf 'NC_CHAR'.  Thus, multi-character string variables
must always have a definite "string-length" dimension.

Attribute values, by contrast, are treated as Python strings with the normal
variable length support.  Their basic dtype can be any numpy string dtype,
but will be converted when required.

The NetCDF C library and netCDF4-python do not support arrays of strings in
attributes, so neither does NcData.


Data Scaling, Masking and Compression
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Ncdata does not implement scaling and offset within data arrays :  The ".data"
array has the actual variable dtype, and the "scale_factor" and
"add_offset" attributes are treated like any other attribute.

The existence of a "_FillValue" attribute controls how.. TODO

.. _file-storage:

File storage control
^^^^^^^^^^^^^^^^^^^^
The :func:`ncdata.netcdf4.to_nc4` cannot control compression or storage options
provided by :meth:`netCDF4.Dataset.createVariable`, which means you can't
control the data compression and translation facilities of the NetCDF file
library.
If required, you should use :mod:`iris` or :mod:`xarray` for this.

Although file-specific storage aspects, such as chunking, data-paths or compression
strategies, are not recorded in the core objects.  However, array representations in
variable and attribute data (notably dask lazy arrays) may hold such information.

The concept of "unlimited" dimensions is also, arguably an exception.  However, this is a
core provision in the NetCDF data model itself (see "Dimension" in the `NetCDF Classic Data Model`_).


Dask chunking control
^^^^^^^^^^^^^^^^^^^^^
Loading from netcdf files generates  variables whose data arrays are all Dask
lazy arrays.  These are created with the "chunks='auto'" setting.

There is simple user override API available to control this on a per-dimension basis.
See :func:`ncdata.netcdf4.from_nc4`.


Xarray Compatibility
--------------------
NcData is tested with xarray >= 2023.7.0

The `Continuous Integration testing on GitHub`_ test against the latest
released version of Xarray compatible with the other requirements
(i.e., usually, the latest release version).

The "encoding" controls are lost in converting from Xarray to Ncdata.
However, an "encoding" attribute which exists on a variable **will** be passed
to the 'encoding' control in Xarray, so this can be used to control data
storage formats.

The NcVariable.data arrays behave as if netCDF4.Variable arrays, hence they
contain raw data which Xarray may convert from integers to floating-point, or
masked data to NaNs.

.. warning::
    In conversion to xarray with :func:`~ncdata.xarray.to_xarray`
    dataset encodings are not reproduced, most notably
    **any "unlimited_dims" control is lost**.  But, this is effectively a bug,
    which may be fixed later.
    See : `issue#66 <https://github.com/pp-mo/ncdata/issues/66>`_


Iris Features
-------------
The `Continuous Integration testing on GitHub`_ tests against the
latest-current "main" branch of Iris.

Ncdata is compatible with iris >= v3.7.0
see : `support added in v3.7.0 <https://scitools-iris.readthedocs.io/en/stable/whatsnew/3.7.html#internal>`_

.. warning::

    In conversion from iris cubes with :func:`ncdata.iris.from_iris`
    use of an `unlimited_dims` key currently causes an exception
    See : `issue#43 <https://github.com/pp-mo/ncdata/issues/43>`_


.. _Continuous Integration testing on GitHub: https://github.com/pp-mo/ncdata/blob/main/.github/workflows/ci-tests.yml
.. _NetCDF Classic Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#classic_model
