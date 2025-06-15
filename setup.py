from setuptools import setup, find_packages
import os

# Extract version from the package without importing it
here = os.path.abspath(os.path.dirname(__file__))
version = None
version_file = os.path.join(here, 'src', 'pyonetrue', 'cli.py')
with open(version_file) as f:
    for line in f:
        if line.startswith('__version__'):
            part = line.split('=')[1].strip()
            part = part.strip('"')
            part = part.strip("'")
            version = part
            break

setup(
    name='pyonetrue',
    version=version,
    author='Philip Dye',
    author_email='phdye@acm.org',
    description='Flatten Python packages into single modules, preserving order and CLI',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/phdye/pyonetrue',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'pyonetrue = pyonetrue.cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
