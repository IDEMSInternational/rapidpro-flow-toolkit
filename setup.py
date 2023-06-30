from setuptools import setup, find_packages

setup(
    name='rapidpro_flow_tools',
    version='2.0.8',
    license='LICENSE',
    author='IDEMS International',
    author_email='communications@idems.international',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    url='https://github.com/IDEMSInternational/rapidpro-flow-toolkit',
    keywords='rapidpro flow tools',
    install_requires=[
        "Jinja2~=3.0.3",
        "networkx~=2.5.1",
        "pydantic~=1.8.2",
        "tablib[ods]>=3.1.0",
        "openpyxl~=3.0.7",
        "google-api-python-client~=2.6.0",
        "google-auth-oauthlib~=0.4.4",
    ]
)
