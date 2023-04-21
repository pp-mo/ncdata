from setuptools import find_packages, setup

setup(
    name="ncdata",
    version="0.0.1",
    url="https://github.com/pp-mo/ncdata.git",
    author="pp-mo",
    author_email="patrick.peglar@metoffice.gov.uk",
    description="NetCDF data interoperability between Iris and Xarray",
    packages=find_packages(),
    install_requires=["numpy"],
)
