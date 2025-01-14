"""Utility to copy NcData objects, but not copying any contained data arrays."""

from ncdata import NameMap, NcAttribute, NcData


def _attributes_copy(attrs: NameMap) -> NameMap:
    return NameMap.from_items(
        [attr.copy() for attr in attrs.values()],
        item_type=NcAttribute,
    )


def ncdata_copy(ncdata: NcData) -> NcData:
    """
    Return a copy of the data.

    The operation makes fresh copies of all ncdata objects, but does not copy arrays in
    variable data.

    Parameters
    ----------
    ncdata
        data to copy

    Returns
    -------
    ncdata
        identical but distinct copy of input

    """
    return NcData(
        name=ncdata.name,
        attributes=_attributes_copy(ncdata.attributes),
        dimensions=[dim.copy() for dim in ncdata.dimensions.values()],
        variables=[var.copy() for var in ncdata.variables.values()],
        groups=[ncdata_copy(group) for group in ncdata.groups.values()],
    )
