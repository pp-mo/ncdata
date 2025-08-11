"""Utility to rename dimensions."""
from ncdata import NcData

def rename_dimension(ncdata: ncdata, name_from: str, name_to: str):
    """
    Rename a dimension of an :class:`NcData`.

    This includes replacing the name on all contained variables which reference it, including those in sub-groups.

    Parameters
    ----------
    ncdata : NcData
        data with a top-level dimension to rename.

    name_from: str
        existing name of dimension to rename.

    name_to: str
        new name of dimension.

    Notes
    -----
    * operation is in-place. To produce a new :class:`NcData` with renamed dimension, use :meth:`Ncdata.copy` first.
    * unlike a simple :class:`~ncdata.NameMap.rename`, this checks whether a dimension of the new name already exists,
      and if so will raise an error.
    """
    if name_to in ncdata.dimensions:
        msg = (
            f"Cannot rename dimension {name_from!s} to {name_to!s} to, "
            f"because a {name_to!s} dimension aready exists."
        )
        raise ValueError(msg)
