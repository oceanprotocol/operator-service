#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

from setuptools import find_packages, setup

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

install_requirements = [
    'eth_account',
    'coloredlogs==10.0',
    'Flask==1.0.2',
    'Flask-Cors==3.0.6',
    'flask-swagger==0.2.14',
    'flask-swagger-ui==3.20.9',
    'Jinja2>=2.10.1',
    'kubernetes==10.0.0',
    'requests>=2.21.0',
    'gunicorn==19.9.0',
    'PyYAML==5.1',
    'pytz==2018.5',
    'simplejson>=3.13.2',
    'psycopg2>=2.8.4',
]

setup_requirements = ['pytest-runner>=2.11.1', ]

dev_requirements = [
    'bumpversion==0.5.3',
    'pkginfo==1.4.2',
    'twine==1.11.0',
    # not virtualenv: devs should already have it before pip-installing
    'watchdog==0.8.3',
]

test_requirements = [
    'codacy-coverage==1.3.11',
    'coverage==4.5.1',
    'mccabe==0.6.1',
    'pylint==2.2.2',
    'pytest==5.4.1',
    'tox==3.2.1',
]

setup(
    author="leucothia",
    author_email='devops@oceanprotocol.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="🐳 Infrastructure Operator Micro-service",
    extras_require={
        'test': test_requirements,
        'dev': dev_requirements + test_requirements,
    },
    include_package_data=True,
    install_requires=install_requirements,
    keywords='operator-service',
    license="Apache Software License 2.0",
    long_description=readme,
    long_description_content_type="text/markdown",
    name='operator-service',
    packages=find_packages(include=['operator_service']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/oceanprotocol/operator-service',
    version='1.0.1',
    zip_safe=False,
)
