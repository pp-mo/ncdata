Core Data Objects
=================
Ncdata uses Python objects to represent netCDF data, and allows the user to freely
inspect and/or modify it, aiming to do this in the most natural and pythonic way.

.. _data-model:

Data Classes
------------
The data model components are elements of the
`NetCDF Classic Data Model`_ , plus **groups** (from the
`Enhanced netCDF data model`_ ).

That is, a Dataset(File) consists of just Dimensions, Variables, Attributes and
Groups.

.. note::
    We are not, as yet, explicitly supporting the NetCDF4 extensions to variable-length
    and user types.  See : :ref:`data-types`

The core ncdata classes representing these Data Model components are
:class:`~ncdata.NcData`, :class:`~ncdata.NcDimension`, :class:`~ncdata.NcVariable` and
:class:`~ncdata.NcAttribute`.

Notes :

* There is no "NcGroup" class : :class:`~ncdata.NcData` is used for both the "group" and
  "dataset" (aka file).

* All data objects have a ``.name`` property, but this can be empty (``None``) when it is not
  contained in a parent object as a component.  See :ref:`components-and-containers`,
  below.


:class:`~ncdata.NcData`
^^^^^^^^^^^^^^^^^^^^^^^
This represents a dataset containing variables, dimensions, attributes and groups.
It is also used to represent groups.

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
all.

A variable has a ``.dtype``, which may be set if creating with no data.
However, at present, after creation ``.data`` and ``.dtype`` can be reassigned and there
is no further checking of any sort.

.. _variable-dtypes:

Variable Data Arrays
""""""""""""""""""""
When a variable does have a ``.data`` property, this will be an array, with at least
the usual ``shape``, ``dtype`` and ``__getitem__`` properties.  In practice we assume
for now that we will always have real (numpy) or lazy (dask) arrays.

When data is exchanged with an actual file, it is simply written if real, and streamed
(via :meth:`dask.array.store`) if lazy.

When data is exchanged with supported data analysis packages (i.e. Iris or Xarray, so
far), these arrays are transferred directly without copying or making duplicates (such
as numpy views).
This is a core principle (see :ref:`design-principles`), but may require special support in
those packages.

See also : :ref:`data-types`

:class:`~ncdata.NcAttribute`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Represents an attribute, with name and value.  The value is always either a scalar
or a 1-D numpy array -- this is enforced as a computed property (read and write).

.. _attribute-dtypes:

Attribute Values
""""""""""""""""
In actual netCDF data, the value of an attribute is effectively limited to a
one-dimensional array of certain valid netCDF types, and one-element arrays are exactly
equivalent to scalar values.

So, the ``.value`` of an :class:`ncdata.NcAttribute` must always be a numpy scalar or
1-dimensional array.  This is checked when creating an attribute, or assigning a new value.

However, it's nearly always simpler to read and write attribute values with the ``.avals``
property:  This converts attribute values to and from Python equivalents.
Notably, string and character values are returned as Python strings, and any length-one
vectors appear as scalar values.

.. attention::
    The correct handling and (future) discrimination of attribute values which are character arrays
    ("char" in netCDF terms) and/or variable-length strings ("string" type) is still to be determined.
    ( We do not yet properly support any variable-length types. )

    For now, we are simply converting **all** string-like attributes by
    :meth:`ncdata.NcAttribute.as_python_value` to python strings.

See also : :ref:`data-types`

.. _correctness-checks:

Correctness and Consistency
---------------------------
In order to allow flexibility in construction and manipulation, it is not practical
for ncdata structures to represent valid netCDF at all times, since this would make
changing things awkward.
For example, if a group refers to a dimension *outside* the group, strict correctness
would not allow you to simply extract it from the dataset, because it is not valid in isolation.
Thus, we do allow ncdata structures to represent *invalid* netCDF data.
For example, circular references, missing dimensions or naming mismatches.

In practice, there are a minimal set of rules which apply when initially creating
ncdata objects, and additional requirements which apply when creating actual netCDF files.
For example, a variable can be initially created with no data.  But if subsequently written
to a file, some data must be defined.

The full set of data validity rules are summarised in the
:func:`ncdata.utils.save_errors` routine.

.. Note::
  These issues are not necessarily all fully resolved.  Caution required !

.. _components-and-containers:

Components, Containers and Names
--------------------------------
Each dimension, variable, attribute or group normally exists as a component in a
parent dataset (or group), where it is stored in a "container" property of the parent,
i.e. either its ``.dimensions``, ``.variables``, ``.attributes`` or ``.groups``.

Each of the "container" properties is a :class:`~ncdata._core.NameMap` object, which
is a dictionary type mapping a string (name) to a specific type of components.
The dictionary ``.keys()`` are a sequence of component names, and its ``.values()`` are
the corresponding contained components.

Every component object also has a ``.name`` property.  By this, it is implicit that you
**could** have a difference between the name by which the object is indexed in its
container, and its ``.name``.  This is to be avoided !

The :meth:`~ncdata.NameMap` container class is provided with convenience methods which
aim to make this easier, such as :meth:`~ncdata.NameMap.add` and
:meth:`~ncdata.NameMap.rename`.

Container methods
^^^^^^^^^^^^^^^^^
The :class:`~ncdata.NameMap` class also provides a variety of manipulation methods,
both normal dictionary operations and some extra ones.

The most notable ones are : ``del``, ``pop``, ``add``, ``addall``, ``rename`` and of
course  ``__setitem__`` .

See :ref:`common_operations` section.

.. _container-ordering:

Container ordering
^^^^^^^^^^^^^^^^^^
The order of elements of a container is technically significant, and does constitute a
potential difference between datasets (or files).

The :meth:`ncdata.NameMap.rename` method preserves the order of an element,
while :meth:`ncdata.NameMap.add` adds the new components at the end.

The :func:`ncdata.utils.dataset_differences` utility provides various keywords allowing
you to ignore ordering in comparisons, when required.

.. _attributes_and_avals:

NcData and NcVariable ".attributes" and ".avals"
---------------------------------------------------
The contents of the ".attributes" property are :class:`~ncdata.NcAttributes` objects,
not attribute *values*.  This is consistent with the other components, and makes handling
of attributes in general easier.

However, for most operations on attributes, it is much easier to use the ``.avals``
property instead.  This accesses *the same attributes*, but in the form of a simple
"name: value" dictionary.

Get attribute value
^^^^^^^^^^^^^^^^^^^
For example, to fetch an attribute you would usually write just :

.. testsetup::

    >>> from ncdata import NcData, NcVariable, NcAttribute
    >>> dataset = NcData(variables=[
    ...     NcVariable("x", attributes={"units": "m"}),
    ... ])


.. doctest:: python

    >>> units1 = dataset.variables["x"].avals["units"]


and **not** :

.. doctest:: python

    >>> # WRONG: this get the NcAttribute object, not its value
    >>> unit = dataset.variables["x"].attributes["units"]

    >>> # WRONG: this returns a character array, not a string
    >>> unit = dataset.variables["x"].attributes["units"].value


Set attribute value
^^^^^^^^^^^^^^^^^^^
Likewise, to **set** a value, you would normally just

.. doctest:: python

    >>> dataset.variables["x"].avals["units"] = "K"

and **not**

.. doctest:: python

    >>> # NOT RECOMMENDED: direct assignment to NcAttribute.value.
    >>> dataset.variables["x"].attributes["units"].value = "K"


``.avals`` as a dictionary
^^^^^^^^^^^^^^^^^^^^^^^^^^
Note also, that as ``.avals`` is a dictionary, you can use standard dictionary
methods such as ``pop``, ``update`` and ``get`` to perform other operations in a
relatively natural, Pythonic way.

.. doctest:: python

    >>> if dataset.avals.get("qq", "") == "this":
    ...     dataset.avals["qq"] += " and that"

    >>> dataset.attributes.update({"experiment": "A407", "expt_run": 704})

.. note::
    The new ``.avals`` property effectively replaces the old
    :meth:`~ncdata.NcData.get_attrval` and :meth:`~ncdata.NcData.set_attrval` methods,
    which are now deprecated and will eventually be removed.


.. _data-constructors:

Core Object Constructors
------------------------
The ``__init__`` methods of the core classes are designed to make in-line definition of
new objects in user code reasonably legible.  So, when initialising one of the container
properties, the keyword/args defining component parts use the utility method
:meth:`ncdata.NameMap.from_items` so that you can specify a group of components in a variety of ways :
either a pre-created container or a similar dictionary-like object :

.. doctest:: python

    >>> from ncdata import NcData, NcVariable
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

.. doctest:: python

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

.. doctest:: python

    >>> var = NcVariable(
    ...    'v3',
    ...    attributes={'x':'this', 'b':1.4, 'arr': [1, 2, 3]}
    ... )
    >>> print(var)
    <NcVariable(<no-dtype>): v3()
        v3:x = 'this'
        v3:b = 1.4
        v3:arr = array([1, 2, 3])
    >


Relationship to File Storage
----------------------------
See :ref:`file-storage`

.. _NetCDF Classic Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#classic_model
.. _Enhanced netCDF data model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#enhanced_model
