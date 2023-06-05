"""
Interface routines for converting data between ncdata and netCDF4.

Converts :class:`ncdata.NcData` to and from :class:`netCDF4.Dataset` objects.

"""
from pathlib import Path
from threading import Lock
from typing import Any, AnyStr, Dict, Union

import dask.array as da
import netCDF4 as nc
import numpy as np

from . import NcAttribute, NcData, NcDimension, NcVariable

# The variable arguments that are 'claimed' by the existing to_nc4 code, and
# therefore not valid to appear in the 'var_kwargs' parameter.
_Forbidden_Variable_Kwargs = ["data", "dimensions", "datatype", "_FillValue"]


def _to_group(
    ncdata: NcData,
    nc4object: Union[nc.Dataset, nc.Group],
    var_kwargs: Dict[str, Any],
    in_group_namepath: str,
) -> None:
    """
    Inner routine supporting ``to_nc4``, and recursive calls for sub-groups.

    See :func:``to_nc4`` for details.
    **Except that** : this routine operates only on a dataset/group, does not accept a
    filepath string or Path.
    """
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
        if any(kwarg in _Forbidden_Variable_Kwargs for kwarg in kwargs):
            msg = "additional kwargs for variable "
            raise ValueError(msg)
        nc4var = nc4object.createVariable(
            varname=varname,
            datatype=var.dtype,
            dimensions=var.dimensions,
            fill_value=fill_value,
            **kwargs,
        )

        data = var.data
        if hasattr(data, "compute"):
            da.store(data, nc4var)
        else:
            nc4var[:] = data

        for attrname, attr in var.attributes.items():
            if attrname != "_FillValue":
                nc4var.setncattr(attrname, attr.as_python_value())

    for attrname, attr in ncdata.attributes.items():
        nc4object.setncattr(attrname, attr.as_python_value())

    for groupname, group in ncdata.groups.items():
        nc4group = nc4object.createGroup(groupname)
        _to_group(
            ncdata=group,
            nc4object=nc4group,
            var_kwargs=var_kwargs.get(groupname, {}),
            in_group_namepath=f"{in_group_namepath}/{groupname}",
        )


_GLOBAL_NETCDF4_LIBRARY_THREADLOCK = Lock()


class _NetCDFDataProxy:
    """
    A reference to the data payload of a single NetCDF file variable.

    Copied from Iris, with some simplifications.
    """

    __slots__ = ("shape", "dtype", "path", "variable_name")

    def __init__(self, shape, dtype, path, variable_name):
        self.shape = shape
        self.dtype = dtype
        self.path = path
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
            try:
                variable = dataset.variables[self.variable_name]
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
    nc4_dataset_or_file: Union[nc.Dataset, Path, AnyStr],
    var_kwargs: Dict[str, Any] = None,
) -> None:
    """
    Write an NcData to a provided (writeable) :class:`netCDF4.Dataset`, or filepath.

    Parameters
    ----------
    ncdata : NcData
        input data
    nc4_dataset_or_file : :class:`netCDF4.Dataset` or :class:`pathlib.Path` or str
        output filepath or :class:`netCDF4.Dataset` to write into
    var_kwargs : dict or None
        additional keys for variable creation.  If present, ``var_kwargs[<var_name>]``
        contains additional keywords passed to :meth:`netCDF4.Dataset.createVariable`,
        for specific variables, such as compression or chunking controls.
        Controls for vars within groups are contained within a
        ``var_kwargs['/<group-name>']`` entry, which is itself a dict (recursively).
        Should **not** include any parameters already controlled by the ``to_nc4``
        operation itself, that is : ``varname``, ``datatype``, ``dimensions`` or
        ``fill_value``.

    Returns
    -------
    None

    Note
    ----
    If a filepath is provided, a file is written and closed afterwards.
    If a dataset is provided, it must be writeable and remains open afterward.

    """
    caller_owns_dataset = hasattr(nc4_dataset_or_file, "variables")
    if caller_owns_dataset:
        nc4ds = nc4_dataset_or_file
    else:
        nc4ds = nc.Dataset(nc4_dataset_or_file, "w")

    try:
        _to_group(
            ncdata, nc4ds, var_kwargs=var_kwargs or {}, in_group_namepath=""
        )
    finally:
        if not caller_owns_dataset:
            nc4ds.close()


def from_nc4(
    nc4_dataset_or_file: Union[nc.Dataset, nc.Group, Path, AnyStr]
) -> NcData:
    """
    Read an NcData from a provided :class:`netCDF4.Dataset`, or filepath.

    Parameters
    ----------
    nc4_dataset_or_file
        source of load data.  Can be either a :class:`netCDF4.Dataset`,
        a :class:`netCDF4.Group`, a :class:`pathlib.Path` or a string.

    Returns
    -------
    ncdata : NcData
    """
    ncdata = NcData()
    caller_owns_dataset = hasattr(nc4_dataset_or_file, "variables")
    if caller_owns_dataset:
        nc4ds = nc4_dataset_or_file
    else:
        nc4ds = nc.Dataset(nc4_dataset_or_file)

    try:
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
            shape = tuple(
                ncdata.dimensions[dimname].size for dimname in var.dimensions
            )
            proxy = _NetCDFDataProxy(
                shape=shape,
                dtype=var.dtype,
                path=nc4ds.filepath(),
                variable_name=varname,
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
        for grpname, group in nc4ds.groups.items():
            ncdata.groups[grpname] = from_nc4(nc4ds.groups[grpname])

    finally:
        if not caller_owns_dataset:
            nc4ds.close()

    return ncdata
