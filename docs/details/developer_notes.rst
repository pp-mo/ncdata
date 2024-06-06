Developer Notes
===============
Maintenance and manual processes


Change Log Maintenance
----------------------
For now, development PRs should normally include additions in the common
changelog file ``docs/change_log.rst``.

For now, we aren't categorising changes, but intend to include a combination
of release-page notes and a simple list of PRs.


Documentation build
-------------------

* For a full docs-build
    * a simple ``$ make html`` will do for now
    * The ``docs/Makefile`` wipes the API docs and invokes sphinx-apidoc for a full rebuild

* Results are then available at ``docs/_build/html/index.html``
    * The above is just for *local testing* if required
    * We have automatic builds for releases and PRs
      via `ReadTheDocs <https://readthedocs.org/projects/ncdata/>`_


Release actions
---------------

#. Cut a release on GitHub : this triggers a new docs version on [ReadTheDocs](https://readthedocs.org/projects/ncdata/)

#. Build the distribution

    #. if needed, get `build <https://github.com/pypa/build>`_

    #. run ``$ python -m build``

#. Push to PyPI

    #. if needed, get `twine <https://github.com/pypa/twine>`_

    #. run
        * ``$ python -m twine upload --repository testpypi dist/*``
        * this uploads to TestPyPI

    #. create a new env with test dependencies
       * ``$ conda create -n ncdtmp python=3.11 iris xarray filelock requests pytest pip``
       * ( N.B. 'filelock' and 'requests' are _test_ dependencies of iris )

    #. install the new package with
       * ``$ pip install --index-url https://test.pypi.org/simple/ ncdata``
       * ..and run tests

    #. if that checks OK,
        * **remove** ``--repository testpypi`` **and repeat** "upload" step (2)
        * --> uploads to "real" PyPI

    #. repeat "pip install" step (4)
       * but **removing** the ``--index-url``
       * ..to check that ``pip install ncdata`` now finds the new version

#. Update conda to source the new version from PyPI

    #. create a PR on the `ncdata feedstock <https://github.com/conda-forge/ncdata-feedstock>`_

    #. update :
        * `version number <https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L2>`_
        * `SHA <https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L10>`_
        * Notes:
            * the `PyPI reference <https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L9>`_
              will normally look after itself
            * also at this point
               * make any required changes to `dependencies <https://github.com/conda-forge/ncdata-feedstock/blob/3f6b35cbdffd2ee894821500f76f2b0b66f55939/recipe/meta.yaml#L17-L29>`_
               * ..but normally, **no** changes will be required

    #. get PR merged
       * wait a few hours..
       * check that the new version appears in the output of ``$ conda search ncdata``
