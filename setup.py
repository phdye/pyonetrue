from setuptools import setup, find_packages

setup(
    name='pyonetrue',
    version='0.5.0',
    author='Your Name',
    author_email='you@example.com',
    description='Flatten Python packages into single modules, preserving order and drivers',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/pyonetrue',
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
