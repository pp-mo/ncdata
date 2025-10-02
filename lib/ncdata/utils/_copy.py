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

    The operation makes fresh copies of all ncdata objects, but does not copy variable
    data arrays.

    See: :ref:`copy_notes`

    Parameters
    ----------
    ncdata
        data to copy

    Returns
    -------
    ncdata
        identical but distinct copy of input

    Notes
    -----
    This operation is now also available as an object method:
    :meth:`~ncdata.NcData.copy`.  For example:

    Syntactically, this is generally more convenient, but the operation is identical.
    For example:

    .. testsetup::

        >>> from ncdata import NcData
        >>> from ncdata.utils import dataset_differences, ncdata_copy
        >>> data = NcData()

    .. doctest::

        >>> data1 = ncdata_copy(data)
        >>> data2 = data.copy()
        >>> dataset_differences(data1, data2) == []
        True

    """
    return NcData(
        name=ncdata.name,
        attributes=_attributes_copy(ncdata.attributes),
        dimensions=[dim.copy() for dim in ncdata.dimensions.values()],
        variables=[var.copy() for var in ncdata.variables.values()],
        groups=[ncdata_copy(group) for group in ncdata.groups.values()],
    )
