"""Utility to copy NcData objects, but not copying any contained data arrays."""

from ncdata import NameMap, NcAttribute, NcData, NcDimension, NcVariable


def _attributes_copy(attrs: NameMap) -> NameMap:
    return NameMap.from_items(
        [
            NcAttribute(name=attr.name, value=attr.value)
            for attr in attrs.values()
        ],
        item_type=NcAttribute,
    )


def ncdata_copy(ncdata: NcData) -> NcData:
    """
    Return a copy of the data.

    The operation makes fresh copies of all ncdata objects, but does not copy arrays in
    either variable data or attribute values.

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
        attributes=_attributes_copy(ncdata.attributes),
        dimensions=[
            NcDimension(dim.name, size=dim.size, unlimited=dim.unlimited)
            for dim in ncdata.dimensions.values()
        ],
        variables=[
            NcVariable(
                name=var.name,
                dimensions=var.dimensions,
                dtype=var.dtype,
                data=var.data,
                attributes=_attributes_copy(var.attributes),
                group=var.group,
            )
            for var in ncdata.variables.values()
        ],
        groups=[ncdata_copy(group) for group in ncdata.groups.values()],
    )
