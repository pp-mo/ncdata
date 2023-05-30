"""
A proof-of-concept example workflow for :mod:`ncdata.netcdf4`.

Showing loading and saving ncdata to/from netcdf files.
"""
from pathlib import Path
import netCDF4 as nc

import iris.tests as itsts

import numpy as np
from ncdata import NcData, NcDimension, NcVariable, NcAttribute
from ncdata.netcdf4 import from_nc4, to_nc4
from tests.unit.netcdf._compare_nc_files import compare_nc_files


def example_nc4_load_save_roundtrip():  # noqa: D103
    # Load an existing file, save-netcdf4 : check same (with Iris for now)
    filepath = itsts.get_data_path(
        ["NetCDF", "stereographic", "toa_brightness_temperature.nc"]
    )
    ncdata = from_nc4(filepath)
    filepath2 = Path("./temp_nc_output.nc").absolute()
    to_nc4(ncdata, filepath2)

    # Convert to Iris + compare (a bit of a cheat, bit OK for now?)
    import iris

    cube1 = iris.load_cube(filepath)
    cube2 = iris.load_cube(filepath2)
    print("Round-tripped result, as iris cube:")
    print(cube2)
    print("\nold-file-cube == new-file-cube ? ", cube1 == cube2)
    assert cube1 == cube2

    equals_result = compare_nc_files(filepath, filepath2) == []
    print("\nFiles compare? :", equals_result)
    assert equals_result


def example_nc4_save_reload_unlimited_roundtrip():
    ncdata = NcData()
    len_x, len_y = 4, 2
    ncdata.dimensions["dim_x"] = NcDimension("dim_x", len_x, unlimited=True)
    ncdata.dimensions["dim_y"] = NcDimension("dim_y", len_y)
    ncdata.variables["var_x"] = NcVariable(
        "var_x",
        dimensions=["dim_x"],
        dtype=np.float32,
        data=np.arange(4),
        # Just an an attribute for the sake of it.
        attributes={"varattr1": NcAttribute("varattr1", 1)},
    )
    ncdata.attributes["globalattr1"] = NcAttribute("globalattr1", "one")
    print("Source ncdata object:")
    print(ncdata)

    print("")
    filepath = Path("./temp_nc_2_unlim.nc").absolute()
    print("Saving to file ", filepath)
    to_nc4(ncdata, filepath)
    import os

    print("\n\nCreated output:")
    os.system(f"ncdump -h {filepath!s}")
    print("\n")

    ds = nc.Dataset(filepath)
    assert list(ds.dimensions.keys()) == ["dim_x", "dim_y"]
    assert ds.dimensions["dim_x"].isunlimited()

    assert list(ds.variables.keys()) == ["var_x"]
    assert ds.variables["var_x"].ncattrs() == ["varattr1"]

    assert ds.ncattrs() == ["globalattr1"]
    assert ds.getncattr("globalattr1") == "one"
    ds.close()

    # Now readback
    ds_back = from_nc4(filepath)
    print("\nRead-back ncdata from file:")
    print(ds_back)

    assert list(ds_back.dimensions.keys()) == ["dim_x", "dim_y"]
    dimx, dimy = [ds_back.dimensions[name] for name in ("dim_x", "dim_y")]
    assert dimx.size == len_x and dimx.unlimited
    assert dimy.size == len_y and not dimy.unlimited

    assert list(ds_back.variables.keys()) == ["var_x"]
    varx = ds_back.variables["var_x"]

    assert list(varx.attributes.keys()) == ["varattr1"]
    assert varx.attributes["varattr1"].value == 1

    assert list(ds_back.attributes.keys()) == ["globalattr1"]
    assert ds_back.attributes["globalattr1"].value == "one"


if __name__ == "__main__":
    example_nc4_load_save_roundtrip()
    example_nc4_save_reload_unlimited_roundtrip()
