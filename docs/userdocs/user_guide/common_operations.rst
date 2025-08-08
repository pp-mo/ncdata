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
    ``addall` are not available.


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

Rename
------
A component can be renamed with the :meth:`~ncdata.NameMap.rename` method.  This changes
both the name in the container **and** the component's own name -- it is not recommended
ever to set ``component.name`` directly, as this obviously can become inconsistent.

Example :

.. doctest:: python

    >>> dataset.variables.rename("x", "y")

.. warning::
    Renaming a dimension will not rename references to it (i.e. in variables), which
    obviously may cause problems.
    We may add a utility to do this safely in future.

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


Equality Checking
-----------------
We provide a simple, comprehensive  ``==`` check for :mod:`~ncdata.NcDimension` and
:mod:`~ncdata.NcAttribute` objects, but not at present :mod:`~ncdata.NcVariable` or
:mod:`~ncdata.NcData`.

So, using ``==`` on :mod:`~ncdata.NcVariable` or :mod:`~ncdata.NcData` objects
will only do an identity check -- that is, it tests ``id(A) == id(B)``, or ``A is B``.

However, these objects **can** be properly compared with the dataset comparison
utilities, :func:`ncdata.utils.dataset_differences` and
:func:`ncdata.utils.variable_differences`.  By default, these operations are very
comprehensive and may be very costly for instance comparing large data arrays, but they
also allow more nuanced and controllable checking, e.g. to skip data array comparisons
or ignore variable ordering.


Object Creation
---------------
The constructors should allow reasonably readable inline creation of data.
See here : :ref:`data-constructors`

Ncdata is deliberately not very fussy about 'correctness', since it is not tied to an actual
dataset which must "make sense".   see : :ref:`correctness-checks` .

Hence, there is no great need to install things in the 'right' order (e.g. dimensions
before variables which need them).  You can create objects in one go, like this :

.. doctest:: python

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

.. doctest:: python

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


