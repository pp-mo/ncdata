"""Temporary integrational proof-of-concept example for dataset printout."""
from pathlib import Path

import iris

import ncdata.iris as nci
from ncdata import NcAttribute, NcData, NcDimension, NcVariable
from tests import testdata_dir


def sample_printout():  # noqa: D103
    iris.FUTURE.datum_support = True
    filepath = testdata_dir / 'toa_brightness_temperature.nc'
    cubes = iris.load(filepath)

    ds = nci.from_iris(cubes)
    # FOR NOW: Add a random extra group to exercise some extra behaviour,
    # namely groups and shortform variables (vars with no attrs)
    ds.groups["extra"] = NcData(
        name="extra",
        dimensions={"extra_qq": NcDimension("extra_qq", 4, unlimited=True)},
        variables={
            "noattrs": NcVariable("noattrs", ["x"]),
            "x": NcVariable(
                name="x",
                dimensions=["y", "extra_qq"],
                attributes={
                    "q1": NcAttribute("q1", 1),
                    "q_multi": NcAttribute("q_multi", [1.1, 2.2]),
                    "q_multstr": NcAttribute("q_multstr", ["one", "two"]),
                },
            ),
        },
        attributes={"extra__global": NcAttribute("extra__global", "=value")},
    )
    print(ds)


if __name__ == "__main__":
    sample_printout()
