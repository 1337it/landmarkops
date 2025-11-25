# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in landmarkops/__init__.py
from landmarkops import __version__ as version

setup(
	name='landmarkops',
	version=version,
	description='Landmark delivery operations with WhatsApp integration',
	author='Landmark',
	author_email='ops@landmark.ae',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
