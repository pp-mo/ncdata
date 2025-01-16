How-To Questions
================
Short goal-focussed descriptions of how to achieve specific things.
These are mostly presented as example code snippets, but also link to other
documentation to describe concepts and technical details.

**"Why Not Just..."** sections highlight warnings for what *not* to do,
i.e. wrong turns and gotchas, with brief descriptions of why.


.. _howto_access:

Access a data object
--------------------
Index by component names to get the object which represents a particular element.

.. code-block:: python

    >>> dataset.attributes["experiment"]
    NcAttribute("'experiment', 'A301.7')
    >>> dataset.dimensions["x"]
    NcDimension('x', 3)
    >>> dataset.variables['vx'].attributes['units']
    NcAttribute("'unit', 'm s-1')

Variable, attributes, dimensions and sub-groups are all stored by name like this,
in a parent property which is a "component container" dictionary.

.. Warning::

    The :attr:`~ncdata.NcVariable.dimensions` property of a :class:`~ncdata.NcVariable`
    is different : it is *not* a dictionary of :class:`~ncdata.NcDimension` objects,
    but just a *list of dimension names*.


.. _howto_add_something:

Add a data object
-----------------
Use the :meth:`~ncdata.NameMap.add` method of a component-container property to insert
a new item.

    >>> data.dimensions.add(NcDimension("y", 4))
    >>> data.dimensions
    {'x': NcDimension('x', 3) 'y': NcDimension('y', 3)}

The item must be of the correct type, in this case a :class:`~ncdata.NcDimension`.
If not, an error will be raised.

.. Warning::

    **Why Not Just...** ``data.dimensions["y"] = NcDimension("y", 4)`` ?

    This does actually work, but the user must ensure that the dictionary key always
    matches the name of the component added.  Using :meth:`~ncdata.NameMap.add` is thus
    safe, and actually *simpler*, since all components have a definite name anyway.


.. _howto_remove_something:

Remove a data object
--------------------
The standard Python ``del`` operator can be applied to a component property to remove
something by its name.

    >>> data.dimensions
    {'x': NcDimension('x', 3) 'y': NcDimension('y', 3)}
    >>> del data.dimensions['x']
    >>> data.dimensions
    {'y': NcDimension('y', 3)}


.. _howto_rename_something:

Rename a data object
--------------------
Use the :meth:`~ncdata.NameMap.rename` method to rename a component.

.. code-block::

    >>> data.dimensions
    {'x': NcDimension('x', 3) 'y': NcDimension('y', 3)}
    >>> data.dimensions.rename['x', 'q']
    >>> data.dimensions
    {'q': NcDimension('q', 3) 'y': NcDimension('y', 3)}

Note that this affects both the element's container key *and* its ``.name``.


.. Warning::

    Renaming a **dimension** can cause problems, so must be done with care.
    See :ref:`howto_rename_dimension`.

.. Warning::

    **Why Not Just...** ``dim = data.dimensions['x']; dim.name = "q"`` ?

    This would break the expected ``key == elements[key].name`` rule.
    We don't prevent this, but it is usually a mistake.
    :func:`~ncdata.utils.save_errors` detects this type of problem.


.. _howto_rename_dimension:

Rename a dimension
------------------
Simply using ``ncdata.dimensions.rename()`` can cause problems, because you must then
**also** replace the name where it occurs in the dimensions of any variables.

.. Note::

    **To-Do** : there should be a utility for this, but as yet it does not exist.
    See `Issue#87 <https://github.com/pp-mo/ncdata/issues/87>`_.


.. _howto_read_attr:

Read an attribute value
-----------------------
To get an attribute of a dataset, group or variable, use the
:meth:`ncdata.NcData.get_attrval` or :meth:`ncdata.NcVariable.get_attrval`
method, which returns either a single (scalar) number, a numeric array, or a string.

.. code-block:: python

    >>> variable.get_attr("x")
    3.0
    >>> dataset.get_attr("context")
    "Results from experiment A301.7"
    >>> dataset.variables["q"].get_attr("level_settings")
    [1.0, 2.5, 3.7]

**Given an isolated** :class:`ncdata.NcAttribute` **instance** :

Its value is best read with the :meth:`ncdata.NcAttribute.get_python_value` method,
which produces the same results as the above.

    >>> variable.attributes[myname].get_python_value()
    3.0

.. Note::

    **Why Not Just...** use ``NcAttribute.value`` ?

    For example

    .. code-block:: python

        >>> data.variables["x"].attributes["q"].value
        [1]

    The ``.value`` is always stored as a :class:`~numpy.ndarray` array, but this is not
    how it is stored in netCDF.  The ``get_python_value()`` returns the attribute
    as a straightforward value, compatible with what is seen in ``ncdump`` output,
    and results from the ``netCDF4`` module.


.. _howto_write_attr:

Change an attribute value
-------------------------
To set an attribute of a dataset, group or variable, use the
:meth:`ncdata.NcData.set_attrval` or :meth:`ncdata.NcVariable.set_attrval` method.

All attributes are writeable, and the type can be freely changed.

.. code-block:: python

    >>> variable.set_attr("x", 3.)
    >>> variable.get_attr("x")
    3.0
    >>> variable.set_attr("x", "string-value")
    >>> variable.get_attr("x")
    "string-value"

.. Note::

    **Why Not Just...** set ``NcAttribute.value`` directly ?

    For example

    .. code-block:: python

        >>> data.variables["x"].attributes["q"].value = 4.2

    This is generally unwise, because the ``.value`` should always be a numpy
    :class:`~numpy.ndarray` array, with a suitable ``dtype``, but the
    :class:`~ncdata.Ncattribute` type does not currently enforce this.
    The ``set_attrval`` method both converts for convenience, and ensures that the
    value is stored in a valid form.


.. _howto_create_attr:

Create an attribute
-------------------
To create an attribute on a dataset, group or variable, just set its value with the
:meth:`ncdata.NcData.set_attrval` or :meth:`ncdata.NcVariable.set_attrval` method.
This works just like :ref:`howto_write_attr` : i.e. it makes no difference whether the
attribute already exists or not.

.. code-block:: python

    >>> variable.set_attr("x", 3.)

.. Note::

    Assigning attributes when *creating* a dataset, variable or group is somewhat
    simpler, discussed :ref:`here <todo>`.


.. _howto_create_variable:

Create a variable
-----------------
Use the :meth:`NcVariable() <ncdata.NcVariable.__init__>` constructor to create a new
variable with a name, dimensions, and optional data and attributes.

A minimal example:

.. code-block:: python

    >>> var = NcVariable("data", ("x_axis",))
    >>> print(var)
    <NcVariable(<no-dtype>): data(x_axis)>
    >>> print(var.data)
    None
    >>>

A more rounded example, including a data array:

.. code-block:: python

    >>> var = NcVariable("vyx", ("y", "x"),
    ...   data=[[1, 2, 3], [0, 1, 1]],
    ...   attributes=[NcAttribute('a', 1), NcAttribute('b', 'setting=off')]
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

.. code-block:: python

    >>> var.data = np.array([1, 2])
    >>> print(var.data)

This may be either a :class:`numpy.ndarray` (real) or a :class:`dask.array.Array`
(lazy) array.  If the data is converted from another source (file, iris or xarray),
it is usually lazy.

It can be freely overwritten by the user.

.. Warning::

    If not ``None``, the ``.data`` should **always** be an array of the correct shape.

    The :func:`~ncdata.utils.save_errors` function checks that all variables have
    valid dimensions, and that ``.data`` arrays match the dimensions.


Read data from a NetCDF file
----------------------------
Use the :func:`ncdata.netcdf4.from_nc4` function to load a dataset from a netCDF file.

.. code-block:: python

    >>> from ncdata.netcdf4 from_nc4
    >>> ds = from_nc4(filepath)
    >>> print(ds)
    <NcData: /
        dimensions:
            time = 10

        variables:
            <NcVariable(int64): x(time)
    >


Control chunking in a netCDF read
---------------------------------
Use the ``dim_chunks`` argument in the :func:`ncdata.netcdf4.from_nc4` function

.. code-block:: python

    >>> from ncdata.netcdf4 from_nc4
    >>> ds = from_nc4(filepath, dim_chunks={"time": 3})
    >>> print(ds.variables["x"].data.chunksize)
    (3,)


Save data to a new file
-----------------------
Use the :func:`ncdata.netcdf4.to_nc4` function to write data to a file:

.. code-block:: python

    >>> from ncdata.netcdf4 import to_nc4
    >>> to_nc4(data, filepath)


Read from or write to Iris cubes
--------------------------------
Use :func:`ncdata.iris.to_iris` and :func:`ncdata.iris.from_iris`.

.. code-block:: python

    >>> from ncdata.iris import from_iris, to_iris
    >>> cubes = iris.load(file)
    >>> ncdata = from_iris(cubes)
    >>>
    >>> cubes2 = to_iris(ncdata)

Note that:

* :func:`ncdata.iris.to_iris` calls :func:`iris.load`
* :func:`ncdata.iris.from_iris` calls :func:`iris.save`

Extra kwargs are passed on to the iris load/save routine.

Since an :class:`~ncdata.NcData` is like a complete file, or dataset, it is written to
or read from multiple cubes, in a :class:`~iris.cube.CubeList`.


Read from or write to Xarray datasets
-------------------------------------
Use :func:`ncdata.xarray.to_xarray` and :func:`ncdata.xarray.from_xarray`.

.. code-block:: python

    >>> from ncdata.xarray import from_xarray, to_xarray
    >>> dataset = xarray.open_dataset(filepath)
    >>> ncdata = from_xarray(dataset)
    >>>
    >>> ds2 = to_xarray(ncdata)

Note that:

* :func:`ncdata.xarray.to_xarray` calls :func:`xarray.Dataset.load_store`.

* :func:`ncdata.xarray.from_xarray` calls :func:`xarray.Dataset.dump_to_store`

Any additional kwargs are passed on to the xarray load/save routine.

An NcData writes or reads as an :class:`xarray.Dataset`.



Convert data directly from Iris to Xarray, or vice versa
--------------------------------------------------------
Use :func:`ncdata.iris_xarray.cubes_to_xarray` and
:func:`ncdata.iris_xarray.cubes_from_xarray`.

.. code-block:: python

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

.. code-block:: python

    >>> cubes = cubes_from_xarray(
    ...   dataset,
    ...   iris_load_kwargs={'constraints': 'air_temperature'},
    ...   xr_save_kwargs={'unlimited_dims': ('time',)},
    ... )
    ...

Combine data from different input files into one output
-------------------------------------------------------
This can be


Create a brand-new dataset
--------------------------
Use the :meth:`NcData() <~ncdata.NcData.__init__>` constructor to create a new dataset.

Contents and components can be attached on creation ...

.. code-block:: python

    >>> data = NcData(
    >>> dimensions=[NcDimension("y", 2), NcDimension("x", 3)],
    >>> variables=[
    >>>     NcVariable("y", ("y",), data=[0, 1]),
    >>>     NcVariable("x", ("x",), data=[0, 1, 2]),
    >>>     NcVariable(
    >>>         "vyx", ("y", "x"),
    >>>         data=np.zeros((2, 3)),
    >>>         attributes=[
    >>>             NcAttribute("long_name", "rate"),
    >>>             NcAttribute("units", "m s-1")
    >>>         ]
    >>>     )],
    >>> attributes=[NcAttribute("history", "imaginary")])
    ...
    >>> print(data)
    <NcData: <'no-name'>
        dimensions:
            y = 2
            x = 3

        variables:
            <NcVariable(int64): y(y)>
    ...

... or added iteratively ...

.. code-block:: python

    >>> data = NcData()
    >>> ny, nx = 2, 3
    >>> data.dimensions.add(NcDimension("y", ny))
    >>> data.dimensions.add(NcDimension("x", nx))
    >>> data.variables.add(NcVariable("y", ("y",)))
    >>> data.variables.add(NcVariable("x", ("x",)))
    >>> data.variables.add(NcVariable("vyx", ("y", "x")))
    >>> vx, vy, vyx = [data.variables[k] for k in ("x", "y", "vyx")]
    >>> vx.data = np.arange(nx)
    >>> vy.data = np.arange(ny)
    >>> vyx.data = np.zeros((ny, nx))
    >>> vyx.set_attrval("long_name", "rate"),
    >>> vyx.set_attrval("units", "m s-1")
    >>> data.set_attrval("history", "imaginary")


Remove or rewrite specific attributes
-------------------------------------


Save selected variables to a new file
-------------------------------------
Load input with :func:`ncdata.netcdf4.from_nc4`; use :meth:`ncdata.NameMap.add` to add
selected elements into a new :class:`ncdata.Ncdata`, and then save it
with :func:`ncdata.netcdf4.to_nc4`.

For a simple case with no groups, it could look something like this:

.. code-block:: python

    >>> input = from_nc4(input_filepath)
    >>> output = NcData()
    >>> for varname in ('data1', 'data2', 'dimx', 'dimy'):
    >>> var = input.variables[varname]
    >>> output.variables.add(var)
    >>> for name in var.dimensions if name not in output.dimensions:
    >>>     output.dimensions.add(input.dimensions[dimname])
    ...
    >>> to_nc4(output, output_filepath)

Sometimes it's simpler to load the input, delete content **not** wanted, then re-save.
It's perfectly safe to do that, since the original file will be unaffected.

.. code-block:: python

    >>> data = from_nc4(input_filepath)
    >>> for name in ('extra1', 'extra2', 'unwanted'):
    >>> del data.variables[varname]
    ...
    >>> del data.dimensions['pressure']
    >>> to_nc4(data, output_filepath)


Adjust file content before loading into Iris/Xarray
---------------------------------------------------
Use :func:`~ncdata.netcdf4.from_nc4`, and then :func:`~ncdata.iris.to_iris` or
:func:`~ncdata.xarray.to_xarray`.  You can thus adjust file content at the file level,
to avoid loading problems.

For example, to replace an invalid coordinate name in iris input :

.. code-block:: python

    >>> from ncdata.netcdf4 import from_nc4
    >>> from ncdata.iris import to_iris
    >>> ncdata = from_nc4(input_filepath)
    >>> for var in ncdata.variables:
    >>> coords = var.attributes.get('coordinates', "")
    >>> if "old_varname" in coords:
    >>>     coords.replace("old_varname", "new_varname")
    >>>     var.set_attrval("coordinates", coords)
    ... 
    >>> cubes = to_iris(ncdata)

or, to replace a mis-used special attribute in xarray input  :

.. code-block:: python

    >>> from ncdata.netcdf4 import from_nc4
    >>> from ncdata.xarray import to_xarray
    >>> ncdata = from_nc4(input_filepath)
    >>> for var in ncdata.variables:
    >>> if "_fillvalue" in var.attributes:
    >>>     var.attributes.rename("_fillvalue", "_FillValue")
    ... 
    >>> cubes = to_iris(ncdata)


Adjust Iris/Xarray save output before writing to a file
-------------------------------------------------------
Use :func:`~ncdata.iris.from_iris` or :func:`~ncdata.xarray.from_xarray`, and then
:func:`~ncdata.netcdf4.to_nc4`.  You can thus make changes to the saved output which
would be difficult to overcome if first written to an actual file.

For example, to force an additional unlimited dimension in iris output :

.. code-block:: python

    >>> from ncdata.iris import from_iris
    >>> from ncdata.netcdf4 import to_nc4
    >>> ncdata = from_iris(cubes)
    >>> ncdata.dimensions['timestep'].unlimited = True
    >>> to_nc4(ncdata, "output.nc")

or, to convert xarray data variable output to masked integers :

.. code-block:: python

    >>> from numpy import ma
    >>> from ncdata.iris import from_xarray
    >>> from ncdata.netcdf4 import to_nc4
    >>> ncdata = from_xarray(dataset)
    >>> var = ncdata.variables['experiment']
    >>> mask = var.data.isnan()
    >>> data = var.data.astype(np.int16)
    >>> data[mask] = -9999
    >>> var.data = data
    >>> var.set_attrval("_FillValue", -9999)
    >>> to_nc4(ncdata, "output.nc")

