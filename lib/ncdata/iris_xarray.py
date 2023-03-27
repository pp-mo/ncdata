"""
Interface routines for converting data between :class:`ncdata.NcData` and
:class:`iris.Cubelist` objects.

"""
import iris
from iris.cube import CubeList
import iris.fileformats.netcdf as ifn

from ncdata.dataset_like import Nc4DatasetLike
from ncdata.xarray import from_xarray as ncdata_from_xarray
from ncdata.xarray import to_xarray as ncdata_to_xarray

#
# The primary conversion interfaces
#


def cubes_from_xarray(xrds: "xarray.Dataset", **xr_load_kwargs):  # noqa
    ncdata = ncdata_from_xarray(xrds, **xr_load_kwargs)
    dslike = Nc4DatasetLike(ncdata)
    cubes = CubeList(ifn.load_cubes(dslike))
    return cubes


def cubes_to_xarray(cubes, iris_save_kwargs=None, xr_save_kwargs=None):
    iris_save_kwargs = iris_save_kwargs or {}
    xr_save_kwargs = xr_save_kwargs or {}
    nc4like = Nc4DatasetLike()
    iris.save(
        cubes, nc4like, saver=iris.fileformats.netcdf.save, **iris_save_kwargs
    )
    xrds = ncdata_to_xarray(nc4like._ncdata, **xr_save_kwargs)
    return xrds
