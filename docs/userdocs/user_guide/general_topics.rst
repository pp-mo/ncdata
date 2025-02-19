.. _general_topics:

General Topics
==============
Odd discussion topics relating to core ncdata classes + data management

Validity Checking
-----------------
See : :ref:`correctness-checks`


.. _data-types:

Data Types (dtypes)
-------------------
:ref:`Variable data <variable-dtypes>` and :ref:`attribute values <attribute-dtypes>`
all use a subset of numpy **dtypes**, compatible with netcdf datatypes.
These are effectively those defined by `netcdf4-python <https://unidata.github.io/netcdf4-python/>`_, and this
therefore also effectively determines what we see in `dask arrays <https://docs.dask.org/en/stable/array.html>`_ .

However, at present ncdata directly supports only the so-called "Primitive Types" of the NetCDF "Enhanced Data Model".
So, it does **not** include the user-defined, enumerated or variable-length datatypes.

.. attention::

    In practice, we have found that at least variables of the variable-length "string" datatype **do** seem to function
    correctly at present, but this is not officially supported, and not currently tested.

    See also : :ref:`howto_load_variablewidth_strings`

    We hope to extend support to the more general `NetCDF Enhanced Data Model`_ in future


For reference, the currently supported + tested datatypes are :

* unsigned byte = numpy "u1"
* unsigned short = numpy "u2"
* unsigned int = numpy "u4"
* unsigned int64 = numpy "u4"
* byte = numpy "i1"
* short = numpy "i2"
* int = numpy "i4"
* int64 = numpy "i8"
* float = numpy "f4"
* double = numpy "f8"
* char = numpy "S1"


Character and String Data
-------------------------
String and character data occurs in at least 3 different places :

1. in names of components (e.g. variables)
2. in string attributes
3. in character-array data variables

Very briefly :

* types (1) and (2) are equivalent to Python strings and may include unicode
* type (3) are equivalent to character (byte) arrays, and normally represent only
  fixed-length strings with the length being given as a file dimension.

NetCDF4 does also have provision for variable-length strings as an elemental type,
which you can have arrays of, but ncdata does not yet properly support this.

For more details, please see : :ref:`string-and-character-data`


.. _thread_safety:

Thread Safety
-------------
Whenever you combine variable data loaded using more than **one** data-format package
(i.e. at present, Iris and Xarray and Ncdata itself), you can potentially get
multi-threading contention errors in netCDF4 library access.  This may result in
problems ranging from sporadic value changes to a segmentation faults or other system
errors.

In these cases you should always to use the :mod:`ncdata.threadlock_sharing` module to
avoid such problems.  See :ref:`thread-safety`.


.. _NetCDF Classic Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#classic_model

.. _NetCDF Enhanced Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#enhanced_model

