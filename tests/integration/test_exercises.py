"""
Temporary : simple tests to exercise the 'ex_' scripts.

This ensures they at least don't crash, though they are not tests themselves
(though they do also use asserts in some cases).

"""


def test_ex_dataset_print():
    from tests.integration.ex_dataset_print import sample_printout

    sample_printout()


def test_ex_iris_saveto_ncdata():
    from tests.integration.ex_iris_saveto_ncdata import (
        example_ncdata_from_iris,
    )

    example_ncdata_from_iris()


def test_ex_iris_xarray_conversion():
    from tests.integration.ex_iris_xarray_conversion import example_from_xr

    example_from_xr()


def test_ex_ncio_loadsave_roundtrip():
    from tests.integration.ex_ncdata_netcdf_conversion import (
        example_nc4_load_save_roundtrip,
    )

    example_nc4_load_save_roundtrip()


def test_ex_ncio_saveload_unlimited_roundtrip():
    from tests.integration.ex_ncdata_netcdf_conversion import (
        example_nc4_save_reload_unlimited_roundtrip,
    )

    example_nc4_save_reload_unlimited_roundtrip()
