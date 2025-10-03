.. _common_operations:

Common Operations
=================
A group of common operations are available on all the core component types,
i.e. the operations of extract/remove/insert/rename/copy on the ``.dimensions``,
``.variables``, ``.attributes`` and ``.groups`` properties of core objects.

Most of these are hopefully "obvious" Pythonic methods of the container objects.

.. Note::

    The special ``.avals`` property of :class:`NcData` and :class:`NcVariable` also
    provides key common operations associated with ``.attributes``, notably ``rename`` and
    the ``del`` operator.  But not those needing NcAttribute objects -- so ``add`` and
    ``addall`` are not available.


Extract and Remove
------------------
These are implemented as :meth:`~ncdata.NameMap.__delitem__` and :meth:`~ncdata.NameMap.pop`
methods, which work in the usual way.

For Example:

.. testsetup::

    >>> from ncdata import NcData, NcVariable
    >>> dataset = NcData(variables=[NcVariable('x'), NcVariable('y')])
    >>> data = dataset

.. doctest:: python

    >>> var_x = dataset.variables.pop("x")
    >>> del data.variables["y"]

Insert / Add
------------
A new content (component) can be added under its own name with the
:meth:`~ncdata.NameMap.add` method.

Example : ``dataset.variables.add(NcVariable("x", dimensions=["x"], data=my_data))``

:meth:`~ncdata.NcAttribute`s can be treated in the same way, as a :class:`ncdata.NameMap`
component of the parent object.  But it is more usual to add or set attributes
using ``.avals`` rather than ``.attributes``.

Example :

.. testsetup::

    >>> dataset = NcData(variables=[NcVariable("x")])

.. doctest:: python

    >>> dataset.variables["x"].avals["units"] = "m s-1"


There is also an :meth:`~ncdata.NameMap.addall` method, which adds multiple content
objects in one operation.

.. doctest:: python

    >>> vars = [NcVariable(name) for name in ("a", "b", "c")]
    >>> dataset.variables.addall(vars)
    >>> list(dataset.variables)
    ['x', 'a', 'b', 'c']

.. _operations_rename:

Rename
------
A component can be renamed with the :meth:`~ncdata.NameMap.rename` method.  This changes
both the name in the container **and** the component's own name -- it is not recommended
ever to set ``component.name`` directly, as this obviously can become inconsistent.

Example :

.. doctest:: python

    >>> dataset.variables.rename("x", "y")

result:

.. doctest:: python

    >>> print(dataset.variables.get("x"))
    None
    >>> print(dataset.variables.get("y"))
    <NcVariable(<no-dtype>): y()
        y:units = 'm s-1'
    >


.. warning::
    Renaming a dimension will not rename references to it (i.e. in variables), which
    obviously may cause problems.
    The utility function :func:`~ncdata.utils.rename_dimension` is provided for this.
    See : :ref:`howto_rename_dimension`.

.. _copy_notes:

Copying
-------
All core objects support a ``.copy()`` method.  See for instance
:meth:`ncdata.NcData.copy`.

These however do *not* copy variable data arrays (either real or lazy), but produce new
(copied) variables referencing the same arrays.  So, for example:

.. doctest:: python

    >>> # Construct a simple test dataset
    >>> import numpy as np
    >>> from ncdata import NcData, NcDimension, NcVariable
    >>> ds = NcData(
    ...     dimensions=[NcDimension('x', 12)],
    ...     variables=[NcVariable('vx', ['x'], np.ones(12))]
    ... )

    >>> # Make a copy
    >>> ds_copy = ds.copy()

    >>> # The new dataset has a new matching variable with a matching data array
    >>> # The variables are different ..
    >>> ds_copy.variables['vx'] is ds.variables['vx']
    False
    >>> # ... but the arrays are THE SAME ARRAY
    >>> ds_copy.variables['vx'].data is ds.variables['vx'].data
    True

    >>> # So changing one actually CHANGES THE OTHER ...
    >>> ds.variables['vx'].data[6:] = 777
    >>> ds_copy.variables['vx'].data
    array([  1.,   1.,   1.,   1.,   1.,   1., 777., 777., 777., 777., 777.,
           777.])

If needed you can of course replace variable data with copies yourself, since you can
freely assign to ``.data``.
For real data, this is just ``var.data = var.data.copy()``.

There is also a utility function :func:`ncdata.utils.ncdata_copy` :  This is
effectively the same thing as the NcData object :meth:`~ncdata.NcData.copy` method.

.. _equality_testing:

Equality Testing
----------------
We implement equality operations ``==`` / ``!=`` for all the core data objects.

.. doctest::

    >>> vA = dataset.variables["a"]
    >>> vB = dataset.variables["b"]
    >>> vA == vB
    False

.. doctest::

    >>> dataset == dataset.copy()
    True

.. warning::
    Equality testing for :class:`~ncdata.NcData` and :class:`~ncdata.NcVariable` actually
    calls the :func:`ncdata.utils.dataset_differences` and
    :func:`ncdata.utils.variable_differences` utilities.

    This can be very costly if it needs to compare large data arrays.

If you need to avoid comparing large (and possibly lazy) arrays then you can use the
:func:`ncdata.utils.dataset_differences` and
:func:`ncdata.utils.variable_differences` utility functions directly instead.
These provide a ``check_var_data=False`` option, to ignore differences in data content.

See: :ref:`utils_equality`

.. _object_creation:

Object Creation
---------------
The constructors should allow reasonably readable inline creation of data.
See here : :ref:`data-constructors`

Ncdata is deliberately not very fussy about 'correctness', since it is not tied to an actual
dataset which must "make sense".   see : :ref:`correctness-checks` .

Hence, there is no great need to install things in the 'right' order (e.g. dimensions
before variables which need them).  You can create objects in one go, like this :

.. doctest:: python

    >>> data1 = NcData(
    ...     dimensions=[
    ...         NcDimension("y", 2),
    ...         NcDimension("x", 3),
    ...     ],
    ...     variables=[
    ...         NcVariable("y", dimensions=["y"], data=[0, 1]),
    ...         NcVariable("x", dimensions=["x"], data=[0, 1, 2]),
    ...         NcVariable("dd", dimensions=["y", "x"], data=[[0, 1, 2], [3, 4, 5]])
    ...     ]
    ... )
    >>> data1
    <ncdata._core.NcData object at ...>


or iteratively, like this :

.. doctest:: python

    >>> data2 = NcData()
    >>> dims = [("y", 2), ("x", 3)]
    >>> data2.variables.addall([
    ...     NcVariable(name, dimensions=[name], data=np.arange(length))
    ...     for name, length in dims
    ... ])
    >>> data2.variables.add(
    ...     NcVariable("dd", dimensions=["y", "x"],
    ...     data=np.arange(6).reshape(2,3))
    ... )
    >>> data2.dimensions.addall([NcDimension(name, length) for name, length in dims])
    >>> data2
    <ncdata._core.NcData object at ...>

Note : here, the variables were created *before* the dimensions.
The result is the same:

.. doctest:: python

    >>> data1 == data2
    True


