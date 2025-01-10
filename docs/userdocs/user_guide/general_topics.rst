General Topics
==============
Odd discussion topics

.. _data-types:

Data Types (dtypes)
-------------------
:ref:`Variable data <variable-dtypes>` and :ref:`attribute values <attribute-dtypes>`
all use a subset of numpy **dtypes**, compatible with netcdf datatypes.
These are effectively those defined by `netcdf4-python <https://unidata.github.io/netcdf4-python/>`_, and this
therefore also effectively determines what we see in `dask arrays <https://docs.dask.org/en/stable/array.html>`_ .

However, at present ncdata directly supports only the `NetCDF Classic Data Model`_, so
this does not include the user-defined, enumerated or variable-length datatypes.

In practice, the variable-length string datatypes

.. _NetCDF Classic Data Model: https://docs.unidata.ucar.edu/netcdf-c/current/netcdf_data_model.html#classic_model
