`pg_dump_splitsort.py` is a handy script for pre-processing `pg_dump` output to
make it more suitable for diffing and storing in version control:

It splits the dump into the following files:

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
