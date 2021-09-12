==========
 pgtricks
==========

|license-badge| |pypi-badge| |downloads-badge| |black-badge| |changelog-badge|

.. |license-badge| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
   :alt: BSD 3 Clause license
   :target: https://github.com/akaihola/pgtricks/blob/master/LICENSE
.. |pypi-badge| image:: https://img.shields.io/pypi/v/pgtricks
   :alt: Latest release on PyPI
   :target: https://pypi.org/project/pgtricks/
.. |downloads-badge| image::  https://pepy.tech/badge/pgtricks
   :alt: Number of downloads
   :target: https://pepy.tech/project/pgtricks
.. |black-badge| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :alt: Source code formatted using Black
   :target: https://github.com/psf/black
.. |changelog-badge| image:: https://img.shields.io/badge/-change%20log-purple
   :alt: Change log
   :target: https://github.com/akaihola/pgtricks/blob/master/CHANGES.rst
.. |next-milestone| image:: https://img.shields.io/github/milestones/progress/akaihola/pgtricks/1?color=red&label=release%201.0.1
   :alt: Next milestone
   :target: https://github.com/akaihola/pgtricks/milestone/1

This package contains two tools for backing up PostgreSQL database dumps.


+------------------------------------------------+--------------------------------+
| |you-can-help|                                 | |support|                      |
+================================================+================================+
| We're asking the community kindly for help to  | We have a                      |
| review pull requests for |next-milestone|_ .   | `community support channel`_   |
| If you have a moment to spare, please take a   | on GitHub Discussions. Welcome |
| look at one of them and shoot us a comment!    | to ask for help and advice!    |
+------------------------------------------------+--------------------------------+

.. _community support channel: https://github.com/akaihola/pgtricks/discussions


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


Contributors ✨
===============

Thanks goes to these wonderful people (`emoji key`_):

.. raw:: html

   <!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section
        This is automatically generated. Please update `contributors.yaml` and
        see `CONTRIBUTING.rst` for how to re-generate this table. -->
   <table>
     <tr>
       <td align="center">
         <a href="https://github.com/oldcai">
           <img src="https://avatars.githubusercontent.com/u/1150130?v=3" width="100px;" alt="@oldcai" />
           <br />
           <sub>
             <b>Albert Cai</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/issues?q=author%3Aoldcai" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/akaihola">
           <img src="https://avatars.githubusercontent.com/u/13725?v=3" width="100px;" alt="@akaihola" />
           <br />
           <sub>
             <b>Antti Kaihola</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/pulls?q=is%3Apr+author%3Aakaihola" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/connorsherson">
           <img src="https://avatars.githubusercontent.com/u/59890055?v=3" width="100px;" alt="@connorsherson" />
           <br />
           <sub>
             <b>Connor Sherson</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/pulls?q=is%3Apr+author%3Aconnorsherson" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/jomonson">
           <img src="https://avatars.githubusercontent.com/u/5840967?v=3" width="100px;" alt="@jomonson" />
           <br />
           <sub>
             <b>Jonathan</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/pulls?q=is%3Apr+author%3Ajomonson" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/jescobar87">
           <img src="https://avatars.githubusercontent.com/u/4821014?v=3" width="100px;" alt="@jescobar87" />
           <br />
           <sub>
             <b>Jose Luis</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/issues?q=author%3Ajescobar87" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/philayres">
           <img src="https://avatars.githubusercontent.com/u/294874?v=3" width="100px;" alt="@philayres" />
           <br />
           <sub>
             <b>Phil Ayres</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/issues?q=author%3Aphilayres" title="Bug reports">🐛</a>
       </td>
     </tr>
     <tr>
       <td align="center">
         <a href="https://github.com/thugcee">
           <img src="https://avatars.githubusercontent.com/u/20202?v=3" width="100px;" alt="@thugcee" />
           <br />
           <sub>
             <b>Seweryn Niemiec</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/issues?q=author%3Athugcee" title="Bug reports">🐛</a>
       </td>
       <td align="center">
         <a href="https://github.com/mihuman">
           <img src="https://avatars.githubusercontent.com/u/16466143?v=3" width="100px;" alt="@mihuman" />
           <br />
           <sub>
             <b>mihuman</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/pulls?q=is%3Apr+author%3Amihuman" title="Code">💻</a>
       </td>
       <td align="center">
         <a href="https://github.com/tyctor">
           <img src="https://avatars.githubusercontent.com/u/44854182?v=3" width="100px;" alt="@tyctor" />
           <br />
           <sub>
             <b>tyctor</b>
           </sub>
         </a>
         <br />
         <a href="https://github.com/akaihola/pgtricks/issues?q=author%3Atyctor" title="Bug reports">🐛</a>
       </td>
     </tr>
   </table>   <!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the all-contributors_ specification.
Contributions of any kind are welcome!

.. _README.rst: https://github.com/akaihola/pgtricks/blob/master/README.rst
.. _emoji key: https://allcontributors.org/docs/en/emoji-key
.. _all-contributors: https://allcontributors.org
