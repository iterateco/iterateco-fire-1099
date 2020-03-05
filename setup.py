"""
Module packaging
"""

from setuptools import setup, find_packages

setup(
    name='iterateco-fire-1099',
    description='Generate 1099-MISC files for transmission through the \
    IRS FIRE system',
    long_description=open('README.md').read(),

    license='MIT',

    author='Hiep Dam',
    author_email='hiep@iterate.co',
    url='https://github.com/iterateco/iterateco-fire-1099',

    version='0.0.1-alpha',

    packages=find_packages(exclude=['contrib', 'docs', 'tests*', 'spec*']),
    include_package_data=True,
    install_requires=['click', 'jsonschema'],
    scripts=['bin/fire-1099'],

    classifiers=[
        'Development Status :: 4 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ]
)
