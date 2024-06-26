Snippets
========

Notes and writeups of handy description areas, that don't yet have a home.

Data component (NameMap) dictionaries
-------------------------------------
For all of these properties, dictionary-style behaviour means that its ``.keys()``
is a sequence of the content names, and ``.values()`` is a sequence of the contained
objects.


NcData
------
The :class:`~ncdata.NcData` class represents either a dataset or group,
the structures of these are identical.

NcAttributes
------------
attributes are stored as NcAttribute objects, rather than simple name: value maps.
thus an 'attribute' of a NcVariable or NcData is an attribute object, not a value.

Thus:

    >>> variable.attributes['x']
    NcAttribute('x', [1., 2., 7.])

The attribute has a ``.value`` property, but it is most usefully accessed with the
:meth:`~ncdata.NcAttribute.as_python_value()` method :

    >>> attr = NcAttribute('b', [1.])
    >>> attr.value
    array([1.])
    >>> attr.as_python_value()
    array(1.)

    >>> attr = NcAttribute('a', "this")
    >>> attr.value
    array('this', dtype='<U4')
    >>> attr.as_python_value()
    'this'

From within a parent object's ``.attributes`` dictionary,


Component Dictionaries
----------------------
ordering
- insert, remove, rename effects
re-ordering


As described :ref:`above <howto_access>`, sub-components are stored under their names
in a dictionary container.

Since all components have a name, and are stored by name in the parent property
dictionary (e.g. ``variable.attributes`` or ``data.dimensions``), the component
dictionaries have an :meth:`~ncdata.NameMap.add` method, which works with the component
name.
supported operations
^^^^^^^^^^^^^^^^^^^^
standard dict methods : del, getitem, setitem, clear, append, extend
extra methods : add, addall

ordering
^^^^^^^^
For Python dictionaries in general,
since `announced in Python 3.7 <https://mail.python.org/pipermail/python-dev/2017-December/151283.html>`_,
the order of the entries is now a significant and stable feature of Python dictionaries.
There
Also as for Python dictionaries generally, there is no particular assistance for
managing or using the order.  The following may give some indication:

extract 'n'th item: ``data.variables[list(elelments.keys())[n]]``
sort the list:
    # get all the contents, sorted by name
    content = list(data.attributes.values())
    content = sorted(content, key= lambda v: v.name)
    # clear the container -- necessary to forget the old ordering
    data.attributes.clear()
    # add all back in, in the new order
    data.attributes.addall(content)

New entries are added last, and renamed entries retain their

The :meth:`~ncdata.utils/dataset_differences` method reports differences in the
ordering of components (unless turned off).


