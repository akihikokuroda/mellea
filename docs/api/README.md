# Mellea API Documentation

This directory contains the Sphinx configuration and source files for generating the Mellea API documentation.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install mellea[docs]
```

Or install the dependencies directly:

```bash
pip install sphinx sphinx_rtd_theme sphinx-autodoc-typehints sphinx_mdinclude
```

### Build Commands

Build HTML documentation:

```bash
./build_docs.sh
```

Clean and rebuild:

```bash
./build_docs.sh clean
```

Build other formats:

```bash
./build_docs.sh html      # HTML (default)
./build_docs.sh dirhtml   # HTML with separate directories
./build_docs.sh text      # Plain text
./build_docs.sh man       # Man pages
./build_docs.sh latex     # LaTeX sources
```

Get help:

```bash
./build_docs.sh --help
```

### Output Location

Built documentation will be in `docs/api/_build/<format>/`

For HTML: `docs/api/_build/html/index.html`

## Directory Structure

```
docs/api/
├── conf.py           # Sphinx configuration
├── index.rst         # Main documentation index
├── stdlib.rst        # Standard library API reference
├── backends.rst      # Backend implementations
├── helpers.rst       # Helper utilities
├── build_docs.sh     # Build script
├── README.md         # This file
└── _build/           # Generated documentation (gitignored)
```

## Configuration

The Sphinx configuration is in `conf.py`. Key settings:

- **Theme**: Read the Docs theme (`sphinx_rtd_theme`)
- **Extensions**: autodoc, autosummary, napoleon, viewcode, intersphinx, autodoc-typehints
- **Autodoc**: Automatically documents all members, including undocumented ones
- **Napoleon**: Supports Google and NumPy style docstrings

## Adding New Modules

To document a new module:

1. Create or update the appropriate `.rst` file (e.g., `stdlib.rst`, `backends.rst`)
2. Add an `automodule` directive:

```rst
New Module
~~~~~~~~~~

.. automodule:: mellea.new_module
   :members:
   :undoc-members:
   :show-inheritance:
```

3. Rebuild the documentation

## Troubleshooting

### Import Errors

If you get import errors when building:

1. Make sure Mellea is installed: `pip install -e .`
2. Check that all dependencies are installed
3. Verify the Python path in `conf.py`

### Missing Modules

If modules aren't appearing in the documentation:

1. Check that the module is properly imported in `mellea/__init__.py`
2. Verify the module path in the `.rst` file
3. Ensure the module has a docstring

### Theme Issues

If the theme doesn't load:

```bash
pip install --upgrade sphinx_rtd_theme