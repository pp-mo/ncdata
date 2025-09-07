from numbers import Number
from typing import Any, Iterable, Mapping

import dask.array as da
import numpy as np

from ncdata import NcData


def index_by_dimensions(
    ncdata: NcData,
    *indices: Iterable[Any],
    **dim_index_kwargs: Mapping[str, Any],
) -> NcData:
    r"""
    Index an NcData over dimensions.

    Parameters
    ----------
    ncdata: NcData
        The input data.
    indices: Iterable[Any]
        Indices to apply in order to the ``ncdata.dimensions``.
        E.G. ``index_by_dimensions(data, 4, [2, 3], slice(0, 3))``.
    dim_index_kwargs: Mapping[str, Any]
        Indexing to apply to named dimensions.
        E.G. ``index_by_dimensions(data, x=1)``,
        ``index_by_dimensions(data, time=slice(0, 100), levels=[1,2,5])``.

    Returns
    -------
        A new copy of 'ncdata', with dimensions and all relevant variables sub-indexed.

    Examples
    --------
    .. testsetup::
        >>> from ncdata import NcDimension
        >>> from ncdata.utils import index_by_dimensions
        >>> data = NcData(dimensions=[NcDimension(nn, 10) for nn in ("time", "levels")])

    >>> data1 = index_by_dimensions(data, slice(0, 10))  # equivalent to [:10]
    >>> data2 = index_by_dimensions(data, levels=[1,2,5])
    >>> data3 = index_by_dimensions(data, time=3, levels=slice(2, 10, 3))

    Notes
    -----
    * Where a dimension key is a single value, the dimension will be *removed*.
      This mimics how numpy arrays behave, i.e. the difference between a[1] and a[[1]]
      or a[1:2].

    * Where both a positional argument (\*args)  and a keyword argument (\*\*kwargs)
      apply to the same dimension, the keyword will take precedence.

    * Supported types of index key are: a single number; a slice; a list of indices or
      booleans.  A tuple, or one-dimensional array can also be used in place of a list.

    * Key types **not** supported are: Multi-dimensional arrays; ``Ellipsis``;
      ``np.newaxis`` / ``None``.

    * A :class:`Slicer` provides the same functionality with a slicing syntax.

    See Also
    --------
    :class:`Slicer`
    """
    # Start by copying the input : then modify that in-place
    ncdata = ncdata.copy()
    # Convert *args to **kwargs (i.e. apply dim names)
    kwargs = {
        dim: index for dim, index in zip(ncdata.dimensions.keys(), indices)
    }
    # Combine with **kwargs
    kwargs.update(dim_index_kwargs)
    for dim_name, key in kwargs.items():
        # Dimension names must occur in the ncdata.
        dimension = ncdata.dimensions.get(dim_name)
        if dimension is None:
            raise ValueError(
                f"Dimension {dim_name!r} is not present in 'ncdata'."
            )

        # Specifically error forbidden key types.
        if np.array(key).ndim > 1:
            raise ValueError(
                f"Key for dimension {dim_name!r} is multi-dimensional: {key}. "
                "Multi-dimensional keys are not supported."
            )
        elif key is Ellipsis:
            raise ValueError(
                f'Key for dimension {dim_name!r} is Ellipsis / "...": '
                "Ellipsis is not supported."
            )
        elif key in (np.newaxis, None):
            raise ValueError(
                f"Key for dimension {dim_name!r} is np.newaxis / None: "
                "New-axis is not supported. "
            )

        # A single value removes the dimension.
        remove_dim = isinstance(key, Number)

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
    .. testsetup::
        >>> from ncdata import NcDimension
        >>> from ncdata.utils import index_by_dimensions
        >>> data = NcData(dimensions=[NcDimension(nn, 10) for nn in ("time", "levels", "X")])

    >>> data1 = Slicer(data)[:3, 1:4]

    >>> data2 = Slicer(data, "time")[:3]

    >>> ds = Slicer(data, ['levels', 'time'])
    >>> data3 = ds[:10, :2]
    >>> data4 = ds[1, :, [1,2,4]]

    Notes
    -----
    * A Slicer contains the original `ncdata` and presents it in a "sliceable" form.
      Indexing it returns a new NcData, so the original data is unchanged.  The Slicer
      is also unchanged and can be reused.

    * :meth:`index_by_dimensions` provides the same functionality in a different form.
      See there for more exact details of the operation.

    See Also
    --------
    :meth:`index_by_dimensions`
    """

    def __init__(
        self, ncdata: NcData, dimensions: str | list[str] | None = None
    ):
        """
        Create an indexer for an NcData, applying to specific dimensions.

        This can then be indexed to produce a derived (sub-indexed) dataset.

        Parameters
        ----------
        ncdata: NcData
            Input data to be sliced.
        dimensions: str | list[str] | None
            If not ``None``, specifies one or more dimension names to which successive
            index keys will be applied.  If ``None``, indexes will be applied in the
            order of ``ncdata.dimensions``.

        Notes
        -----
        All remaining dimensions not mentioned in 'dimensions' are added afterwards.
        This generalises the behaviour described for ``dimensions=None``.
        """
        #: data to be indexed.
        self.ncdata = ncdata
        if dimensions is None:
            dimensions = []
        elif isinstance(dimensions, str):
            dimensions = [dimensions]
        # Add all dims *not* specifically mentioned afterwards.
        remaining_dims = [
            dim for dim in ncdata.dimensions.keys() if dim not in dimensions
        ]
        #: dimensions to index, in order.
        self.dim_names = tuple(dimensions + remaining_dims)

    def __getitem__(self, keys) -> NcData:
        """
        Return an indexed portion of self.ncdata.

        Index with 'keys' applied to dimensions in the order ``slicer.dim_names``.
        """
        if not isinstance(keys, tuple):
            # Single key, e.g. 1, slice(None), [2,3,4], array([2,3])
            # N.B. *otherwise* keys is always a tuple
            # A single tuple argument is passed as-is, i.e. interprets as multiple keys
            keys = [keys]

        n_keys = len(keys)
        if len(keys) > len(self.dim_names):
            msg = (
                f"Too many index keys ({n_keys}), for the available dimensions: "
                f"{self.dim_names!r}."
            )
            raise ValueError(msg)

        # NB too *few* keys is not a problem, since 'zip' truncates for us.
        dim_kwargs = {name: key for name, key in zip(self.dim_names, keys)}

        return index_by_dimensions(self.ncdata, **dim_kwargs)
