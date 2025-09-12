Utilities and Conveniences
==========================
This section provide a short overview of various more involved operations which are
provided in the :mod:`~ncdata.utils` module.  In all cases, more detail is available in
the `API pages <../../details/api/ncdata.utils.html>`_

Rename Dimensions
-----------------
The :func:`~ncdata.utils.rename_dimension` utility does this, in a way which ensures a
safe and consistent result.

Dataset Equality Testing
------------------------
The function :func:`~ncdata.utils.dataset_differences` produces a list of messages
detailing all the ways in which two datasets are different.

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

.. note::
   To compare isolated variables, a subsidiary routine
   :func:`~ncdata.utils.variable_differences` is also provided.

Sub-indexing
------------
A new dataset can be derived by indexing over dimensions, analagous to sub-indexing
an array.  This operation indexes all the variables appropriately, to produce a new
independent dataset which is complete and self-consistent.

The function :func:`~ncdata.utils.index_by_dimensions` provides indexing where the
indices are passed as arguments or keywords for the specific dimensions.

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

    >>> subdata = index_by_dimensions(data, y=2, x=slice(None, 4))
    >>> print(subdata)
    <NcData: <'no-name'>
        dimensions:
            x = 4
    <BLANKLINE>
        variables:
            <NcVariable(int64): v1(x)>
    >
    >>> print(subdata.variables["v1"].data)
    [20 21 22 23]

Slicing syntax
^^^^^^^^^^^^^^
The :class:`~ncdata.utils.Slicer` class is provided to enable the same operation to be
expressed using multi-dimensional slicing syntax.

So for example, the above is more neatly expressed like this ...

.. testsetup::

    >>> from ncdata.utils import Slicer

.. doctest::

    >>> data_slicer = Slicer(data, ["y", "x"])
    >>> subdata2 = data_slicer[2, :4]

.. doctest::

    >>> dataset_differences(subdata, subdata2) == []
    True


Consistency Checking
--------------------
The :func:`~ncdata.utils.save_errors` function provides a general
correctness-and-consistency check.

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


See : :ref:`correctness-checks`


Data Copying
------------
The :func:`~ncdata.utils.ncdata_copy` makes structural copies of datasets.
However, this can be easily be accessed as :meth:`ncdata.NcData.copy`, which is the same
operation.

See: :ref:`copy_notes`