__author__ = 'elip'

from setuptools import setup

COSMO_CELERY_VERSION = '0.3'
COSMO_CELERY_BRANCH = 'feature/CLOUDIFY-2370-plugins-as-python-libs'
COSMO_CELERY = "https://github.com/CloudifySource/" \
               "cosmo-celery-common/tarball/{" \
               "0}#egg=cosmo-celery-common-{1}" \
    .format(COSMO_CELERY_BRANCH,
            COSMO_CELERY_VERSION)

setup(
    name='cosmo-plugin-dsl-parser',
    version='0.3',
    author='elip',
    author_email='elip@gigaspaces.com',
    packages=['dsl_parser'],
    license='LICENSE',
    description='Plugin for transforming recipe DSLs',
    zip_safe=False,
    install_requires=[
        "cosmo-celery-common",
        "PyYAML",
        'jsonschema'
    ],

    dependency_links=[COSMO_CELERY]
)
