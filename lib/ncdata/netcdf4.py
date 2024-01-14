"""
Interface routines for converting data between ncdata and netCDF4.

Converts :class:`ncdata.NcData` to and from :class:`netCDF4.Dataset` objects.

"""
from pathlib import Path
from threading import Lock
from typing import Dict, Optional, Union

import dask.array as da
import netCDF4 as nc
import numpy as np

from . import NcAttribute, NcData, NcDimension, NcVariable

__all__ = ["from_nc4", "to_nc4"]


# The variable arguments which are 'claimed' by the existing to_nc4 code, and
# therefore not valid to appear in the 'var_kwargs' parameter.
_Forbidden_Variable_Kwargs = ["data", "dimensions", "datatype", "fill_value"]


def _to_nc4_group(
    ncdata: NcData,
    nc4object: Union[nc.Dataset, nc.Group],
    var_kwargs: Optional[Dict[str, Dict]] = None,
) -> None:
    """
    Inner routine supporting ``to_nc4``, and recursive calls for sub-groups.

    See :func:``to_nc4`` for details.
    **Except that** : this routine operates only on a dataset/group, does not accept a
    filepath string or Path.
    """
    if var_kwargs is None:
        var_kwargs = {}

    for dimname, dim in ncdata.dimensions.items():
        size = 0 if dim.unlimited else dim.size
        nc4object.createDimension(dimname, size)

    for varname, var in ncdata.variables.items():
        fillattr = "_FillValue"
        if fillattr in var.attributes:
            fill_value = var.attributes[fillattr].value
        else:
            fill_value = None

        kwargs = var_kwargs.get(varname, {})
        forbidden_keys = set(_Forbidden_Variable_Kwargs) & set(kwargs)
        if forbidden_keys:
            msg = (
                f"additional `var_kwargs` for variable {var} included key(s) "
                f"{list(forbidden_keys)!r}, which are disallowed since they are amongst"
                f"those controlled by the ncdata.netcdf interface itself : "
                f"{list(_Forbidden_Variable_Kwargs)!r}."
            )
            raise ValueError(msg)

        nc4var = nc4object.createVariable(
            varname=varname,
            datatype=var.dtype,
            dimensions=var.dimensions,
            fill_value=fill_value,
            **kwargs,
        )
        # As for loading, the ncdata variables must represent actual 'raw' netcdf
        # variables, of the internal data type, i.e. *not* scaled data.
        nc4var.set_auto_maskandscale(False)

        # Assign attributes.
        # N.B. must be done before writing data, to enable scale+offset controls !
        for attrname, attr in var.attributes.items():
            if attrname != "_FillValue":
                nc4var.setncattr(attrname, attr.as_python_value())

        data = var.data
        if hasattr(data, "compute"):
            da.store(data, nc4var)
        else:
            nc4var[:] = data

    for attrname, attr in ncdata.attributes.items():
        nc4object.setncattr(attrname, attr.as_python_value())

    for groupname, group in ncdata.groups.items():
        nc4group = nc4object.createGroup(groupname)
        _to_nc4_group(
            ncdata=group,
            nc4object=nc4group,
            var_kwargs=var_kwargs.get("/" + groupname, {}),
        )


_GLOBAL_NETCDF4_LIBRARY_THREADLOCK = Lock()


class _NetCDFDataProxy:
    """
    A reference to the data payload of a single NetCDF file variable.

    Copied from Iris, with some simplifications.
    """

    __slots__ = ("shape", "dtype", "path", "variable_name", "group_names_path")

    def __init__(
        self, shape, dtype, filepath, variable_name, group_names_path=None
    ):
        self.shape = shape
        self.dtype = dtype
        self.path = filepath
        if group_names_path is None:
            group_names_path = []
        self.group_names_path = group_names_path
        self.variable_name = variable_name

    @property
    def ndim(self):
        return len(self.shape)

    def __getitem__(self, keys):
        # Using a DatasetWrapper causes problems with invalid ID's and the
        #  netCDF4 library, presumably because __getitem__ gets called so many
        #  times by Dask. Use _GLOBAL_NETCDF4_LOCK directly instead.
        with _GLOBAL_NETCDF4_LIBRARY_THREADLOCK:
            dataset = nc.Dataset(self.path)
            # Always yield raw variable data of the declared variable dtype
            # i.e. *not* scaled+offset values (where enabled)
            dataset.set_auto_maskandscale(False)
            ds_or_group = dataset
            try:
                for group_name in self.group_names_path:
                    ds_or_group = ds_or_group.groups[group_name]
                variable = ds_or_group.variables[self.variable_name]
                # Get the NetCDF variable data and slice.
                var = variable[keys]
            finally:
                dataset.close()
        return np.asanyarray(var)

    def __repr__(self):
        fmt = (
            "<{self.__class__.__name__} shape={self.shape}"
            " dtype={self.dtype!r} path={self.path!r}"
            " variable_name={self.variable_name!r}>"
        )
        return fmt.format(self=self)

    def __getstate__(self):
        return {attr: getattr(self, attr) for attr in self.__slots__}

    def __setstate__(self, state):
        for key, value in state.items():
            setattr(self, key, value)


def to_nc4(
    ncdata: NcData,
    nc4_dataset_or_file: Union[nc.Dataset, Path, str],
    var_kwargs: Dict[str, Dict] = None,
) -> None:
    """
    Save NcData to a netCDF file.

    Parameters
    ----------
    ncdata : NcData
        input data
    nc4_dataset_or_file : :class:`netCDF4.Dataset` or :class:`pathlib.Path` or str
        output filepath or :class:`netCDF4.Dataset` to write into
    var_kwargs : dict or None
        additional keys for variable creation.  If present, each entry
        ``var_kwargs[<var_name>]`` is itself a dictionary, containing entries of the
        form ``<kwarg_name>: <kwarg_value>``, which specify additional keyword controls
        passed to :meth:`netCDF4.Dataset.createVariable` for this variable.
        This allows control of e.g. compression or chunking.

        Keyword controls for variables in a sub-group can be given in a
        ``var_kwargs['/<group-name>']`` entry, which is itself a ``var_kwargs`` - like
        dictionary.

        **Note:** this must not include keywords controlled by the ``to_nc4`` operation
        itself.  That is, any of : ["data", "dimensions", "datatype", "fill_value"].

    Returns
    -------
    None

    Notes
    -----
    If a filepath is provided, a file is written and closed afterwards.
    If a dataset is provided, it must be writeable and remains open afterward.

    """
    caller_owns_dataset = hasattr(nc4_dataset_or_file, "variables")
    if caller_owns_dataset:
        nc4ds = nc4_dataset_or_file
    else:
        nc4ds = nc.Dataset(nc4_dataset_or_file, "w")

    try:
        _to_nc4_group(ncdata, nc4ds, var_kwargs=var_kwargs)
    finally:
        if not caller_owns_dataset:
            nc4ds.close()


def _from_nc4_group(
    nc4ds: Union[nc.Dataset, nc.Group],
) -> NcData:
    """
    Inner routine for :func:`from_nc4`.

    See docstring there.
    Provided mainly for recursion into groups, also to keep the dataset open/close separate.
    """
    parent_ds = nc4ds
    group_names_path = []
    while parent_ds.parent is not None:
        group_names_path = [parent_ds.name] + group_names_path
        parent_ds = parent_ds.parent

    ncdata = NcData(name=nc4ds.name)

    for dimname, nc4dim in nc4ds.dimensions.items():
        size = len(nc4dim)
        unlimited = nc4dim.isunlimited()
        ncdata.dimensions[dimname] = NcDimension(dimname, size, unlimited)

    for varname, nc4var in nc4ds.variables.items():
        var = NcVariable(
            name=varname,
            dimensions=nc4var.dimensions,
            dtype=nc4var.dtype,
            group=ncdata,
        )
        ncdata.variables[varname] = var

        # Assign a data object : for now, always LAZY.
        # code shamelessly stolen from iris.fileformats.netcdf

        # Work out the shape of the variable.
        # It may refer to dimensions in enclosing groups.
        group = parent_ds
        dims_map = group.dimensions.copy()
        for group_name in group_names_path:
            # Inner groups take priority, of course :
            # their dimensions mask any of the same name in outer groups
            group = group.groups[group_name]
            dims_map.update(group.dimensions)

        shape = tuple(dims_map[dimname].size for dimname in var.dimensions)

        proxy = _NetCDFDataProxy(
            shape=shape,
            dtype=var.dtype,
            filepath=parent_ds.filepath(),
            variable_name=varname,
            group_names_path=group_names_path,
        )
        var.data = da.from_array(
            proxy, chunks=shape, asarray=True, meta=np.ndarray
        )

        for attrname in nc4var.ncattrs():
            var.attributes[attrname] = NcAttribute(
                attrname, nc4var.getncattr(attrname)
            )

    for attrname in nc4ds.ncattrs():
        ncdata.attributes[attrname] = NcAttribute(
            attrname, nc4ds.getncattr(attrname)
        )

    # And finally, groups -- by the magic of recursion ...
    for group_name, group in nc4ds.groups.items():
        ncdata.groups[group_name] = _from_nc4_group(nc4ds.groups[group_name])

    return ncdata


def from_nc4(
    nc4_dataset_or_file: Union[nc.Dataset, nc.Group, Path, str]
) -> NcData:
    """
    Load NcData from a :class:`netCDF4.Dataset` or netCDF file.

    Parameters
    ----------
    nc4_dataset_or_file
        source of load data.  Can be either a :class:`netCDF4.Dataset`,
        a :class:`netCDF4.Group`, a :class:`pathlib.Path` or a string.

    Returns
    -------
    ncdata : NcData
    """
    caller_owns_dataset = hasattr(nc4_dataset_or_file, "variables")
    if caller_owns_dataset:
        nc4ds = nc4_dataset_or_file
    else:
        nc4ds = nc.Dataset(nc4_dataset_or_file)

    try:
        ncdata = _from_nc4_group(nc4ds)
    finally:
        if not caller_owns_dataset:
            nc4ds.close()

    return ncdata
