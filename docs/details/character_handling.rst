.. _string-and-character-data:

Character and String Data Handling
----------------------------------
NetCDF can contain string and character data in at least 3 different contexts :

Characters in Data Component Names
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
That is, names of groups, variables, attributes or dimensions.
Component names in the API are just native Python strings.

Since NetCDF version 4, the names of components within files are fully unicode
compliant, using UTF-8.

These names can use virtually **any** characters, with the exception of the forward
slash "/", since in some technical cases a component name needs to specified as a
"path-like" compound.


.. _character-attributes:

Characters in Attribute Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Character data in string *attribute* values can likewise be read and written simply as
Python strings.

However they are actually *stored* in an :class:`~ncdata.NcAttribute`'s
``.value`` as a character array of dtype "<U??"  (that is, the dtype does not really
have a "??", but some definite length).  These are returned by
:meth:`ncdata.NcAttribute.as_python_value` as a simple Python string.

A vector of strings is also a permitted attribute value, but bear in mind that
**a vector of strings is not currently supported in netCDF4 implementations**.
Thus, you cannot have an array or list of strings as an attribute value in an actual file,
and if stored to a file such an attribute will be concatenated into a single string value.

In actual files, Unicode is again supported via UTF-8, and seamlessly encoded/decoded.


Characters in Variable Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Character data in variable *data* arrays are generally stored as fixed-length arrays of
characters (i.e. fixed-width strings), and no unicode interpretation is applied by the
libraries (neither netCDF4 or ncdata).  In this case, the strings appear in Python as
numpy character arrays of dtype "<U1".  All elements have the same fixed length, but
may contain zero bytes so that they convert to variable-width (Python) strings up to a
maximum width.  Trailing characters are filled with "NUL", i.e. "\\0" character
aka "zero byte".  The (maximum) string length is a separate dimension, which is
recorded as a normal netCDF file dimension like any other.

.. note::

    Although it is not tested, it has proved possible (and useful) at present to load
    files with variables containing variable-length string data, but it is
    necessary to supply an explicit user chunking to workaround limitations in Dask.
    Please see the :ref:`howto example <howto_load_variablewidth_strings>`.

.. warning::

    The netCDF4 package will perform automatic character encoding/decoding of a
    character variable if it has a special ``_Encoding`` attribute.  Ncdata does not
    currently allow for this.  See : :ref:`known-issues`

