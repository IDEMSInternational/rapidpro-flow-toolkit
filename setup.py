from setuptools import setup, find_packages

setup(
    name='rapidpro_flow_tools',
    version='0.9.2',
    license='MIT',
    author='Ed Moss',
    author_email='ed.moss@eemengineering.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    url='https://github.com/IDEMSInternational/rapidpro-flow-toolkit',
    keywords='rapidpro flow tools',
)
