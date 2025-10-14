Installation
============
Ncdata is available on PyPI and conda-forge

Install from conda-forge with conda
-----------------------------------
Like this:

.. code-block:: bash

    $ conda install -c conda-forge ncdata


Install from PyPI with pip
--------------------------
Like this:

.. code-block:: bash

    $ pip install ncdata


Check install
^^^^^^^^^^^^^

.. code-block:: bash

    $ python -c "from ncdata import NcData; print(NcData())"
    <NcData: <'no-name'>
    >


Developer Installation
----------------------
To work on changes to the ncdata code, you will need an "editable installation".
See : :ref:`developer_install`.
