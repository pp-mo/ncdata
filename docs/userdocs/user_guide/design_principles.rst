Purpose and Principles of NcData
================================

Purpose
-------
* represent netcdf data as Python objects, independent of file storage

* allow data to be freely created, modified or adjusted,
  with a Pythonic interface

* allow analysis packages (Iris, Xarray) to exchange data efficiently,
  including lazy data operations and streaming

.. _design-principles:

Design Principles
-----------------
* all data structures are represented as Python objects

* data can be losslessly converted to and from actual NetCDF files

* data structures can be freely manipulated, **independent of data files**

* variables can contain either real (numpy) or lazy (Dask) arrays

* variable data is exchanged directly with Iris/Xarray, with no copying
  or fetching of variable data arrays

  **Note : “lossless, copy-free and lazy-preserving”**.

* lazy arrays are saved to file by Dask 'streaming', allowing transfer of
  variable arrays larger than memory

* Iris and Xarray objects are converted to and from ncdata in the **same** way
  they are read from or written to NetCDF files

* translation between formats is based on conversion to + from ncdata


.. note::

    From the final 2 points : since conversion to+from ncdata is equivalent
    to file i/o, *so is inter-format conversion*

    **E.G.** translation from Iris to Xarray should be equivalent to *saving*
    from Iris to a file, then *loading* that file into Xarray
