# -*- coding: utf-8 -*-

from distutils.core import setup
from setuptools import find_packages

setup(name='Phatty',
    version='1.1',
    description='Library editor for Moog Little Phatty',
    author='David García Goñi',
    author_email='dagargo@gmail.com',
    url='https://github.com/dagargo/phatty',
    packages=find_packages(exclude=['doc', 'test']),
    package_data={'phatty': ['resources/*']},
    license='GNU General Public License v3 (GPLv3)',
    install_requires=['mido', 'python-rtmidi'],
    test_suite='tests',
    tests_require=['mock']
)
