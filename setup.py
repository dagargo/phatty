# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages

setup(name='Phatty',
    version='2.0',
    description='Library editor for Moog Little Phatty',
    author='David García Goñi',
    author_email='dagargo@gmail.com',
    url='https://github.com/dagargo/phatty',
    packages=find_packages(exclude=['tests']),
    package_data={'phatty': ['resources/*']},
    license='GNU General Public License v3 (GPLv3)'
)
