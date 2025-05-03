from setuptools import setup, find_packages

setup(
    name='pyonetrue',
    version='0.5.3',
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
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
