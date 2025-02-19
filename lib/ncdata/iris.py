r"""
Interface routines for converting data between ncdata and Iris.

Convert :class:`~ncdata.NcData`\s to and from Iris :class:`~iris.cube.Cube`\s.

"""
#
# NOTE:  This uses the :mod:`ncdata.dataset_like` interface ability to mimic a
# :class:`netCDF4.Dataset` object, which can then be loaded like a file into Iris.
# The Iris netcdf loader now has specific support for loading an open dataset object,
# see : https://github.com/SciTools/iris/pull/5214.
# This means that, hopefully, all we need to know of Iris itself is the load and save,
# though we do specifically target the netcdf format interface.
#

from typing import Any, AnyStr, Dict, Iterable, Union

import iris
import iris.fileformats.netcdf as ifn
from iris.cube import Cube, CubeList

from . import NcData
from .dataset_like import Nc4DatasetLike

__all__ = ["from_iris", "to_iris"]


def to_iris(ncdata: NcData, **iris_load_kwargs: Dict[AnyStr, Any]) -> CubeList:
    """
    Read Iris cubes from an :class:`~ncdata.NcData`.

    Behaves like an Iris 'load' operation.

    Parameters
    ----------
    ncdata : NcData
        object to be loaded, treated as equivalent to a netCDF4 dataset.

    iris_load_kwargs : dict
        extra keywords, passed to :func:`iris.fileformats.netcdf.load_cubes`

    Returns
    -------
    cubes : iris.cube.CubeList
        loaded results
    """
    dslike = Nc4DatasetLike(ncdata)
    cubes = CubeList(ifn.load_cubes(dslike, **iris_load_kwargs))
    return cubes


def from_iris(
    cubes: Union[Cube, Iterable[Cube]], **iris_save_kwargs: Dict[AnyStr, Any]
) -> NcData:
    """
    Create an :class:`~ncdata.NcData` from Iris cubes.

    Behaves like an Iris 'save' operation.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube`, or iterable of Cubes
        cube or cubes to "save" to an NcData object.
    iris_save_kwargs : dict
        additional keys passed to :func:`iris.fileformats.netcdf.save` operation.

    Returns
    -------
    ncdata : NcData
        output data created from saving ``cubes``

    """
    nc4like = Nc4DatasetLike()
    delayed = iris.save(
        cubes,
        nc4like,
        compute=False,  # *required* for save-to-dataset.
        saver=ifn.save,
        **iris_save_kwargs,
    )
    delayed.compute()  # probably a no-op, but for sake of completeness.
    return nc4like._ncdata
