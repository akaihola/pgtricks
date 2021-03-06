#!/usr/bin/env python

from argparse import ArgumentParser, Namespace
from glob import glob
import os
from subprocess import CalledProcessError, check_output

from typing_extensions import Protocol

from pgtricks.pg_dump_splitsort import split_sql_file


def parse_arguments() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('database')
    parser.add_argument('remote', nargs='?')
    parser.add_argument('--output-dir', '-o', default='.')
    return parser.parse_args()


def dump_database(database: str, output_file: str) -> None:
    output_dir = os.path.dirname(output_file)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    check_output(['pg_dump', '-O', '-f', output_file, database])


class GitCallable(Protocol):
    def __call__(self, *args: str) -> str: ...


def make_git(directory: str) -> GitCallable:
    def git(*args: str) -> str:
        return check_output(('git',) + args, cwd=directory).decode('utf-8')
    return git


def commit_database(directory: str, remote: str) -> None:
    try:
        git = make_git(directory)
        if not os.path.isdir(os.path.join(directory, '.git')):
            git('init')
        if not git('config', '--get', 'remote.origin.url'):
            if not remote:
                raise ValueError("Can't set remote repository URL - missing "
                                 "from the command line")
            git('remote', 'add', 'origin', remote)
        current_origin = git('config', '--get', 'remote.origin.url')[:-1]
        if remote and current_origin != remote:
            raise ValueError("Git remote origin {!r} doesn't match {!r}"
                             .format(current_origin, remote))
        git('add', '-u')
        git('add', '*.sql')
        if git('status', '--porcelain'):
            git('commit', '-m', 'Automatic database update')
            git('push', 'origin', 'master')
    except CalledProcessError as exc_info:
        print(exc_info.output)
        raise


def main() -> None:
    opts = parse_arguments()
    output_file = os.path.join(opts.output_dir,
                               '{}.sql'.format(opts.database))
    for path in glob(os.path.join(opts.output_dir, '*.sql')):
        os.remove(path)
    dump_database(opts.database, output_file)
    split_sql_file(output_file)
    os.remove(output_file)
    commit_database(opts.output_dir, opts.remote)


if __name__ == '__main__':
    main()
