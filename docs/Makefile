# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

allapi:
	rm -rf ./details/api
	sphinx-apidoc -Mfe -o ./details/api ../lib/ncdata

# N.B. when no changelog entries pending, *don't* add a release section.
#  - this gives a "clean" changelog when building a release version.
towncrier:
	if [ "$$(ls changelog_fragments | grep "\.rst")" != "" ]; then towncrier build --yes; fi

# Tweaked "make html", which restores the changelog state after docs build.
html-keeplog: html
	git checkout HEAD change_log.rst changelog_fragments/


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile allapi towncrier
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

view:
	firefox ./_build/html/index.html
