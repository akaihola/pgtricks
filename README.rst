==========
 pgtricks
==========

|travis-badge|_ |license-badge|_ |pypi-badge|_ |downloads-badge|_

.. |travis-badge| image:: https://travis-ci.com/akaihola/pgtricks.svg?branch=master
.. _travis-badge: https://travis-ci.com/akaihola/pgtricks
.. |license-badge| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
.. _license-badge: https://github.com/akaihola/pgtricks/blob/master/LICENSE
.. |pypi-badge| image:: https://img.shields.io/pypi/v/pgtricks
.. _pypi-badge: https://pypi.org/project/pgtricks/
.. |downloads-badge| image:: https://pepy.tech/badge/pgtricks
.. _downloads-badge: https://pepy.tech/project/pgtricks

This package contains two tools for backing up PostgreSQL database dumps.


Installing
==========

To install in a virtualenv or globally as a superuser::

    pip install pgtricks

To install only for the current user::

    pip install --user pgtricks


pg_dump_splitsort
=================

``pg_dump_splitsort`` is a handy script for pre-processing PostgreSQL's
``pg_dump`` output to make it more suitable for diffing and storing in version
control.

Usage::

    pg_dump_splitsort <filename>.sql

The script splits the dump into the following files:

| ``0000_prologue.sql``:
    everything up to the first COPY
| ``0001_<schema>.<table>.sql``
| :
| :
| ``NNNN_<schema>.<table>.sql``:
    COPY data for each table *sorted by the first field*
| ``9999_epilogue.sql``:
    everything after the last COPY

The files for table data are numbered so a simple sorted concatenation of all
files can be used to re-create the database::

    $ cat *.sql | psql <database>

I've found that a good way to take a quick look at differences between dumps is
to use the `meld` tool on the whole directory::

    $ meld old-dump/ new-dump/

Storing the dump in version control also gives a decent view on the
differences. Here's how to configure git to use color in diffs::

    # ~/.gitconfig
    [color]
            diff = true
    [color "diff"]
            frag = white blue bold
            meta = white green bold
            commit = white red bold

**Note:** If you have created/dropped/renamed tables, remember to delete all
`.sql` files before post-processing the new dump.


pg_incremental_backup
=====================

The ``pg_incremental_backup`` script

- makes a database dump using ``pg_dump``
- splits the dump into per-table files using ``pg_dump_splitsort``
- creates or commits changes into a local Git repository containing the dump
- pushes the changes to the remote repository

Usage::

    pg_incremental_backup [-h] [--output-dir OUTPUT_DIR] database [remote]

    positional arguments:
      database
      remote

    optional arguments:
      -h, --help            show this help message and exit
      --output-dir OUTPUT_DIR, -o OUTPUT_DIR
