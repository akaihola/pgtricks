"""Tests for :mod:`pgtricks.pg_split_schema_dump`"""

import os
import warnings
from textwrap import dedent

from pgtricks.pg_split_schema_dump import split_sql_file


def test_split_sql_file(tmpdir):
    target_directory = tmpdir / 'target'
    sqlpath = tmpdir / 'test.sql'
    sqlpath.write(
        dedent(
            '''

            --
            -- Name: table1; Type: TABLE; Schema: public; Owner:
            --

            (information for table1 goes here)

            --
            -- Name: table2; Type: TABLE; Schema: public; Owner:
            --

            (information for table2 goes here)

            --
            -- Name: table3; Type: TABLE; Schema: public; Owner:
            --

            (information for table3 goes here)
            '''
        )
    )

    split_sql_file(str(sqlpath), str(target_directory))

    assert {path.basename for path in target_directory.listdir()} == {
        'public.table1.TABLE',
        'public.table2.TABLE',
        'public.table3.TABLE',
    }
    assert (target_directory / 'public.table1.TABLE').readlines(cr=False) == [
        'SET search_path = public;',
        '',
        '',
        '',
        '--',
        '-- Name: table1; Type: TABLE; Schema: public; Owner:',
        '--',
        '',
        '(information for table1 goes here)',
    ]
    assert (target_directory / 'public.table2.TABLE').readlines(cr=False) == [
        'SET search_path = public;',
        '',
        '',
        '',
        '--',
        '-- Name: table2; Type: TABLE; Schema: public; Owner:',
        '--',
        '',
        '(information for table2 goes here)',
    ]
    assert (target_directory / 'public.table3.TABLE').readlines(cr=False) == [
        'SET search_path = public;',
        '',
        '',
        '',
        '--',
        '-- Name: table3; Type: TABLE; Schema: public; Owner:',
        '--',
        '',
        '(information for table3 goes here)',
        '',
    ]


def test_split_sql_file_no_schema(tmpdir):
    target_directory = tmpdir / 'target'
    sqlpath = tmpdir / 'test.sql'
    sqlpath.write(
        dedent(
            '''

            --
            -- Name: table1; Type: TABLE; Schema: -; Owner:
            --

            (information for table1 goes here)
            '''
        )
    )

    split_sql_file(str(sqlpath), str(target_directory))

    assert {path.basename for path in target_directory.listdir()} == {
        'no_schema.table1.TABLE'
    }


def test_split_sql_file_unrecognized_content(tmpdir):
    target_directory = tmpdir / 'target'
    sqlpath = tmpdir / 'test.sql'
    sqlpath.write(
        dedent(
            '''

            --
            -- Name: table1; Type: TABLE; Schema: public; Owner:
            --

            (information for table1 goes here)

            --
            -- an example of unidentified content
            --

            (information for the unidentified content goes here)

            --
            -- Name: table2; Type: TABLE; Schema: public; Owner:
            --

            (information for table2 goes here)
            '''
        )
    )
    with warnings.catch_warnings(record=True) as caught_warnings:

        split_sql_file(str(sqlpath), str(target_directory))

    assert {path.basename for path in target_directory.listdir()} == {
        'public.table1.TABLE',
        'public.table2.TABLE',
    }
    assert len(caught_warnings) == 1
    caught_warnings_text = str(caught_warnings[0].message).replace(str(tmpdir), "")
    assert caught_warnings_text == dedent(
        f"""\
        Can't identify the following SQL chunk in {os.sep}test.sql:
        =============================================================================


        --
        -- an example of unidentified content
        --

        (information for the unidentified content goes here)
        ============================================================================="""
    )


def test_split_sql_file_with_quotes_in_name(tmpdir):
    target_directory = tmpdir / "target"
    sqlpath = tmpdir / "test.sql"
    sqlpath.write(
        dedent(
            """

            --
            -- Name: "user"; Type: TABLE; Schema: public; Owner:
            --

            (information for user table goes here)
            """
        )
    )

    split_sql_file(str(sqlpath), str(target_directory))

    assert {path.basename for path in target_directory.listdir()} == {
        "public.user.TABLE"
    }
    assert (target_directory / "public.user.TABLE").readlines(cr=False) == [
        "SET search_path = public;",
        "",
        "",
        "",
        "--",
        '-- Name: "user"; Type: TABLE; Schema: public; Owner:',
        "--",
        "",
        "(information for user table goes here)",
        "",
    ]
