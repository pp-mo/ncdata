Core Data Objects
=================
Ncdata uses Python objects to represent netCDF data, and allows the user to freely
inspect and/or modify it, aiming to do this is the most natural and pythonic way.

.. _data-model:

Data Classes
------------
The data model components are elements of the
`NetCDF Classic Data Model`_ , plus **groups** (from the 'enhanced' netCDF model).

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
This represents a dataset containing variables, attributes and groups.
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
all.  A variable has a ``.dtype``, which may be set if creating with no data.
However, at present, after creation ``.data`` and ``.dtype`` can be reassigned and there
is no further checking of any sort.

.. _variable-dtypes:

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

See also : :ref:`data-types`

:class:`~ncdata.NcAttribute`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Represents an attribute, with name and value.  The value is always either a scalar
or a 1-D numpy array -- this is enforced as a computed property (read and write).

.. _attribute-dtypes:

Attribute Values
""""""""""""""""
Attribute ``.value`` s are actually numpy arrays, but restricted to one dimension.
They can be written from python values : numbers, strings or sequences, or from numpy
arrays or scalars.  They read back as numpy numeric scalars or arrays, or as strings.

See also : :ref:`data-types`


Correctness and Consistency
---------------------------
In practice, to support flexibility in construction and manipulation, it is
not practical for ncdata structures to represent valid netCDF at
all times, since this would makes changing things awkward.
For example, if a group refers to a dimension *outside* the group, you could not simply
extract it from the dataset because it is not valid in isolation.

Thus, we do allow that ncdata structures represent *invalid* netCDF data.
For example, circular references, missing dimensions or naming mismatches.
Effectively there are a set of data validity rules, which are summarised in the
:func:`ncdata.utils.save_errors` routine.

In practice, there a minimal set of runtime rules for creating ncdata objects, and
additional requirements when ncdata is converted to actual netCDF.  For example,
variables can be initially created with no data.  But if subsequently written to a file,
data must be assigned first.

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
The dictionary``.keys()`` are a sequence of component names, and its ``.values()`` are
the corresponding contained components.

Every component object also has a ``.name`` property.  By this, it is implicit that you
**could** have a difference between the name by which the object is indexed in its
container, and its ``.name``.  This is to be avoided !
The :meth:`~ncdata.NameMap` container class is provided with convenience methods which
aim to make this easier, such as :meth:`~ncdata.NameMap.add` and
:meth:`~ncdata.NameMap.rename`.

NcData and NcVariable ".attributes" components
----------------------------------------------
Note that the contents of a ".attributes" are :class:`~ncdata.NcAttributes` objects,
not attribute values.
Thus to fetch an attribute you might write, for example one of these :

.. code-block::

    units1 = dataset.variables['var1'].get_attrval('units')
    units1 = dataset.variables['var1'].attributes['units'].as_python_value()

but **not** ``unit = dataset.variables['x'].attributes['attr1']``
or  ``unit = dataset.variables['x'].attributes['attr1']``

or, likewise, to set values, one of

.. code-block::

    dataset.variables['var1'].set_attrval('units', "K")
    dataset.variables['var1'].attributes['units'] = NcAttribute("units", K)

but **not** ``dataset.variables['x'].attributes['units'].value = "K"``


Component ordering
^^^^^^^^^^^^^^^^^^
The order of elements of a container is technically significant, and does constitute a
potential difference between datasets (or files).  The
:meth:`ncdata.NameMap.rename` method preserves the order of an element,
while :meth:`ncdata.NameMap.add` adds the new components at the end.
The :func:`ncdata.utils.dataset_differences` utility provides various keywords allowing
you to ignore ordering in comparisons, when required.

Other :class:`~ncdata.NameMap` methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The :class:`~ncdata.NameMap` class also provides


Core Object Constructors
------------------------
The ``__init__`` methods of the core classes are designed to make in-line definition of
new objects in user code reasonably legible.  So, when initialising one of the container
properties, the keyword/args defining component parts use the utility method
:meth:`ncdata.NameMap.from_items` so that you can specify a group of components in a variety of ways :
either a pre-created container or a similar dictionary-like object :

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
