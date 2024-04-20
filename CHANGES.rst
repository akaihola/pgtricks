Unreleased_
===========

These features will be included in the next release:

Added
-----
- Builds for Python 3.10, 3.11 and 3.12.

Removed
-------

Fixed
-----
- Empty tables are now handled correctly.
- Very large tables are now sorted without crashing. This is done by merge sorting
  in temporary files.


1.0.0_ / 2021-09-11
====================

Added
-----

- Type hints
- Contributors list
- Install instructions in the README file
- Support only Python 3.7 and later
- Flush last line in ``pg_dump_splitsort.py``
- ``pg_split_schema_dump.py`` for splitting a schema-only dump into multiple SQL files


0.9.1_ / 2015-03-10
===================

Added
-----

- Document ``pg_incremental_backup.py`` in the README file


0.9_ / 2015-03-10
=================

Added
-----

- The ``pg_incremental_backup.py`` script with remote repository URL as an optional
  command line argument
- The New (3-clause) BSD license
- Unit tests, a ``setup.py`` script and a README file with a usage example
- ``pg_dump_splitsort.py`` for sorting and splitting ``pg_dump`` output


.. _Unreleased: https://github.com/akaihola/pgtricks/compare/1.0.0...HEAD
.. _1.0.0: https://github.com/akaihola/pgtricks/compare/0.9.1...1.0.0
.. _0.9.1: https://github.com/akaihola/pgtricks/compare/0.9...0.9.1
.. _0.9: https://github.com/akaihola/pgtricks/compare/46e4cdb...0.9
