"""Test conversion of remote and local Zarr store to iris Cube."""
from importlib.resources import files as importlib_files
from pathlib import Path

import iris
import pytest
import xarray as xr
import ncdata
import ncdata.iris_xarray
import zarr


def _return_kwargs():
    time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)
    xr_kwargs = {
            "consolidated": True,
            "decode_times": time_coder,
            "engine": "zarr",
            "chunks": {},
            "backend_kwargs": {},
    }

    return xr_kwargs


def _run_checks(cube):
    """Run some standard checks."""
    assert cube.var_name == "q"
    assert cube.standard_name == "specific_humidity"
    assert cube.long_name is None
    coords = cube.coords()
    coord_names = [coord.standard_name for coord in coords]
    assert "longitude" in coord_names
    assert "latitude" in coord_names


def test_load_zarr2_local():
    """Test loading a Zarr2 store from local FS."""
    zarr_path = (
        Path(importlib_files("tests"))
        / "zarr-sample-data"
        / "example_field_0.zarr2"
    )

    xr_kwargs = _return_kwargs()
    zarr_xr = xr.open_dataset(zarr_path, **xr_kwargs)
    zarr_xr.unify_chunks()

    conversion_func = ncdata.iris_xarray.cubes_from_xarray
    cubes = conversion_func(zarr_xr)

    assert len(cubes) == 1
    cube = cubes[0]
    _run_checks(cube)


def test_load_zarr3_local():
    """Test loading a Zarr3 store from local FS."""
    zarr_path = (
        Path(importlib_files("tests"))
        / "zarr-sample-data"
        / "example_field_0.zarr3"
    )

    xr_kwargs = _return_kwargs()
    zarr_xr = xr.open_dataset(zarr_path, **xr_kwargs)
    zarr_xr.unify_chunks()

    conversion_func = ncdata.iris_xarray.cubes_from_xarray
    cubes = conversion_func(zarr_xr)

    assert len(cubes) == 1
    cube = cubes[0]
    _run_checks(cube)


def test_load_remote_zarr():
    """Test loading a remote Zarr store.

    This is a ~250MB compressed Zarr in an S3 bucket.
    Conversion is done fully lazily, by passing chunks={}
    to Xarray loader. Test takes ~3-4s and needs ~400MB res mem.
    """
    zarr_path = (
        "https://uor-aces-o.s3-ext.jc.rl.ac.uk/"
        "esmvaltool-zarr/pr_Amon_CNRM-ESM2-1_02Kpd-11_r1i1p2f2_gr_200601-220112.zarr3"
    )

    xr_kwargs = _return_kwargs()
    zarr_xr = xr.open_dataset(zarr_path, **xr_kwargs)
    zarr_xr.unify_chunks()

    conversion_func = ncdata.iris_xarray.cubes_from_xarray
    cubes = conversion_func(zarr_xr)

    assert isinstance(cubes, iris.cube.CubeList)
    assert len(cubes) == 1
    assert cubes[0].has_lazy_data()


def test_load_remote_zarr_realized_data():
    """Test with the same remote Zarr store but chunks=None."""
    zarr_path = (
        "https://uor-aces-o.s3-ext.jc.rl.ac.uk/"
        "esmvaltool-zarr/pr_Amon_CNRM-ESM2-1_02Kpd-11_r1i1p2f2_gr_200601-220112.zarr3"
    )

    xr_kwargs = _return_kwargs()
    xr_kwargs["chunks"] = None
    zarr_xr = xr.open_dataset(zarr_path, **xr_kwargs)

    conversion_func = ncdata.iris_xarray.cubes_from_xarray
    msg = (
        "has fully realized data, if you need lazy data, "
        "then add chunks={} as argument to Xarray open_dataset."
    )
    with pytest.warns(UserWarning, match=msg) as w:
        cubes = conversion_func(zarr_xr)
