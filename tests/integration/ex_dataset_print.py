"""Temporary integrational proof-of-concept example for dataset printout."""
import iris
import iris.tests as itsts


def sample_printout():  # noqa: D103
    iris.FUTURE.datum_support = True
    filepath = itsts.get_data_path(
        ["NetCDF", "stereographic", "toa_brightness_temperature.nc"]
    )
    cubes = iris.load(filepath)
    import ncdata.iris as nci

    ds = nci.from_iris(cubes)
    print(ds)


if __name__ == "__main__":
    sample_printout()
