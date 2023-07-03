"""Temporary integrational proof-of-concept example for dataset printout."""
import iris
import iris.tests as itsts

import ncdata.iris as nci
from ncdata import NcAttribute, NcData, NcDimension, NcVariable


def sample_printout():  # noqa: D103
    iris.FUTURE.datum_support = True
    filepath = itsts.get_data_path(
        ["NetCDF", "stereographic", "toa_brightness_temperature.nc"]
    )
    cubes = iris.load(filepath)

    ds = nci.from_iris(cubes)
    # FOR NOW: Add a random extra group to exercise some extra behaviour,
    # namely groups and shortform variables (vars with no attrs)

    class NameMap(dict):
        """
        Name-dictionary.

        A convenience for constructing a dictionary containing objects indexed by
        their "obj.name"s.

        A custom constructor and += operator are provided for this.
        Other methods are not changed, however, so the intended contract that
        ``self[x].name == x`` can easily be broken by manipulation.
        """

        def __init__(self, *args):
            """
            Constructor taking a number of ``object``\\s as args.
            Each must have an ``arg.name``, and is inserted at that index.
            """
            super().__init__(((arg.name, arg) for arg in args))

        def __iadd__(self, obj):
            """
            Support a "+=" operator to add an additional content object.

            Only adds one item.  For multiples, use
            ``self.update(NameMap(*more_objects))`` instead.
            """
            self[obj.name] = obj
            return self

    ds.groups["extra"] = NcData(
        name="extra",
        dimensions=NameMap(NcDimension("extra_qq", 4)),
        variables=NameMap(
            NcVariable("noattrs", ["x"]),
            NcVariable(
                name="x",
                dimensions=["y", "extra_qq"],
                attributes=NameMap(
                    NcAttribute("q1", 1),
                    NcAttribute("q_multi", [1.1, 2.2]),
                    NcAttribute("q_multstr", ["one", "two"]),
                ),
            ),
        ),
        attributes=NameMap(NcAttribute("extra__global", "=value")),
    )
    print(ds)


if __name__ == "__main__":
    sample_printout()
