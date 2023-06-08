from setuptools import setup, find_packages

setup(
    name='rapidpro_flow_tools',
    version='2.0.7',
    license='LICENSE',
    author='IDEMS International',
    author_email='communications@idems.international',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    url='https://github.com/IDEMSInternational/rapidpro-flow-toolkit',
    keywords='rapidpro flow tools',
)