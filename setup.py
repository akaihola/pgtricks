from setuptools import setup


setup(name='pgtricks',
      version='0.9.1',
      description='PostgreSQL utilities',
      long_description=open('README.rst').read(),
      author='Antti Kaihola',
      author_email='antti.15+pgtricks@kaihola.fi',
      url='https://github.com/akaihola/pgtricks',
      packages=['pgtricks'],
      entry_points={
          'console_scripts': [
              'pg_dump_splitsort = pgtricks.pg_dump_splitsort:main',
              'pg_incremental_backup = pgtricks.pg_incremental_backup:main']},
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 2 :: Only',
          'Topic :: Database',
          'Topic :: System :: Archiving :: Backup'],
      keywords='database postgresql backup git',
      license='BSD',
      zip_safe=True,
      test_suite='pgtricks.tests',
      tests_require=['mock==1.0.1']
)
