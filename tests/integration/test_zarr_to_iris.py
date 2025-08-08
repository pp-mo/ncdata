"""Test conversion of remote and local Zarr store to iris Cube."""
import iris
import xarray as xr
import ncdata
import ncdata.iris_xarray
import zarr


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

    time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)
    zarr_xr = xr.open_dataset(
        zarr_path,
        consolidated=True,
        decode_times=time_coder,
        engine="zarr",
        chunks={},
        backend_kwargs={},
    )
    zarr_xr.unify_chunks()

    conversion_func = ncdata.iris_xarray.cubes_from_xarray
    cubes = conversion_func(zarr_xr)

    assert isinstance(cubes, iris.cube.CubeList)
    assert len(cubes) == 1
    assert cubes[0].has_lazy_data()
