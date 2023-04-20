"""
Interface routines for converting data between :class:`ncdata.NcData` and iterables of
:class:`iris.cube.Cube`\s.

"""
import iris
from iris.cube import CubeList
import iris.fileformats.netcdf as ifn

# from ncdata.dataset_like import Nc4DatasetLike
from .iris import to_iris, from_iris
from ncdata.xarray import from_xarray
from ncdata.xarray import to_xarray

#
# The primary conversion interfaces
#


def cubes_from_xarray(
        xrds: "xarray.Dataset",
        xr_save_kwargs=None, iris_load_kwargs=None
    ) -> CubeList :
    """
    Convert an xarray :class:`xarray.Dataset` to an Iris :class:`iris.cube.CubeList`.
    
    Equivalent to saving the dataset to a netcdf file, and loading that with Iris.

    Netcdf variable data in the output contains the same array objects as the input,
    i.e. arrays (Dask or Numpy) are not copied or computed.  

    Parameters
    ----------
    xrds : :class:`xarray.Dataset`
        input dateset

    xr_save_kwargs : dict
        additional keywords passed to :meth:`xarray.Dataset.dump_to_store`

    iris_load_kwargs : dict
        additional keywords passed to :func:`iris.fileformats.netcdf.load_cubes`

    Returns
    -------
    cubes : :class:`iris.cube.CubeList`
        loaded cubes

    """
    # Ensure kwargs are dicts, for use with '**'
    iris_load_kwargs = iris_load_kwargs or {}
    xr_save_kwargs = xr_save_kwargs or {}
    ncdata = from_xarray(xrds, **xr_save_kwargs)
    cubes = to_iris(ncdata, **iris_load_kwargs)
    return cubes


def cubes_to_xarray(cubes, iris_save_kwargs=None, xr_load_kwargs=None):
    """
    Convert Iris :class:`iris.cube.Cube`\s to an xarray :class:`xarray.Dataset`.

    Equivalent to saving the dataset to a netcdf file, and loading that with Xarray.

    Netcdf variable data in the output contains the same array objects as the input,
    i.e. arrays (Dask or Numpy) are not copied or computed.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube`, or iterable of Cubes.
        source data

    iris_save_kwargs : dict
        additional keywords passed to :func:`iris.save`, and to
        :func:`iris.fileformats.netcdf.saver.save`

    xr_load_kwargs : dict
        additional keywords passed to :meth:`xarray.Dataset.load_store`

    Returns
    -------
    xrds : :class:`xarray.Dataset`
        converted data in the form of an Xarray :class:`xarray.Dataset`

    """
    # Ensure kwargs are dicts, for use with '**'
    iris_save_kwargs = iris_save_kwargs or {}
    xr_load_kwargs = xr_load_kwargs or {}
    ncdata = from_iris(cubes, **iris_save_kwargs)
    xrds = to_xarray(ncdata, **xr_load_kwargs)
    return xrds
