from textwrap import dedent

from pgtricks.pg_split_schema_dump import split_sql_file


def test_split_sql_file(tmpdir):
    target_directory = tmpdir / 'target'
    (tmpdir / 'test.sql').write(
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

    split_sql_file(tmpdir / 'test.sql', target_directory)
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
