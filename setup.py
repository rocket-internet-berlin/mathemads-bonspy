# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='bonspy',
    version='0.0.1',
    description='Library that converts bidding trees to the AppNexus Bonsai language.',
    author='Alexander Volkmann, Georg Walther',
    packages=['bonspy'],
    package_dir={'bonspy': 'bonspy'},
    url='https://github.com/mathemads/bonspy',
    download_url='https://github.com/mathemads/bonspy/tarball/master',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2.7'
    ]
)
