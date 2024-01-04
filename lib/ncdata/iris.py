r"""
Interface routines for converting data between ncdata and Iris.

Convert :class:`~ncdata.NcData` to and from Iris :class:`~iris.cube.Cube`\\s.

This uses the :class:`ncdata.dataset_like` interface ability to mimic netCDF4.Dataset
objects, which are used like files to load and save Iris data.
This means that all we need to know of Iris is its netcdf load+save interfaces.

"""
from typing import AnyStr, Dict, Iterable, Union

import iris
import iris.fileformats.netcdf as ifn
from iris.cube import Cube, CubeList

from . import NcData
from .dataset_like import Nc4DatasetLike

__all__ = ["from_iris", "to_iris"]

#
# The primary conversion interfaces
#


def to_iris(ncdata: NcData, **kwargs) -> CubeList:
    """
    Read Iris cubes from an :class:`~ncdata.NcData`.

    Behaves like an Iris 'load' operation.

    Parameters
    ----------
    ncdata : NcData
        object to be loaded, treated as equivalent to a netCDF4 dataset.

    kwargs : dict
        extra keywords, passed to :func:`iris.fileformats.netcdf.load_cubes`

    Returns
    -------
    cubes : CubeList
        loaded results
    """
    dslike = Nc4DatasetLike(ncdata)
    cubes = CubeList(ifn.load_cubes(dslike, **kwargs))
    return cubes


def from_iris(
    cubes: Union[Cube, Iterable[Cube]], **kwargs: Dict[AnyStr, AnyStr]
) -> NcData:
    """
    Create an :class:`~ncdata.NcData` from Iris cubes.

    Behaves like an Iris 'save' operation.

    Parameters
    ----------
    cubes : :class:`iris.cube.Cube`, or iterable of Cubes
        cube or cubes to "save" to an NcData object.
    kwargs : dict
        additional keys passed to :func:`iris.save` operation.

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
        **kwargs,
    )
    delayed.compute()  # probably a no-op, but for sake of completeness.
    return nc4like._ncdata
