.. _general_topics:

General Topics
==============
Odd discussion topics realting to core ncdata classes + data management

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

However, at present ncdata directly supports only the so-called "Primitive Types" of the
`NetCDF Enhanced Data Model`_  : :ref:`data-model`.
So, this does ***not*** include the user-defined, enumerated or variable-length datatypes.

.. attention::

    In practice, we have found that at least variables of the variable-length "string" datatype do seem to function
    correctly at present, but this is not officially supported, and not currently tested.

    We hope to extend support to the more general `NetCDF Enhanced Data Model`_ in future.

For reference, the currently supported + tested datatypes are currently :

* unsigned byte = numpy "u1"
* unsigned short = numpy "u2"
* unsigned int = numpy "u4"
* unsigned long = numpy "u4"
* byte = numpy "i1"
* short = numpy "i2"
* int = numpy "i4"
* long = numpy "i8"
* float = numpy "f4"
* double = numpy "f8"
* char = numpy "U1"

.. _NetCDF Classic Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#classic_model

.. _NetCDF Enhanced Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#enhanced_model


.. _string-and-character-data:

Character and String Data Handling
----------------------------------
NetCDF can can contain string and character data in at least 3 different contexts :

Characters in Data Component Names
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
(i.e. groups, variables, attributes or dimensions)

Since NetCDF version 4, the names of components within files are fully unicode compliant
and can use virtually ***any*** characters, with the exception of the forward slash "/"
( since in some technical cases a component name needs to specified as a "path-like" compound )

Characters in Variable Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Character data in variable *data* arrays are generally stored as fixed-length arrays of
characters (i.e. fixed-width strings), and no unicode interpretation is applied by the
libraries (neither netCDF4 or ncdata).  In this case, the strings appear in Python as
numpy character arrays of dtype "<U1".  All elements have the same fixed length, but
may contain zero bytes so that they convert to variable-width (Python) strings up to a
maximum width.  The string (maximum) length is a separate dimension, which is recorded
as a normal netCDF dimension like any other.

Characters in Attribute Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Character data in string *attribute* values can be written simply as Python
strings.  They are stored in an :class:`~ncdata.NcAttribute`'s ``.value`` as a
character array of dtype "<U?", or are returned from
:meth:`ncdata.NcAttribute.as_python_value` as a simple Python string.
A vector of strings does also function as an attribute value, but bear in mind that a
vector of strings is not currently supported in netCFD4 implementations.
Unicode is supported, and encodes/decodes seamlessly into actual files.


Thread Safety
-------------
Whenever you combine variable data loaded using more than **one** data-format package
(i.e. at present, Iris and Xarray and Ncdata itself), you can potentially get
multi-threading contention errors in netCDF4 library access.  This may result in
problems ranging from sporadic value changes to a segmentation faults or other system
errors.

In these cases you should always to use the :mod:`ncdata.threadlock_sharing` module to
avoid such problems.  See :ref:`thread-safety`.
