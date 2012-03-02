#!/usr/bin/env python

from distutils.core import setup
import MonkeyBackup 

modules=['MonkeyBackup']
scripts=['monkey-backup']
configfiles=[ "monkey-backup.ini", "include.txt", "exclude.txt" ]
#manfiles=[ x+'.1.gz' for x in scripts]

if __name__ == '__main__':
    setup(name="monkey-backup",
        version=MonkeyBackup.__version__,
        description=MonkeyBackup.__description__,
        author=MonkeyBackup.__author__,
        author_email=MonkeyBackup.__email__,
        url=MonkeyBackup.__url__,
        license=MonkeyBackup.__license__,
        py_modules=modules,
        scripts=scripts,
        data_files=[
             ('/etc/monkey-backup', configfiles),
        #    ('share/man/man1', manfiles)
        ]
    )

