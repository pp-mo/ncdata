"""
A proof-of-concept example workflow for :func:`ncdata.iris.from_iris`.

Check that conversion succeeds and print the resulting dataset.
"""
import iris
import iris.tests as itsts

from ncdata.iris import from_iris


def example_ncdata_from_iris():
    print("")
    print("==============")
    print("TEMPORARY: iris save-to-ncdata test")
    iris.FUTURE.datum_support = True
    filepath = itsts.get_data_path(
        ["NetCDF", "stereographic", "toa_brightness_temperature.nc"]
    )
    cubes = iris.load(filepath)
    ds = from_iris(cubes)
    # save to file
    print(ds)


if __name__ == "__main__":
    # TODO: save only for now :  TBD add a load case.
    example_ncdata_from_iris()