from numbers import Number
from typing import Any, List, Mapping, Union

import dask.array as da
from ncdata import NcData
from ncdata.utils import ncdata_copy


def index_by_dimensions(
    ncdata: NcData, **dim_index_kwargs: Mapping[str, Any]
) -> NcData:
    """
    Index an NcData over dimensions.

    Parameters
    ----------
    ncdata
        input data
    dim_index_kwargs
        specify indexing to apply to dimensions.
        E.G. ``x=1``, ``time=slice(0, 100)``, ``levels=[1,2,5]``.

    Returns
    -------
        copy of input with dimensions, and all relevant variables, sub-indexed.

    Notes
    -----
    Where a dimension key is a single value, the dimension will be *removed*.
    This mimics how numpy arrays behave, i.e. the difference between a[1] and a[1:2]

    Examples
    --------
    ncdata = index_by_dimensions(ncdata, time=slice(0, 10))  # equivalent to [:10]
    ncdata = index_by_dimensions(ncdata, levels=[1,2,5])
    ncdata = index_by_dimensions(ncdata, time=3, levels=slice(2, 10, 3))

    See Also
    --------
    :class:`Slicer` provides the same function with a slicing syntax
    """
    # Start by copying the input : then modify that in-place
    ncdata = ncdata_copy(ncdata)
    for dim_name, key in dim_index_kwargs.items():
        # Dimension names must occur in the ncdata.
        dimension = ncdata.dimensions.get(dim_name)
        if dimension is None:
            raise ValueError(
                f"Dimension {dim_name!r} is not present in 'ncdata'."
            )

        # Check for and fail repeated dimensions: the meaning would be unclear (!)
        matches = [name for name in dim_index_kwargs if name == dim_name]
        if len(matches) > 1:
            msg = (
                f"Dimensions to index, {tuple(dim_index_kwargs.keys())}, "
                f"includes dimension {dim_name!r} more than once."
            )
            raise ValueError(msg)

        # Hopefully this replicates how numpy makes this decision?
        remove_dim = isinstance(key, Number)

        # TODO:
        #   Key types must be supported:
        #       * int (or other numeric, including numpy scalars ?)
        #       * list of int
        #       * slice object
        #       * 1-D array of numeric
        #   Key "special" types we could possibly error or convert, to avoid confusion
        #   with numpy behaviours ? :
        #       arrays, tuples, booleans, None, newaxis, ellipsis ...

        # Index the data of all referencing variables
        for var in ncdata.variables.values():
            if dim_name in var.dimensions:
                # construct a list of slice objects
                (i_slicedim,) = [
                    i
                    for i, name in enumerate(var.dimensions)
                    if name == dim_name
                ]
                slices = [slice(None) for dim in var.dimensions]
                slices[i_slicedim] = key

                # index the data
                var.data = var.data[tuple(slices)]

                # also remove the dim, if it will be removed
                if remove_dim:
                    # N.B. can't 'del' a tuple item
                    var.dimensions = tuple(
                        dim for dim in var.dimensions if dim != dim_name
                    )

        # Remove or reduce the dimension itself.
        if remove_dim:
            del ncdata.dimensions[dim_name]
        else:
            # calculate the new dim size, using numpy-like logic
            # TODO: there is probably a better way of calculating this ?
            new_size = da.zeros(dimension.size)[key].shape[0]
            dimension.size = new_size

    return ncdata


class Slicer:
    """
    An object which can index an NcData over its dimensions.

    This wraps the :meth:`index_by_dimensions` method for convenience, returning an
    object which supports the Python extended slicing syntax.

    Examples
    --------
    data = Slicer(ncdata, 'time')[:10]
    data = Slicer(ncdata, 'level')[[1, 2, 5]]
    data = Slicer(ncdata, 'level', 'time', 'x', 'y')[1, :3, 2:10:3, ::-1]
    """

    def __init__(self, ncdata: NcData, dimensions: Union[str, List[str]]):
        """
        Create an indexer for an NcData, applying to specific dimensions.

        This can then be indexed to produce a derived (sub-indexed) dataset.

        Parameters
        ----------
        ncdata
            input data
        dimensions
            one or more dimension names, to which successive index keys will be applied
        """
        self.ncdata = ncdata
        if isinstance(dimensions, str):
            dimensions = [dimensions]
        self.dim_names = tuple(dimensions)

    def __getitem__(self, keys) -> NcData:
        """
        Return an indexed portion of self.ncdata.

        Index with 'keys' in the specified dimensions.
        """
        if not isinstance(keys, tuple):
            # Single key, e.g. 1, slice(None), [2,3,4], array([2,3])
            # N.B. *otherwise* keys is always a tuple
            # A single tuple argument is passed as-is, i.e. interprets as multiple keys
            keys = [keys]

        n_keys = len(keys)
        if len(keys) > len(self.dim_names):
            msg = (
                f"Too many index keys, {n_keys}, for the specified indexing dimension "
                "names, {self.dim_names!r}."
            )
            raise ValueError(msg)

        # NB too *few* keys is not a problem, since 'zip' truncates for us.
        dim_kwargs = {name: key for name, key in zip(self.dim_names, keys)}

        return index_by_dimensions(self.ncdata, **dim_kwargs)
