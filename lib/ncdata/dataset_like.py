r"""
An adaptor layer allowing an :class:`~ncdata.NcData` to masquerade as a :class:`netCDF4.Dataset` object.

Note:
    This is a low-level interface, exposed publicly for extended experimental uses.
    If you only want to convert **Iris** data to+from :class:`~ncdata.NcData`,
    please use the functions in :mod:`ncdata.iris` instead.

----

These classes contain :class:`~ncdata.NcData` and :class:`~ncdata.NcVariable`\\s, but
emulate the access APIs of a :class:`netCDF4.Dataset` / :class:`netCDF4.Variable`.

This is provided primarily to support a re-use of the :mod:`iris.fileformats.netcdf`
file format load + save, to convert cubes to+from ncdata objects (and hence, especially,
convert Iris :class:`~iris.cube.Cube`\\s to+from an Xarray :class:`~xarray.Dataset`).

Notes
-----
Currently only supports what is required for Iris load/save capability.
It *should* be possible to use these objects with other packages expecting a
:class:`netCDF4.Dataset` object, however the API simulation is far from complete, so
this may need to be extended, in future, to support other such uses.

"""
from typing import Dict, List

import numpy as np

from . import NcAttribute, NcData, NcDimension, NcVariable


class _Nc4DatalikeWithNcattrs:
    # A mixin, shared by Nc4DatasetLike and Nc4VariableLike, which adds netcdf-like
    #  attribute operations 'ncattrs / setncattr / getncattr', *AND* extends the local
    #  objects attribute to those things also
    # N.B. "self._ncdata" is the underlying NcData object : either an NcData or
    #  NcVariable object.

    def ncattrs(self) -> List[str]:
        return list(self._ncdata.attributes.keys())

    def getncattr(self, attr: str):
        attrs = self._ncdata.attributes
        if attr in attrs:
            result = attrs[attr].as_python_value()
        else:
            # Don't allow it to issue a KeyError, as this upsets 'getattr' usage.
            # Raise an AttributeError instead.
            raise AttributeError(attr)
        return result

    def setncattr(self, attr: str, value):
        # TODO: are we sure we need this translation ??
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        # N.B. using the NcAttribute class for storage also ensures/requires that all
        #  attributes are cast as numpy arrays (so have shape, dtype etc).
        self._ncdata.attributes[attr] = NcAttribute(attr, value)

    def __getattr__(self, attr):
        # Extend local object attribute access to the ncattrs of the stored data item
        #  (Unpleasant, but I think the Iris load code requires it).
        return self.getncattr(attr)

    def __setattr__(self, attr, value):
        if attr in self._local_instance_props:
            # N.B. use _local_instance_props to define standard instance attributes, to avoid a
            #  possible endless loop here.
            super().__setattr__(attr, value)
        else:
            # # if not hasattr(self, '_allsetattrs'):
            # #     self._allsetattrs = set()
            # self._allsetattrs.add(attr)
            self.setncattr(attr, value)


class Nc4DatasetLike(_Nc4DatalikeWithNcattrs):
    """
    An object which emulates a :class:`netCDF4.Dataset`.

    It can be both read and written (modified) via its emulated
    :class:`netCDF4.Dataset`-like API.

    The core NcData content, 'self._ncdata', is a :class:`ncdata.NcData`.
    This completely defines the parent object state.
    If not provided on init, a new, empty dataset is created.

    """

    _local_instance_props = ("_ncdata", "variables", "dimensions")

    def __init__(self, ncdata: NcData = None):
        if ncdata is None:
            ncdata = NcData()  # an empty dataset
        #: the contained dataset.  If not provided, a new, empty dataset is created.
        self._ncdata = ncdata
        # N.B. we need to create + store our OWN variables, as they are wrappers for
        #  the underlying NcVariable objects, with different properties.
        self.variables = {
            name: Nc4VariableLike._from_ncvariable(ncvar)
            for name, ncvar in self._ncdata.variables.items()
        }
        self.dimensions = {
            name: Nc4DimensionLike(dim)
            for name, dim in self._ncdata.dimensions.items()
        }

    @property
    def groups(self):  # noqa: D102
        return None  # not supported

    def createDimension(self, dimname: str, size: int):  # noqa: D102
        if dimname in self.dimensions:
            msg = f'creating duplicate dimension "{dimname}".'
            raise ValueError(msg)

        # Create a new actual NcDimension in the contained dataset.
        dim = NcDimension(dimname, size)
        self._ncdata.dimensions[dimname] = dim
        # Create a wrapper for it, install that into self, and return it.
        nc4dim = Nc4DimensionLike(dim)
        self.dimensions[dimname] = nc4dim
        return nc4dim

    def createVariable(
        self,
        varname: str,
        datatype: np.dtype,
        dimensions: List[str] = (),
        **encoding: Dict[str, str],
    ):  # noqa: D102
        if varname in self.variables:
            msg = f'creating duplicate variable "{varname}".'
            raise ValueError(msg)
        # Add a variable into the underlying NcData object.
        ncvar = NcVariable(
            name=varname,
            dimensions=dimensions,
            group=self._ncdata,
        )
        # Note: initially has no data (or attributes), since this is how netCDF4 expects
        #  to do it.
        self._ncdata.variables[varname] = ncvar
        # Create a netCDF4-like "wrapper" variable + install that here.
        nc4var = Nc4VariableLike._from_ncvariable(ncvar, dtype=datatype)
        self.variables[varname] = nc4var
        return nc4var

    def sync(self):  # noqa: D102
        pass

    def close(self):  # noqa: D102
        self.sync()

    @staticmethod
    def filepath() -> str:  # noqa: D102
        #
        # Note: for now, let's just not care about this.
        # we *might* need this to be an optional defined item on an NcData ??
        # .. or, we ight need to store an xarray "encoding" somewhere ?
        # TODO: more thought here ?
        # return self.ncdata.encoding.get("source", "")
        return "<Nc4DatasetLike>"


class Nc4VariableLike(_Nc4DatalikeWithNcattrs):
    """
    An object which contains a :class:`ncdata.NcVariable` and emulates a :class:`netCDF4.Variable`.

    The core NcData content, 'self._ncdata', is a :class:`NcVariable`.
    This completely defines the parent object state.

    """

    _local_instance_props = ("_ncdata", "name", "datatype", "_data_array")

    def __init__(self, ncvar: NcVariable, datatype: np.dtype):  # noqa: D107
        self._ncdata = ncvar
        self.name = ncvar.name
        # Note: datatype must be known at creation, which may be before an actual data
        #  array is assigned on the ncvar.
        self.datatype = np.dtype(datatype)
        if ncvar.data is None:
            # temporary empty data (to support never-written scalar values)
            # NOTE: significantly, does *not* allocate an actual full array in memory
            array = np.zeros(self.shape, self.datatype)
            ncvar.data = array
        self._data_array = ncvar.data

    @classmethod
    def _from_ncvariable(cls, ncvar: NcVariable, dtype: np.dtype = None):
        if dtype is None:
            dtype = ncvar.dtype
        self = cls(
            ncvar=ncvar,
            datatype=dtype,
        )
        return self

    # Label this as an 'emulated' netCDF4.Variable, containing an actual (possibly
    #  lazy) array, which can be directly read/written.
    @property
    def _data_array(self):
        return self._ncdata.data

    @_data_array.setter
    def _data_array(self, data):
        self._ncdata.data = data
        self.datatype = data.dtype

    def group(self):  # noqa: D102
        return self._ncdata.group

    @property
    def dimensions(self) -> List[str]:  # noqa: D102
        return self._ncdata.dimensions

    #
    # "Normal" data access is via indexing.
    # N.B. we do still need to support this, e.g. for DimCoords ?
    #
    def __getitem__(self, keys):  # noqa: D105
        if keys != slice(None):
            raise IndexError(keys)
        if self.ndim == 0:
            return self._ncdata.data
        return self._ncdata.data[keys]

    # The __setitem__ is not required for normal saving.
    # The saver will assign ._data_array instead
    # TODO: might need to support this for future non-Iris usage ?
    #
    # def __setitem__(self, keys, data):
    #     if keys != slice(None):
    #         raise IndexError(keys)
    #     if not hasattr(data, "dtype"):
    #         raise ValueError(f"nonarray assigned as data : {data}")
    #     if not data.shape == self.shape:
    #         msg = (
    #             f"assigned data has wrong shape : "
    #             f"{data.shape} instead of {self.shape}"
    #         )
    #         raise ValueError(msg)
    #     self._ncdata.data = data
    #     self.datatype = data.dtype

    @property
    def dtype(self):  # noqa: D102
        return self.datatype

    @property
    def dims(self):  # noqa: D102
        return self.dimensions

    @property
    def ndim(self):  # noqa: D102
        return len(self.dimensions)

    @property
    def shape(self):  # noqa: D102
        dims = self.group().dimensions
        return tuple(dims[n].size for n in self.dimensions)

    @property
    def size(self):  # noqa: D102
        return np.prod(self.shape)

    def chunking(self):  # noqa: D102
        """
        Return chunk sizes.

        Actual datasets return a list of sizes by dimension, or 'contiguous'.

        For now, simply returns ``None``.  Could be replaced when required.
        """
        return None


class Nc4DimensionLike:
    """
    An object which emulates a :class:`netCDF4.Dimension` object.

    The core NcData content, 'self._ncdata', is a :class:`ncdata.NcDimension`.
    This completely defines the parent object state.

    """

    def __init__(self, ncdim: NcDimension):  # noqa: D107
        self._ncdata = ncdim

    @property
    def name(self):  # noqa: D102
        return self._ncdata.name

    @property
    def size(self):  # noqa: D102
        return self._ncdata.size

    def isunlimited(self):  # noqa: D102
        return self.size == 0

    def group(self):  # noqa: D102
        # Not properly supported ?
        return None
