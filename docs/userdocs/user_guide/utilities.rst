Utilities and Conveniences
==========================
This section provide a short overview of various more involved operations which are
provided in the :mod:`~ncdata.utils` module.  In all cases, more detail is available in
the `API pages <../../details/api/ncdata.utils.html>`_

Rename Dimensions
-----------------
The :func:`~ncdata.utils.rename_dimension` utility does this, in a way which ensures a
safe and consistent result.

See: :ref:`operations_rename`


.. _utils_equality:

Dataset Equality Testing
------------------------
The functions :func:`~ncdata.utils.dataset_differences` and
:func:`~ncdata.utils.variable_differences` produce a list of messages detailing all the
ways in which two datasets or variables are different.

For Example:
^^^^^^^^^^^^
.. testsetup::

    >>> from ncdata import NcData, NcDimension, NcVariable
    >>> from ncdata.utils import dataset_differences
    >>> import numpy as np

.. doctest::

    >>> data1 = NcData(
    ...   dimensions=[NcDimension("x", 5)],
    ...   variables=[NcVariable("vx", dimensions=["x"], data=np.arange(5))]
    ... )
    >>> data2 = data1.copy()
    >>> print(dataset_differences(data1, data2))
    []

.. doctest::

    >>> data2.dimensions["x"].unlimited = True
    >>> data2.variables["vx"].data = np.array([1, 3])  # NB must be a *new* array !

.. doctest::

    >>> diffs = dataset_differences(data1, data2)
    >>> for msg in diffs:
    ...    print(msg)
    Dataset "x" dimension has different "unlimited" status : False != True
    Dataset variable "vx" shapes differ : (5,) != (2,)

For a short-form test that two things are the same, you can just check that the
results ``== []``.

By default, these functions compare **everything** about the two arguments.
However, they also have multiple keywords which allow certain *types* of differences to
be ignored, E.G. ``check_dims_order=False``, ``check_var_data=False``.

.. note::
    The ``==`` and ``!=`` operations on  :class:`ncdata.NcData` and
    :class:`ncdata.NcVariable` use these utility functions to check for differences.

    .. warning::
        As they lack a keyword interface, these operations provide no tolerance options,
        so they always check absolutely everything.  Especially, they perform **full
        data-array comparisons**, which can have very high performance costs if data
        arrays are large.

.. _utils_indexing:

Sub-indexing
------------
A new dataset can be derived by indexing over dimensions, analagous to sub-indexing
an array.

This operation indexes all the variables appropriately, to produce a new, independent
dataset which is complete and self-consistent.

The basic indexing operation is provided in three forms:

#. the :func:`~ncdata.utils.index_by_dimensions` function provides the basic operation
#. the :class:`~ncdata.utils.Slicer` objects allow indexing with a slicing syntax
#. the :meth:`ncdata.NcData.slicer` and ``NcData.__getitem__`` methods allow a neater syntax
   for slicing datasets directly

.. note::
    The simplest way is usually to use the :class:`~ncdata.NcData` methods.
    See: :ref:`howto_slice`

Indexing function
^^^^^^^^^^^^^^^^^
The function :func:`~ncdata.utils.index_by_dimensions` provides indexing where the
indices are passed as keywords for each named dimension.

For example:

.. testsetup::

    >>> from ncdata.utils import index_by_dimensions

.. doctest::

    >>> data = NcData(
    ...   dimensions=[NcDimension("y", 4), NcDimension("x", 10)],
    ...   variables=[NcVariable(
    ...      "v1", dimensions=["y", "x"],
    ...      data=np.arange(40).reshape((4, 10))
    ...   )]
    ... )

.. doctest::

    >>> subdata_A = index_by_dimensions(data, x=2)
    >>> print(subdata_A)
    <NcData: <'no-name'>
        dimensions:
            y = 4
    <BLANKLINE>
        variables:
            <NcVariable(int64): v1(y)>
    >
    >>> print(subdata_A.variables["v1"].data)
    [ 2 12 22 32]

    >>> subdata_B = index_by_dimensions(data, y=slice(0, 2), x=[4, 1, 2])
    >>> print(subdata_B)
    <NcData: <'no-name'>
        dimensions:
            y = 2
            x = 3
    <BLANKLINE>
        variables:
            <NcVariable(int64): v1(y, x)>
    >
    >>> print(subdata_B.variables["v1"].data)
    [[ 4  1  2]
     [14 11 12]]


Slicing syntax
^^^^^^^^^^^^^^
The :class:`~ncdata.utils.Slicer` class is provided to enable the same operation to be
expressed using multi-dimensional slicing syntax.

A Slicer is created by specifying an NcData and a list of dimensions, ``Slicer(data, **dim_names)``.

If **no dim-names** are specified, this defaults to all dimensions of the NcData in order,
i.e. ``Slicer(data, list(data.dimensions))``.

A ``Slicer`` object is re-usable, and supports the numpy-like extended slicing syntax,
i.e. keys of the form "a:b:c".

So for example, the above examples are more neatly expressed like this ...

.. testsetup::

    >>> from ncdata.utils import Slicer

.. doctest::

    >>> data_slicer = Slicer(data, "x", "y")
    >>> subdata_A_2 = data_slicer[2]  # equivalent to ibd(data, x=2)
    >>> subdata_B_2 = data_slicer[[4, 1, 2], :2]  # equivalent to ibd(data, x=[4, 1, 2], y=slice(0, 2))

.. doctest::

    >>> subdata_A == subdata_A_2
    True
    >>> subdata_B == subdata_B_2
    True


NcData direct indexing
^^^^^^^^^^^^^^^^^^^^^^
The NcData ``NcData.__getitem__``  and :meth:`~ncdata.NcData.slicer` methods
provide a more concise way of slicing data (which is nevertheless still the same
operation, functionally).

This is explained by the simple equivalences:

    ``data.slicer(*dims)`` === ``Slicer(data, *dims)``

and

    ``data[*keys]`` === ``data.slicer()[*keys]``


So, for example, the above examples can also be written ...

.. doctest::

    >>> subdata_A_3 = data.slicer("x")[2]
    >>> subdata_A_4 = data[:, 2]
    >>> subdata_A_3 == subdata_A_4 == subdata_A
    True

.. doctest::

    >>> subdata_B_3 = data.slicer("x", "y")[[4, 1, 2], :2]
    >>> subdata_B_4 = data[:2, [4, 1, 2]]
    >>> subdata_B_3 == subdata_B_4 == subdata_B
    True


Consistency Checking
--------------------
The :func:`~ncdata.utils.save_errors` function provides a general
correctness-and-consistency check.

See: :ref:`correctness-checks`

For example:

.. testsetup::

    >>> from ncdata.utils import save_errors

.. doctest::

    >>> data_bad = data.copy()
    >>> array = data_bad.variables["v1"].data
    >>> data_bad.variables["v1"].data = array[:2]
    >>> data_bad.variables.add(NcVariable("q", data={"x": 4}))

.. doctest::

    >>> for msg in save_errors(data_bad):
    ...    print(msg)
    Variable 'v1' data shape = (2, 10), does not match that of its dimensions = (4, 10).
    Variable 'q' has a dtype which cannot be saved to netcdf : dtype('O').


Data Copying
------------
The :func:`~ncdata.utils.ncdata_copy` function makes structural copies of datasets.
However, this can now be more easily accessed as :meth:`ncdata.NcData.copy`, which is
the same operation.

See: :ref:`copy_notes`