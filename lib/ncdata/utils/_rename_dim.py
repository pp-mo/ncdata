"""Utility to rename dimensions."""
from ncdata import NcData


def _rename_dims_in_vars(ncdata: NcData, name_from: str, name_to: str) -> None:
    """Rename a dimension in all contained variables which reference it."""
    for var in ncdata.variables.values():
        if name_from in var.dimensions:
            var.dimensions = tuple(
                [
                    name_to if name == name_from else name
                    for name in var.dimensions
                ]
            )

    # Also rename in all sub-groups, expect where the dimension is redefined ("scope hole").
    for grp in ncdata.groups.values():
        if name_from not in grp.dimensions:
            _rename_dims_in_vars(grp, name_from, name_to)


def rename_dimension(ncdata: NcData, name_from: str, name_to: str) -> None:
    """
    Rename a dimension of an :class:`~ncdata.NcData`.

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
    * operation is in-place. To produce a new :class:`~ncdata.NcData` with
      renamed dimension, use :meth:`~ncdata.NcData.copy` first.
    * unlike a simple :class:`~ncdata.NameMap.rename`, this checks whether a dimension
      of the new name already exists, and if so will raise an error.
    """
    if name_to in ncdata.dimensions:
        msg = (
            f"Cannot rename dimension {name_from!r} to {name_to!r} to, "
            f"because a {name_to!r} dimension already exists."
        )
        raise ValueError(msg)
    ncdata.dimensions.rename(name_from, name_to)
    _rename_dims_in_vars(ncdata, name_from, name_to)
