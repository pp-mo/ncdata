# Copyright Iris contributors
#
# This file is part of Iris and is released under the LGPL license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
"""
An abstract representation of Netcdf data with groups, variables + attributes,
as provided by the NetCDF "Common Data Model" :
https://docs.unidata.ucar.edu/netcdf-java/5.3/userguide/common_data_model_overview.html

It is also provided with read/write conversion interfaces to Xarray, Iris and netCDF4,
thus acting as an efficient exchange channel between any of those forms.

"""
from ._core import NcAttribute, NcData, NcDimension, NcVariable

__all__ = ["NcAttribute", "NcData", "NcDimension", "NcVariable"]
