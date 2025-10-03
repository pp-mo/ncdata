How-To Questions
================
Short goal-focussed descriptions of how to achieve specific things.
These are mostly presented as example code snippets, but also link to other
documentation to describe concepts and technical details.

**"Why Not Just..."** sections highlight warnings for what *not* to do,
i.e. wrong turns and gotchas, with brief descriptions of why.

.. testsetup::

    >>> import xarray
    >>> import iris
    >>> iris.FUTURE.save_split_attrs = True
    >>> import pathlib
    >>> from pprint import pprint
    >>> import numpy as np
    >>> from subprocess import check_output
    >>> def ncdump(path):
    ...     text = check_output(f'ncdump -h {path}', shell=True).decode()
    ...     text = text.replace("\t", " " * 3)
    ...     print(text)


.. _howto_access:

Access a variable, dimension, attribute or group
------------------------------------------------
Index by component names to get the object which represents a particular element.

.. doctest:: python

    >>> from ncdata import NcData, NcAttribute, NcDimension, NcVariable
    >>> data = NcData(
    ...   dimensions=[NcDimension("x", 3)],
    ...   variables=[NcVariable("vx", attributes={"units": "m.s-1", "q": 0})],
    ...   attributes={"experiment": "A301.7"}
    ... )
    ...
    >>> data.attributes["experiment"]
    NcAttribute('experiment', 'A301.7')
    >>> data.dimensions["x"]
    NcDimension('x', 3)
    >>> data.variables['vx'].attributes['units']
    NcAttribute('units', 'm.s-1')

Variable, attributes, dimensions and sub-groups are all stored by name like this,
in a parent property which is a "component container" dictionary.

.. Note::
    It is usually easier and more convenient to access attributes via the ``.avals``
    rather than the ``.attributes``.

    For example:

    .. doctest:: python

        >>> data.avals["experiment"]
        'A301.7'

    See: :ref:`attributes_and_avals`


.. Warning::

    The :attr:`~ncdata.NcVariable.dimensions` property of a :class:`~ncdata.NcVariable`
    is different : it is *not* a dictionary of :class:`~ncdata.NcDimension` objects,
    but just a *list of dimension names*.


.. _howto_add_something:

Add a variable, dimension, attribute or group
---------------------------------------------
Use the :meth:`~ncdata.NameMap.add` method of a component-container property to insert
a new item.

    >>> data.dimensions.add(NcDimension("y", 5))
    >>> data.dimensions
    {'x': NcDimension('x', 3), 'y': NcDimension('y', 5)}

The item must be of the correct type, in this case a :class:`~ncdata.NcDimension`.
If not, an error will be raised.

.. Warning::

    **Why Not Just...** ``data.dimensions["y"] = NcDimension("y", 5)`` ?

    This does actually work, but the user must ensure that the dictionary key always
    matches the name of the component added.  Using :meth:`~ncdata.NameMap.add` is thus
    safe, and actually *simpler*, since all components have a definite name anyway.


.. _howto_remove_something:

Remove a variable, dimension, attribute or group
------------------------------------------------
The standard Python ``del`` operator can be applied to a component property to remove
something by its name.

    >>> data.dimensions
    {'x': NcDimension('x', 3), 'y': NcDimension('y', 5)}

    >>> del data.dimensions['y']
    >>> data.dimensions
    {'x': NcDimension('x', 3)}


.. _howto_rename_something:

Rename a variable, attribute or group
-------------------------------------
Use the :meth:`~ncdata.NameMap.rename` method to rename a component.

.. doctest:: python

    >>> data2 = NcData(variables=[NcVariable("xx")])
    >>> data2.variables
    {'xx': <ncdata._core.NcVariable object at ...>}
    >>> data2.variables.rename('xx', 'qqqq')
    >>> data2.variables
    {'qqqq': <ncdata._core.NcVariable object at ...>}

Note that this affects both the element's container key *and* its ``.name``.


.. Warning::

    **Why Not Just...** ``var = data.variables['x']; var.name = "q"`` ?

    This would break the expected ``key == elements[key].name`` rule.
    We don't prevent this, but it is usually a mistake.
    :func:`~ncdata.utils.save_errors` detects this type of problem.

.. Warning::

    Renaming a **dimension** can cause particular problems, so must be done with care.
    See :ref:`howto_rename_dimension`.


.. _howto_rename_dimension:

Rename a dimension
------------------
Simply using ``ncdata.dimensions.rename()`` can cause problems, because you must then
**also** replace the name where it occurs in the dimensions of any variables.

Instead, you should use the :func:`~ncdata.utils.rename_dimension` function, which does
this correctly.

For example:

.. doctest:: python

    >>> from ncdata.utils import rename_dimension
    >>> ncdata = NcData(
    ...     dimensions=[NcDimension("x", 3), NcDimension("y", 4)],
    ...     variables=[NcVariable("vy", ["y"]), NcVariable("vzyx", ["z", "y", "x"])]
    ... )
    >>> print(ncdata)
    <NcData: <'no-name'>
        dimensions:
            x = 3
            y = 4
    <BLANKLINE>
        variables:
            <NcVariable(<no-dtype>): vy(y)>
            <NcVariable(<no-dtype>): vzyx(z, y, x)>
    >

    >>> rename_dimension(ncdata, "y", "qqq")
    >>> print(ncdata)
    <NcData: <'no-name'>
        dimensions:
            x = 3
            qqq = 4
    <BLANKLINE>
        variables:
            <NcVariable(<no-dtype>): vy(qqq)>
            <NcVariable(<no-dtype>): vzyx(z, qqq, x)>
    >


.. _howto_read_attr:

Read an attribute value
-----------------------
To get an attribute of a dataset, group or variable, fetch it from the
:meth:`ncdata.NcData.avals` or :meth:`ncdata.NcVariable.avals`.

This returns either a single (scalar) number, a numeric array, or a string.

.. doctest:: python

    >>> var = NcVariable("x", attributes={"a": [3.0], "levels": [1., 2, 3]})
    >>> var.avals["a"]
    array(3.)

    >>> dataset = NcData(variables=[var], attributes={"a": "seven"})
    >>> print(dataset.avals["a"])
    seven
    >>> print(dataset.avals.get("context"))
    None
    >>> dataset.variables["x"].avals["levels"]
    array([1., 2., 3.])

**Given an isolated** :class:`ncdata.NcAttribute` **instance** :

Its value is best read with the :meth:`ncdata.NcAttribute.as_python_value` method,
which produces the same results as the above.

    >>> print(var.attributes["a"].as_python_value())
    3.0


.. Warning::

    **Why Not Just...** use ``NcAttribute.value`` ?

    For example

    .. doctest:: python

        >>> print(var.attributes["a"].value)
        [3.]

    The ``.value`` is always stored as a :class:`~numpy.ndarray` array (never a scalar),
    but this is not how it is stored in netCDF.  The ``get_python_value()`` returns the
    attribute as a straightforward value, compatible with what is seen in ``ncdump``
    output, and results from the ``netCDF4`` module.


.. _howto_write_attr:

Change an attribute value
-------------------------
To set an attribute of a dataset, group or variable, use the
:meth:`ncdata.NcData.avals`.

All attributes are writeable, and the type can be freely changed.

.. doctest:: python

    >>> var.avals["x"] = 3.
    >>> print(var.avals["x"])
    3.0

    >>> print(var.attributes["x"])
    NcAttribute('x', 3.0)
    >>> var.avals["x"] = "string-value"
    >>> print(var.attributes["x"])
    NcAttribute('x', 'string-value')
    >>> var.avals["x"]
    'string-value'

**Or** if you already have an attribute object in hand, you can simply set
``attribute.value`` directly : this a property with controlled access, so the
assigned value is cast with :func:`numpy.asarray`.

For example

.. doctest:: python

    >>> attr = data.variables["vx"].attributes["q"]
    >>> attr.value = 4.2
    >>> print(attr.value)
    4.2
    >>> attr.value
    array(4.2)

.. _howto_create_attr:

Create an attribute
-------------------
To create an attribute on a dataset, group or variable, just set its value in the
:data:`ncdata.NcData.avals` dictionary.
This works just like :ref:`howto_write_attr` : i.e. it makes no difference whether the
attribute already exists or not.

.. doctest:: python

    >>> print(var.avals.get("xx"))
    None
    >>> var.avals["xx"] = 3.
    >>> print(var.avals["xx"])
    3.0

.. Note::

    Assigning attributes when *creating* a dataset, variable or group is somewhat
    simpler, discussed :ref:`here <object_creation>`.


.. _howto_create_variable:

Create a variable
-----------------
Use the :meth:`NcVariable() <ncdata.NcVariable.__init__>` constructor to create a new
variable with a name, dimensions, and optional data and attributes.

A minimal example:

.. doctest:: python

    >>> var = NcVariable("data")
    >>> print(var)
    <NcVariable(<no-dtype>): data()>
    >>> print(var.data)
    None
    >>>

A more rounded example, including a data array:

.. doctest:: python

    >>> var = NcVariable("vyx", ("y", "x"),
    ...   data=[[1, 2, 3], [0, 1, 1]],
    ...   attributes={'a': 1, 'b': 'setting=off'}
    ... )
    >>> print(var)
    <NcVariable(int64): vyx(y, x)
        vyx:a = 1
        vyx:b = 'setting=off'
    >
    >>> print(var.data)
    [[1 2 3]
     [0 1 1]]
    >>>



.. _howto_access_vardata:

Read or write variable data
---------------------------
The :attr:`~ncdata.NcVariable.data` property of a :class:`~ncdata.NcVariable` usually
holds a data array.

.. doctest:: python

    >>> var.data = np.array([1, 2])
    >>> var.data
    array([1, 2])

This may be either a :class:`numpy.ndarray` (real) or a :class:`dask.array.Array`
(lazy) array.  If the data is converted from another source (file, iris or xarray),
it is usually lazy.

It can be freely overwritten by the user.

.. Warning::

    If not ``None``, the ``.data`` should **always** be an array of the correct shape.

    The :func:`~ncdata.utils.save_errors` function checks that all variables have
    valid dimensions, and that ``.data`` arrays match the dimensions.


.. _howto_copy:

Make a copy of data
-------------------
Use the :meth:`ncdata.NcData.copy` method to make a copy.

.. doctest::

    >>> data2 = data.copy()
    >>> data == data2
    True

Note that this creates all-new independent ncdata objects, but all variable data arrays
will be linked to the originals (to avoid making copies).

See: :ref:`copy_notes`

.. _howto_slice:

Extract a subsection by indexing
--------------------------------
The nicest way is usually to use the NcData :meth:`~ncdata.Ncdata.slicer` method to
specify dimensions to index, and then index the result.

.. testsetup::

    >>> from ncdata import NcData, NcDimension
    >>> from ncdata.utils import Slicer
    >>> full_data = NcData(dimensions=[NcDimension("x", 7), NcDimension("y", 6)])
    >>> for nn, dim in full_data.dimensions.items():
    ...    full_data.variables.add(NcVariable(nn, dimensions=[nn], data=np.arange(dim.size)))

.. doctest::

    >>> data_region = full_data.slicer("y", "x")[3, 1::2]

effect:

.. doctest::

    >>> for dimname in full_data.dimensions:
    ...     print("(original)", dimname, ':', full_data.variables[dimname].data)
    (original) x : [0 1 2 3 4 5 6]
    (original) y : [0 1 2 3 4 5]

    >>> for dimname in data_region.dimensions:
    ...     print("(new)", dimname, ':', data_region.variables[dimname].data)
    (new) x : [1 3 5]

You can also slice data directly, which simply acts on the dimensions in order:

.. doctest::

    >>> data_region_2 = full_data[1::2, 3]
    >>> data_region_2 == data_region
    True

See: :ref:`utils_indexing`


Read data from a NetCDF file
----------------------------
Use the :func:`ncdata.netcdf4.from_nc4` function to load a dataset from a netCDF file.

.. testsetup::

    >>> _ds = NcData(
    ...     dimensions=[NcDimension("time", 10)],
    ...     variables=[NcVariable("time", ["time"], data=np.arange(10, dtype=int))],
    ... )
    ...
    >>> from ncdata.netcdf4 import to_nc4
    >>> filepath = "_t1.nc"
    >>> to_nc4(_ds, filepath)


.. doctest:: python

    >>> from ncdata.netcdf4 import from_nc4
    >>> ds = from_nc4(filepath)
    >>> print(ds)
    <NcData: /
        dimensions:
            time = 10
    <BLANKLINE>
        variables:
            <NcVariable(int64): time(time)>
    >


Control chunking in a netCDF read
---------------------------------
Use the ``dim_chunks`` argument in the :func:`ncdata.netcdf4.from_nc4` function

.. doctest:: python

    >>> from ncdata.netcdf4 import from_nc4
    >>> ds = from_nc4(filepath, dim_chunks={"time": 3})
    >>> print(ds.variables["time"].data.chunks)
    ((3, 3, 3, 1),)


Save data to a new file
-----------------------
Use the :func:`ncdata.netcdf4.to_nc4` function to write data to a file:

.. doctest:: python

    >>> from ncdata.netcdf4 import to_nc4
    >>> to_nc4(data, filepath)
    >>> ncdump(filepath)  # utility which calls 'ncdump' command (not shown)
    netcdf ...{
    dimensions:
       x = 3 ;
    variables:
       double vx ;
          vx:units = "m.s-1" ;
          vx:q = 4.2 ;
    <BLANKLINE>
    // global attributes:
          :experiment = "A301.7" ;
    }
    <BLANKLINE>

Read from or write to Iris cubes
--------------------------------
Use :func:`ncdata.iris.to_iris` and :func:`ncdata.iris.from_iris`.

.. doctest:: python

    >>> from ncdata.iris import from_iris, to_iris

    >>> cubes = iris.load(filepath)
    >>> print(cubes)
    0: vx / (m.s-1)                        (scalar cube)

    >>> ncdata = from_iris(cubes)
    >>> print(ncdata)
    <NcData: <'no-name'>
        variables:
            <NcVariable(float64): vx()
                vx:units = 'm.s-1'
                vx:q = 4.2
            >
    <BLANKLINE>
        global attributes:
            :Conventions = 'CF-1.7'
            :experiment = 'A301.7'
    >

    >>> ncdata.variables.rename("vx", "vxxx")
    >>> cubes2 = to_iris(ncdata)
    >>> print(cubes2)
    0: vxxx / (m.s-1)                      (scalar cube)

Note that:

* :func:`ncdata.iris.to_iris` calls :func:`iris.load`
* :func:`ncdata.iris.from_iris` calls :func:`iris.save`

Extra kwargs are passed on to the iris load/save routine.

Since an :class:`~ncdata.NcData` is like a complete file, or dataset, it is written to
or read from multiple cubes, in a :class:`~iris.cube.CubeList`.


Read from or write to Xarray datasets
-------------------------------------
Use :func:`ncdata.xarray.to_xarray` and :func:`ncdata.xarray.from_xarray`.

.. doctest:: python

    >>> from ncdata.xarray import from_xarray, to_xarray
    >>> dataset = xarray.open_dataset(filepath)
    >>> ncdata = from_xarray(dataset)

    >>> print(ncdata)
    <NcData: <'no-name'>
        variables:
            <NcVariable(float64): vx()
                vx:units = 'm.s-1'
                vx:q = 4.2
                vx:_FillValue = nan
            >
    <BLANKLINE>
        global attributes:
            :experiment = 'A301.7'
    >

    >>> ds2 = to_xarray(ncdata)
    >>> print(ds2)
    <xarray.Dataset> Size: 8B
    Dimensions:  ()
    Data variables:
        vx       float64 8B nan
    Attributes:
        experiment:  A301.7

Note that:

* :func:`ncdata.xarray.to_xarray` calls :func:`xarray.Dataset.load_store`.

* :func:`ncdata.xarray.from_xarray` calls :func:`xarray.Dataset.dump_to_store`

Any additional kwargs are passed on to the xarray load/save routine.

An NcData writes or reads as an :class:`xarray.Dataset`.



Convert data directly from Iris to Xarray, or vice versa
--------------------------------------------------------
Use :func:`ncdata.iris_xarray.cubes_to_xarray` and
:func:`ncdata.iris_xarray.cubes_from_xarray`.

.. doctest:: python

    >>> from ncdata.iris_xarray import cubes_from_xarray, cubes_to_xarray
    >>> cubes = iris.load(filepath)
    >>> dataset = cubes_to_xarray(cubes)
    >>>
    >>> cubes2 = cubes_from_xarray(dataset)

These functions are simply a convenient shorthand for combined use of
:func:`ncdata.xarray.from_xarray` then :func:`ncdata.iris.to_iris`,
or :func:`ncdata.iris.from_iris` then :func:`ncdata.xarray.to_xarray`.

Extra keyword controls for the relevant iris and xarray load and save routines can be
passed using specific dictionary keywords, e.g.

.. doctest:: python

    >>> cubes = cubes_from_xarray(
    ...   dataset,
    ...   iris_load_kwargs={'constraints': 'air_temperature'},
    ...   xr_save_kwargs={'unlimited_dims': ('time',)},
    ... )


Combine data from different input files into one output
-------------------------------------------------------
This can be easily done by pasting elements from two sources into one output dataset.

You can freely modify a loaded dataset, since it is no longer connected to the input
file.

Just be careful that any shared dimensions match.

.. testsetup:: python

    >>> d1 = NcData(
    ...     dimensions=[NcDimension("x", 3)],
    ...     variables=[NcVariable("DATA1_qqq", ["x"], data=[1, 2, 3])]
    ... )
    >>> d2 = NcData(
    ...     dimensions=[NcDimension("x", 3)],
    ...     variables=[
    ...         NcVariable("x1", ["x"], data=[111, 111, 111]),
    ...         NcVariable("x2", ["x"], data=[222, 222, 222]),
    ...         NcVariable("x3", ["x"], data=np.array([333, 333, 333], dtype=float)),
    ...     ]
    ... )
    >>> to_nc4(d1, "input1.nc")
    >>> to_nc4(d2, "input2.nc")

.. doctest:: python

    >>> from ncdata.netcdf4 import from_nc4, to_nc4
    >>> data1 = from_nc4('input1.nc')
    >>> print(data1)
    <NcData: /
        dimensions:
            x = 3
    <BLANKLINE>
        variables:
            <NcVariable(int64): DATA1_qqq(x)>
    >

    >>> data2 = from_nc4('input2.nc')
    >>> print(data2)
    <NcData: /
        dimensions:
            x = 3
    <BLANKLINE>
        variables:
            <NcVariable(int64): x1(x)>
            <NcVariable(int64): x2(x)>
            <NcVariable(float64): x3(x)>
    >

    >>> # Add some known variables from file2 into file1
    >>> wanted = ('x1', 'x3')
    >>> for name in wanted:
    ...     data1.variables.add(data2.variables[name])
    ...

    >>> # data1 has now been changed
    >>> print(data1)
    <NcData: /
        dimensions:
            x = 3
    <BLANKLINE>
        variables:
            <NcVariable(int64): DATA1_qqq(x)>
            <NcVariable(int64): x1(x)>
            <NcVariable(float64): x3(x)>
    >

    >>> # just check that it also saves ok
    >>> filepath = pathlib.Path('_temp_testdata.nc')
    >>> to_nc4(data1, filepath)
    >>> filepath.exists()
    True

Create a brand-new dataset
--------------------------
Use the :meth:`NcData() <~ncdata.NcData.__init__>` constructor to create a new dataset.

Contents and components can be attached on creation ...

.. doctest:: python

    >>> data = NcData(
    ...     dimensions=[NcDimension("y", 2), NcDimension("x", 3)],
    ...     variables=[
    ...         NcVariable("y", ("y",), data=list(range(2))),
    ...         NcVariable("x", ("x",), data=list(range(3))),
    ...         NcVariable(
    ...             "vyx", ("y", "x"),
    ...             data=np.zeros((2, 3)),
    ...             attributes={
    ...                 "long_name": "rate",
    ...                 "units": "m s-1"
    ...             }
    ...         )],
    ...     attributes={"history": "imaginary", "test_a1": 1, "test_a2": [2, 3]}
    ... )
    >>> print(data)
    <NcData: <'no-name'>
        dimensions:
            y = 2
            x = 3
    <BLANKLINE>
        variables:
            <NcVariable(int64): y(y)>
            <NcVariable(int64): x(x)>
            <NcVariable(float64): vyx(y, x)
                vyx:long_name = 'rate'
                vyx:units = 'm s-1'
            >
    <BLANKLINE>
        global attributes:
            :history = 'imaginary'
            :test_a1 = 1
            :test_a2 = array([2, 3])
    >

Or, they can be added iteratively ...

.. doctest:: python

    >>> data2 = NcData()
    >>> ny, nx = 2, 3
    >>> data2.dimensions.add(NcDimension("y", ny))
    >>> data2.dimensions.add(NcDimension("x", nx))
    >>> data2.variables.add(NcVariable("y", ["y"], data=[0, 1]))
    >>> data2.variables.add(NcVariable("x", ["x"], data=[0, 1, 2]))
    >>> data2.variables.add(NcVariable("vyx", ("y", "x"), dtype=float))
    >>> vx, vy, vyx = [data2.variables[k] for k in ("x", "y", "vyx")]
    >>> vx.data = np.arange(nx)
    >>> vy.data = np.arange(ny)
    >>> vyx.data = np.zeros((ny, nx))
    >>> vyx.avals["long_name"] = "rate"
    >>> vyx.avals["units"] = "m s-1"
    >>> for k, v in [("history", "imaginary"), ("test_a1", 1), ("test_a2", [2, 3])]:
    ...     data2.avals[k] = v
    ...

In fact, there should be NO difference between these two.

.. doctest:: python

    >>> data == data2
    True


Remove or rewrite specific attributes
-------------------------------------
Load an input dataset with :func:`ncdata.netcdf4.from_nc4`.

Then you can modify, add or remove global and variable attributes at will,
and re-save as required.

For example :

.. testsetup:: python

    >>> # Save the above complex data-example
    >>> to_nc4(data, "test_data.nc")

.. doctest:: python

    >>> from ncdata.netcdf4 import from_nc4, to_nc4
    >>> ds = from_nc4('test_data.nc')
    >>> history = ds.avals.get("history", "")
    >>> ds.avals["history"] = history + ": modified to SPEC-FIX.A"
    >>> removes = ("test_a1", "review")
    >>> for name in removes:
    ...     if name in ds.attributes:
    ...         del ds.attributes[name]
    ...
    >>> for var in ds.variables.values():
    ...     if "coords" in var.attributes:
    ...         var.avals.rename("coords", "coordinates")  # common non-CF problem
    ...     units = var.avals.get("units")
    ...     if units and units == "ppm":
    ...         var.avals["units"] = "1.e-6"  # another common non-CF problem
    ...
    >>> to_nc4(ds, "output_fixed.nc")


Save selected variables to a new file
-------------------------------------
Load an input dataset with :func:`ncdata.netcdf4.from_nc4`; make a new empty dataset
with :class:`~ncdata.NcData`\ ();  use ``dataset.dimensions.add()``,
``dataset.variables.add()`` and similar to add/copy selected elements into it; then
save it with :func:`ncdata.netcdf4.to_nc4`.

For a simple case with no groups, it could look something like this:

.. testsetup:: python

    >>> ds = from_nc4("_temp_testdata.nc")
    >>> ds.variables.add(NcVariable("z", data=[2.]))
    >>> to_nc4(ds, "testfile.nc")
    >>> input_filepath = "_testdata_plus.nc"
    >>> to_nc4(ds, input_filepath)
    >>> output_filepath = pathlib.Path("tmp.nc")

.. doctest:: python

    >>> ds_in = from_nc4(input_filepath)
    >>> ds_out = NcData()
    >>> wanted = ['DATA1_qqq', 'x3', 'z']
    >>> for varname in wanted:
    ...     var = ds_in.variables[varname]
    ...     ds_out.variables.add(var)
    ...     for dimname in var.dimensions:
    ...         if dimname not in ds_out.dimensions:
    ...             ds_out.dimensions.add(ds_in.dimensions[dimname])
    ...
    >>> assert "x" in ds_out.dimensions
    >>> assert all(name in ds_out.variables for name in wanted)

    >>> # Also, just check that it saves OK
    >>> to_nc4(ds_out, output_filepath)
    >>> output_filepath.exists()
    True

Sometimes it's simpler to load the input, delete content **not** wanted, then re-save.
It's perfectly safe to do that, since the original file will be unaffected.

.. testsetup:: python

    >>> testds = NcData(
    ...     dimensions=[NcDimension("x", 2), NcDimension("pressure", 3)],
    ...     variables=[
    ...         NcVariable("main1", ["x"], data=np.zeros(2)),
    ...         NcVariable("extra1", ["x", "pressure"], data=np.zeros((2, 3))),
    ...         NcVariable("extra2", ["pressure"], data=np.zeros(3)),
    ...         NcVariable("unwanted", data=7),
    ...     ],
    ... )
    >>> to_nc4(testds, input_filepath)

.. doctest:: python

    >>> data = from_nc4(input_filepath)
    >>> for varname in ('extra1', 'extra2', 'unwanted'):
    ...     del data.variables[varname]
    ...
    >>> del data.dimensions['pressure']
    >>> to_nc4(data, output_filepath)


Adjust file content before loading into Iris/Xarray
---------------------------------------------------
Use :func:`~ncdata.netcdf4.from_nc4`, and then :func:`~ncdata.iris.to_iris` or
:func:`~ncdata.xarray.to_xarray`.  You can thus adjust file content at the file level,
to avoid loading problems.

For example, to replace an invalid coordinate name in iris input :

.. doctest:: python

    >>> from ncdata.netcdf4 import from_nc4
    >>> from ncdata.iris import to_iris
    >>> ncdata = from_nc4(input_filepath)
    >>> for var in ncdata.variables.values():
    ...     coords = var.avals.get('coordinates', "")
    ...     if "old_varname" in coords:
    ...         coords.replace("old_varname", "new_varname")
    ...         var.avals["coordinates"] = coords
    ... 
    >>> cubes = to_iris(ncdata)

or, to replace a mis-used special attribute in xarray input  :

.. doctest:: python

    >>> from ncdata.netcdf4 import from_nc4
    >>> from ncdata.xarray import to_xarray
    >>> ncdata = from_nc4(input_filepath)
    >>> for var in ncdata.variables.values():
    ...     if "_fillvalue" in var.attributes:
    ...         var.attributes.rename("_fillvalue", "_FillValue")
    ... 
    >>> cubes = to_iris(ncdata)


Adjust Iris/Xarray save output before writing to a file
-------------------------------------------------------
Use :func:`~ncdata.iris.from_iris` or :func:`~ncdata.xarray.from_xarray`, and then
:func:`~ncdata.netcdf4.to_nc4`.  You can thus make changes to the saved output which
would be difficult to overcome if first written to an actual file.

For example, to force an additional unlimited dimension in iris output :

.. testsetup:: python

    >>> from iris.cube import Cube
    >>> from iris.coords import DimCoord
    >>> co_x = DimCoord(np.arange(5.), long_name="x")
    >>> co_t = DimCoord(np.arange(10.), long_name="timestep", units="days since 2010-05-01")
    >>> cube = Cube(np.zeros((10, 5)), dim_coords_and_dims=[(co_t, 0), (co_x, 1)])
    >>> cubes = [cube]

    >>> # Also build a test xarray dataset.  Cheat and use ncdata, to_xarray ?
    >>> data = np.arange(10.)
    >>> data[[2, 5]] = np.nan
    >>> var = NcVariable("experiment", ["x"], data=data)
    >>> ds = NcData(dimensions=[NcDimension("x", 10)], variables=[var])
    >>> to_nc4(ds, "__xr_tmp.nc")
    >>> xr_dataset = xarray.open_dataset("__xr_tmp.nc", chunks=-1)

.. doctest:: python

    >>> from ncdata.iris import from_iris
    >>> from ncdata.netcdf4 import to_nc4
    >>> ncdata = from_iris(cubes)
    >>> ncdata.dimensions['timestep'].unlimited = True
    >>> to_nc4(ncdata, "output.nc")

or, to convert xarray data variable output to masked integers :

.. doctest:: python

    >>> from numpy import ma
    >>> from ncdata.xarray import from_xarray
    >>> from ncdata.netcdf4 import to_nc4
    >>> ncdata = from_xarray(xr_dataset)
    >>> var = ncdata.variables['experiment']
    >>> mask = np.isnan(var.data)
    >>> data = var.data.astype(np.int16)
    >>> data[mask] = -9999
    >>> var.data = data
    >>> var.avals["_FillValue"] = -9999
    >>> to_nc4(ncdata, "output.nc")


.. _howto_load_variablewidth_strings:

Load a file containing variable-width string variables
------------------------------------------------------
You must supply a ``dim_chunks`` keyword to the :meth:`ncdata.netcdf4.from_nc4` method,
specifying how to chunk all dimension(s) which the "string" type variable uses.

.. testsetup:: python

    >>> # manufacture a dataset with a "string" variable in it.
    >>> cdl = """
    ... netcdf foo {
    ...     dimensions:
    ...         date = 6 ;
    ...
    ...     variables:
    ...         string date_comments(date) ;
    ...
    ...     data:
    ...         date_comments = "one", "two", "three", "four", "5", "sixteen" ;
    ... }
    ... """
    >>> from iris.tests.stock.netcdf import ncgen_from_cdl
    >>> filepath = "_vlstring_data.nc"
    >>> ncgen_from_cdl(cdl_str=cdl, cdl_path=None, nc_path=filepath)

.. doctest:: python

    >>> from ncdata.netcdf4 import from_nc4
    >>> # This file has a netcdf "string" type variable, with dimensions ('date',).
    >>> # : **don't chunk that dimension**.
    >>> dataset = from_nc4(filepath, dim_chunks={"date": -1})

This is needed to avoid a Dask error like
``"auto-chunking with dtype.itemsize == 0 is not supported, please pass in `chunks`
explicitly."``

When you do this, Dask returns the variable data as a numpy *object* array, containing
Python strings.  You will probably also want to (manually) convert that to something
more tractable, to work with it effectively.

For example, something like this :

.. doctest:: python

    >>> var = dataset.variables['date_comments']
    >>> string_objects = var.data.compute()
    >>> bytes_objects = [string.encode() for string in string_objects]
    >>> maxlen = max([len(bytes) for bytes in bytes_objects])
    >>> maxlen
    7

    >>> # convert to fixed-width char array (a bit awkward because of how bytes index)
    >>> newdata = np.array([[bytes[i:i+1] for i in range(maxlen)] for bytes in bytes_objects])
    >>> print(newdata.shape, newdata.dtype)
    (6, 7) |S1

    >>> # NOTE: variable data dtype *must* be "S1" for intended behaviour
    >>> dataset.dimensions.add(NcDimension('name_strlen', maxlen))
    >>> var.dimensions = var.dimensions + ("name_strlen",)
    >>> var.data = newdata
    >>> # NOTE: at present it is also required to correct .dtype manually.  See issue#114
    >>> var.dtype = newdata.dtype

    >>> # When re-saved, this data loads back OK without a chunk control
    >>> to_nc4(dataset, "tmp.nc")
    >>> readback = from_nc4("tmp.nc")
    >>> print(readback.variables["date_comments"])
    <NcVariable(|S1): date_comments(date, name_strlen)>
