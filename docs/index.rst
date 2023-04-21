.. ncdata documentation master file, created by
   sphinx-quickstart on Thu Apr  6 17:33:47 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ncdata
======
NetCDF data interoperability between Iris and Xarray.

Ncdata exchanges data between Xarray and Iris as efficently as possible

   "lossless, copy-free and lazy-preserving".

This enables the user to freely mix+match operations from both projects, getting the
"best of both worlds".


User Documentation
------------------
For now, we don't yet have documentation beyond the API notes.

* a general project introduction is provide in the project README,
  along with all the current project status information.

  * Please see : `README <https://github.com/pp-mo/ncdata#readme>`_

* Some simple usage examples (scripts) are provided in the codebase.

  * Please see : `Testcode scripts <https://github.com/pp-mo/ncdata/blob/main/lib/tests/integration>`_


API documentation
-----------------

.. toctree::
   :maxdepth: 5

   api/modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
