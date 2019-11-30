from setuptools import setup

setup(
    name='LaLigaOfficialScrapper',
    author='José Ignacio Amelivia Santiago',
    author_email='jignacio.amelivia@gmail.com',
    url='https://namelivia.com',
    description='This is scrapper for La Liga Official wepage',
    license='LICENSE',
    long_description=open('README.md').read(),
    packages=['la_liga_official_scrapper'],
    include_package_data=True,
    install_requires=[
        'unidecode >= 1.1.1',
        'pymongo >= 3.9.0',
        'unittest2 >= 1.1.0',
        'mongomock >= 3.18.0',
        'lxml >= 4.4.2',
        'requests >= 2.22.0',
        'python-dateutil >= 2.8.1',
    ],
)
