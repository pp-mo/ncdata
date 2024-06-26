Outstanding Issues
==================

Known Problems
--------------
To be fixed

* in conversion from iris cubes
  with `from_iris <https://ncdata.readthedocs.io/en/latest/api/ncdata.iris.html#ncdata.iris.from_iris>`_

   * use of an `unlimited_dims` key currently causes an exception

   * `issue#43 <https://github.com/pp-mo/ncdata/issues/43>`_

* in conversion to xarray
  with `to_xarray <https://ncdata.readthedocs.io/en/latest/api/ncdata.xarray.html#ncdata.xarray.to_xarray>`_

   * dataset encodings are not reproduced

   * most notably, **the "unlimited_dims" control is missing**

   * `issue#66 <https://github.com/pp-mo/ncdata/issues/66>`_


Identified Design Limitations
-----------------------------

Features unsupported
^^^^^^^^^^^^^^^^^^^^
There are no current plans to address these, but could be considered in future

* user-defined datatypes are not supported

    * i.e. as introduced in NetCDF4

    * notably, includes compound and variable-length types

    * ..and especially **variable-length strings in variables**.
      see : :ref:`string_and_character_data`


Features planned
^^^^^^^^^^^^^^^^
Features not yet implemented, but intended for future releases

   * groups (not yet fully supported ?)

   * file output chunking control

