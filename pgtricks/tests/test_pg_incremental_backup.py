from __future__ import print_function, unicode_literals
try:
    from unittest.mock import patch
except ImportError:
    # Python 2.7
    from mock import patch
import os
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
from pgtricks import pg_incremental_backup


class DumpDatabaseTestCase(TestCase):
    def setUp(self):
        self.tempdir = mkdtemp()
        self.output_dir = os.path.join(self.tempdir, 'inner_dir')
        self.output_file = os.path.join(self.output_dir, 'output_file.sql')
        with patch.object(pg_incremental_backup,
                          'check_output') as self.check_output:

            pg_incremental_backup.dump_database('dummy_db', self.output_file)

    def tearDown(self):
        rmtree(self.tempdir, ignore_errors=True)

    def test_creates_output_directory(self):
        self.assertTrue(os.path.isdir(self.output_dir))

    def test_runs_pg_dump(self):
        self.check_output.assert_called_once_with(['pg_dump',
                                                   '-O',
                                                   '-f', self.output_file,
                                                   'dummy_db'])


class MakeGitTestCase(TestCase):
    def setUp(self):
        git = pg_incremental_backup.make_git('directory/path')
        with patch.object(pg_incremental_backup,
                          'check_output') as self.check_output:
            self.check_output.return_value = b'git output'

            self.result = git('arg1', 'arg2')

    def test_returns_git_output(self):
        self.assertEqual('git output', self.result)

    def test_calls_git(self):
        self.check_output.assert_called_once_with(('git', 'arg1', 'arg2'),
                                                  cwd='directory/path')
