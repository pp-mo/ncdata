"""
Interface routines for converting data between ncdata and xarray.

Converts :class:`~ncdata.NcData` to and from Xarray :class:`~xarray.Dataset` objects.

This embeds a certain amount of Xarray knowledge (and dependency), hopefully a minimal
amount.  The structure of an NcData object makes it fairly painless.

"""
from pathlib import Path
from typing import AnyStr, Union

import xarray as xr
from xarray.backends import NetCDF4DataStore

from . import NcAttribute, NcData, NcDimension, NcVariable


class _XarrayNcDataStore(NetCDF4DataStore):
    """
    An adapter class presenting ncdata as an xarray datastore.

    Provides a subset of the
    :class:`xarray.common.AbstractWriteableDataStore` interface, and which converts
    to/from a contained :class:`~ncdata.NcData`.

    This requires some knowledge of Xarray, but it is very small.

    This approach originated from @TomekTrzeciak.
    See https://gist.github.com/TomekTrzeciak/b00ff6c9dc301ed6f684990e400d1435
    """

    # This property ensures that variables are adjusted for netCDF4 output
    # (rather than netCDF3) in the call to
    # "xarray.backends.netCDF4_.NetCDF4DataStore.encode_variable".
    # This 'encode_variable' routine is invoked by "self.encode"
    # -- which is actually "xarray.backends.common.WritableCFDataStore.encode".
    format = "NETCDF4"

    def __init__(self, ncdata: NcData = None):
        if ncdata is None:
            ncdata = NcData()
        self.ncdata = ncdata

    def load(self):
        """
        Return Xarray variables + attributes representing the contained 'self.ncdata'.

        Called, indirectly, by :meth:`to_xarray` via
        :meth:`xarray.backends.store.StoreBackendEntrypoint.open_dataset`.
        """
        variables = {}
        for k, v in self.ncdata.variables.items():
            attrs = {
                name: attr.as_python_value()
                for name, attr in v.attributes.items()
            }
            xr_var = xr.Variable(
                v.dimensions, v.data, attrs, getattr(v, "encoding", {})
            )
            variables[k] = xr_var

        attributes = {
            name: attr.as_python_value()
            for name, attr in self.ncdata.attributes.items()
        }
        return variables, attributes

    def store(
        self,
        variables,
        attributes,
        check_encoding_set=frozenset(),
        writer=None,
        unlimited_dims=None,
    ):
        """
        Populate the stored `self.ncdata` from given Xarray variables + attributes.

        Called, indirectly, by :meth:`from_xarray` via
        :meth:`xr.Dataset.dump_to_store`.
        """
        unlimited_dims = unlimited_dims or []
        # Encode the xarray data as-if-for netcdf4 output, so we convert internal forms
        # (such as strings and timedates) to file-relevant forms.
        variables, attributes = self.encode(variables, attributes)

        # Install (global) attributes into self.
        for attrname, v in attributes.items():
            self.ncdata.attributes[attrname] = NcAttribute(attrname, v)

        # Install variables, creating dimensions as we go.
        for varname, var in variables.items():
            if varname in self.ncdata.variables:
                raise ValueError(f'duplicate variable : "{varname}"')

            for dim_name, size in zip(var.dims, var.shape):
                if dim_name in self.ncdata.dimensions:
                    if self.ncdata.dimensions[dim_name].size != size:
                        raise ValueError(
                            f"size mismatch for dimension {dim_name!r}: "
                            f"{self.ncdata.dimensions[dim_name]} != {size}"
                        )
                else:
                    self.ncdata.dimensions[dim_name] = NcDimension(
                        dim_name,
                        size=size,
                        unlimited=dim_name in unlimited_dims,
                    )

            attrs = {
                name: NcAttribute(name, value)
                for name, value in var.attrs.items()
            }

            data = var.data
            nc_var = NcVariable(
                name=varname,
                dimensions=var.dims,
                attributes=attrs,
                data=data,
                group=self.ncdata,
            )
            self.ncdata.variables[varname] = nc_var

    def get_encoding(self):
        return {}

    def close(self):
        pass

    #
    # This interface supports conversion to+from an xarray "Dataset".
    # N.B. using the "AbstractDataStore" interface preserves variable contents, being
    # either real or lazy arrays.
    #
    @classmethod
    def from_xarray(
        cls, dataset_or_file: Union[xr.Dataset, AnyStr, Path], **xr_load_kwargs
    ):
        if not isinstance(dataset_or_file, xr.Dataset):
            # It's a "file" (or pathstring, or Path ?).
            dataset_or_file = xr.load_dataset(
                dataset_or_file, **xr_load_kwargs
            )
        nc_data = cls()
        dataset_or_file.dump_to_store(nc_data, **xr_load_kwargs)
        return nc_data

    def to_xarray(self, **xr_load_kwargs) -> xr.Dataset:
        from xarray.backends.store import StoreBackendEntrypoint

        store_entrypoint = StoreBackendEntrypoint()
        ds = store_entrypoint.open_dataset(self, **xr_load_kwargs)
        return ds


def to_xarray(ncdata: NcData, **xarray_load_kwargs) -> xr.Dataset:
    """
    Convert :class:`~ncdata.NcData` to an xarray :class:`~xarray.Dataset`.

    Parameters
    ----------
    ncdata : NcData
        source data

    kwargs : dict
        additional xarray "load keywords", passed to :meth:`xarray.Dataset.load_store`

    Returns
    -------
    xrds : xarray.Dataset
        converted data in the form of an Xarray :class:`xarray.Dataset`

    """
    return _XarrayNcDataStore(ncdata).to_xarray(**xarray_load_kwargs)


def from_xarray(
    xrds: Union[xr.Dataset, Path, AnyStr], **xarray_save_kwargs
) -> NcData:
    """
    Convert an xarray :class:`xarray.Dataset` to a :class:`NcData`.

    Parameters
    ----------
    xrds : :class:`xarray.Dataset`
        source data

    kwargs : dict
        additional xarray "save keywords", passed to
        :meth:`xarray.Dataset.dump_to_store`

    Returns
    -------
    ncdata : NcData
        data converted to an :class:`~ncdata.NcData`

    """
    return _XarrayNcDataStore.from_xarray(xrds, **xarray_save_kwargs).ncdata
