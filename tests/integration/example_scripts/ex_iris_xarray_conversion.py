"""
A proof-of-concept example workflow for :mod:`ncdata.iris_xarray`.

Showing conversion from Xarray to Iris, and back again.
"""
import iris
import iris.tests as itsts
import numpy as np
import xarray as xr

from ncdata.iris_xarray import cubes_from_xarray, cubes_to_xarray
from tests import testdata_dir


def example_from_xr():  # noqa: D103
    filepath = testdata_dir / "toa_brightness_temperature.nc"
    xrds = xr.open_dataset(filepath, chunks="auto")
    iris.FUTURE.datum_support = True
    print("\nOriginal Xarray dataset:\n", xrds)
    cubes = cubes_from_xarray(xrds)
    print("\nxrds['time']:\n", xrds["time"])
    print("\n\n")
    print("============ CONVERT xr.Dataset TO cubes ... =========\n")
    # print("Cubes:")
    # print(cubes)
    cube = cubes[0]
    print("\nCube:")
    print(cube)

    data = cube.core_data()
    print("\ncube.core_data():")
    print(data)
    # match = data is xrds['data'].data
    # print('\ncube.core_data() is xrds["data"].data:')
    # print(match)
    co_auxlons = cube.coord("longitude")
    print('\ncube.coord("longitude"):')
    print(co_auxlons)
    points = co_auxlons.core_points()
    print('\ncube.coord("longitude").core_points():')
    print(points)
    print('\ncube.coord("longitude").points:')
    print(points.compute())

    print("\n")
    print("============ CONVERT cubes TO xr.Dataset ... =========")
    print("")
    xrds2 = cubes_to_xarray(cubes)
    print("\nxrds2:\n", xrds2)
    print("\ntime:\n", xrds2["time"])

    print("\n")
    print("============ Array identity checks ... =========")

    print(
        "xrds2['data'].data   is   cube.core_data() : ",
        bool(xrds2["data"].data is cube.core_data()),
    )
    assert xrds2["data"].data is cube.core_data()

    print(
        "xrds2['lon'].data   is   cube.coord('longitude').core_points() : ",
        bool(xrds2["lon"].data is cube.coord("longitude").core_points()),
    )
    assert xrds2["lon"].data is cube.coord("longitude").core_points()

    print(
        "xrds2['x'].data   is   cube.coord('projection_x_coordinate').core_points() : ",
        bool(
            xrds2["x"].data
            is cube.coord("projection_x_coordinate").core_points()
        ),
    )
    # NOTE: this one does **not** succeed.
    # TODO: find out exactly why -- ? in some way, because it is a dim coord ?
    # assert xrds2["x"].data is cube.coord("projection_x_coordinate").core_points()

    # NOTE: This part is an actual data content comparison.
    # When comparing actual (lazy) array content, we will often need to take extra
    # measures to ensure thread-safe use of the netcdf library, if data may be fetched
    # (computed) from both Iris and Xarray lazy data arrays **together**.
    # In this case, however, the Iris coordinate ".points" is fetched *first*, so no
    # special care is needed.
    print(
        "np.all(xrds2['x'].data == cube.coord('projection_x_coordinate').points) : ",
        bool(
            np.all(
                xrds2["x"].data == cube.coord("projection_x_coordinate").points
            )
        ),
    )
    assert np.all(
        xrds2["x"].data == cube.coord("projection_x_coordinate").points
    )


if __name__ == "__main__":
    example_from_xr()
