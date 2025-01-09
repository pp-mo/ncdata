Core Data Objects
=================
Ncdata uses Python objects to represent netCDF data, and allows the user to freely
inspect and/or modify it, aiming to do this is the most natural and pythonic way.

Data Classes
------------
Each core data model component simply parallels an element of the
`NetCDF Classic Data Model`_ : that is, a Dataset(File) consisting of Dimensions,
Variables, Attributes and Groups.

.. note::
    We are not, as yet, explicitly supporting the NetCDF4 extensions to variable-length
    and user types

The core classes representing the Data Model components are :class:`~ncdata.NcData`,
:class:`~ncdata.NcDimension`, :class:`~ncdata.NcVariable` and
:class:`~ncdata.NcAttribute`.

There is no "NcGroup" class : :class:`~ncdata.NcData` is used for both the "group" and
"dataset" (aka file).

:class:`~ncdata.NcData`
^^^^^^^^^^^^^^^^^^^^^^^
This represents a dataset containing variables, attributes and groups.
It is also used to represent groups.

When it is a dataset, its ``.name`` may be empty.

:class:`~ncdata.NcDimension`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This represents a dimension, defined in terms of name, length, and whether "unlimited"
(or not).

:class:`~ncdata.NcVariable`
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Represents a data variable, with dimensions and, optionally, data and attributes.

Note that ``.dimensions`` is simply a list of names (strings) : they are not
:class:`~ncdata.NcDimension` objects, and not linked to actual dimensions of the
dataset, so *actual* dimensions are only identified dynamically, when they need to be.

Variables can be created with either real (numpy) or lazy (dask) arrays, or no data at
all.  A variable has a ``.dtype``, which may be set if creating with no data.
However, at present, after creation ``.data`` and ``.dtype`` can be reassigned and there
is no further checking of any sort.

Variable Data Arrays
""""""""""""""""""""
When a variable does have a ``.data`` property, this will be an array, with at least
the usual ``shape``, ``dtype`` and ``__getitem__`` properties.  In practice we assume
for now that we will have real (numpy) or lazy (dask) arrays.

When data is exchanged with an actual file, it is simply written if real, and streamed
(via :meth:`dask.array.store`) if lazy.

When data is exchanged with supported data analysis packages (i.e. Iris or Xarray, so
far), these arrays are transferred directly without copying or making duplicates (such
as numpy views).
This is a core principle (see :ref:`design-principles`), but may require special support in
those packages.


:class:`~ncdata.NcAttribute`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Represents an attribute, with name and value.  The value is always a either a scalar
or a 1-D numpy array -- this is enforced as a computed property (read and write).

Attribute Data Arrays
"""""""""""""""""""""


Correctness and Consistency
---------------------------
In practice, to support flexibility in construction and manipulation, it is simply
impractical to require that ncdata structures represent valid netCDF data structures at
all times, since this makes it cumbersome to make structural changes.
For example, you could not extract a group from a dataset which refers to a dimension
*outside* the group.

Thus, it is an inevitable possibility that ncdata structures represent *invalid* netCDF
data, for example circular references, missing dimensions or naming mismatches.
Effectively there are a set of data validity rules, which are summarised in the
:func:`ncdata.utils.save_errors` routine.

In practice, there is a minimum set of requirements for creating ncdata objects, and
additional requirements for when ncdata is converted to actual netCDF.  For example,
variables can be initially created with no data.  But if subsequently written to a file,
data must be assigned first.

.. Note::
  These issues are not necessarily fully resolved.  Caution required !


Components, Containers and Names
--------------------------------
Each dimension, variable, attribute or group normally exists as a component in a
parent dataset (or group), where it is stored in the relevant parent object's container
property, i.e. either ``.dimensions``, ``.variables``, ``.attributes`` or ``.groups``.

These properties all have the type of the :class:`~ncdata._core.NameMap` class, which
is a dictionary type mapping a string (name) to a specific core data class type.

Each core object also has a ``.name`` property.  By this, it is implicit that you
**could** have a difference between the name by which the object is indexed in the
container it lives in, and its own ``.name``.  This is to be avoided !
The :meth:`~ncdata.NameMap` container class is provided mostly to make this smoother :
the convenience methods such as :meth:`~ncdata.NameMap.add` and
:meth:`~ncdata.NameMap.rename` should help.


Core Object Constructors
------------------------
The ``__init__`` methods of the core classes are designed to make in-line definition of
new objects in user code reasonably legible.  So, when initialising one of the container
properties, the utility method :meth:`ncdata.NameMap.from_items` enables you to pass a
pre-created or existing container, or similar dictionary-like object :

.. code-block:: python

    >>> ds1 = NcData(groups={
    ...    'x':NcData('x'),
    ...    'y':NcData('y')
    ... })
    >>> print(ds1)
    <NcData: <'no-name'>
        groups:
            <NcData: x
            >
            <NcData: y
            >
    >

or **more usefully**, just a *list* of suitable data objects, like this...

.. code-block:: python

    >>> ds2 = NcData(
    ...    variables=[
    ...        NcVariable('v1', ('x',), data=[1,2]),
    ...        NcVariable('v2', ('x',), data=[2,3])
    ...    ]
    ... )
    >>> print(ds2)
    <NcData: <'no-name'>
        variables:
            <NcVariable(int64): v1(x)>
            <NcVariable(int64): v2(x)>
    >

Or, in the **special case of attributes**, a regular dictionary of ``name: value`` form
will be automatically converted to a NameMap of ``name: NcAttribute(name: value)`` :

.. code-block:: python

    >>> var = NcVariable(
    ...    'v3',
    ...    attributes={'x':'this', 'b':1.4, 'arr': [1, 2, 3]}
    ... )
    >>> print(var)
    <NcVariable(<no-dtype>): v3()
        v3:x = 'this'
        v3:b = 1.4,
        v3:arr = array([1, 2, 3])
    >


Relationship to File Storage
----------------------------
Note that file-specific storage aspects, such as chunking, data-paths or compression
strategies, are not recorded in the core objects.  However, array representations in
variable and attribute data (notably dask lazy arrays) may hold such information.
The concept of "unlimited" dimensions is arguably an exception.  However, this is a
core provision in the NetCDF data model itself (see "Dimension" in the `NetCDF Classic Data Model`_).

.. _NetCDF Classic Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#classic_model
