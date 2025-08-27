#!/usr/bin/env python

import greekroom
from pathlib import Path

from setuptools import setup, find_namespace_packages

long_description = Path('README.md').read_text(encoding='utf-8', errors='ignore')

classifiers = [  # copied from https://pypi.org/classifiers/
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Topic :: Utilities',
    'Topic :: Text Processing',
    'Topic :: Text Processing :: General',
    'Topic :: Text Processing :: Filters',
    'Topic :: Text Processing :: Linguistic',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3 :: Only',
]

setup(
    name='greekroom',
    version=greekroom.__version__,
    description=greekroom.__description__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=classifiers,
    python_requires='>=3.11',
    url='https://github.com/BibleNLP/greek-room',
    download_url='https://github.com/BibleNLP/greek-room',
    platforms=['any'],
    author='Ulf Hermjakob',
    author_email='ulfhermjakob@gmail.com',
    packages=find_namespace_packages(include=['greekroom', 'gr_utilities', 'owl'], exclude=['aux', 'old', 'tmp']),
    keywords=['machine translation', 'datasets', 'NLP', 'natural language processing,'
                                                        'computational linguistics'],
    entry_points={
        'console_scripts': [
            'repeated_words.py=greekroom.owl.repeated_words:main',
            'wb_file_props.py=greekroom.gr_utilities.wb_file_props:main',
        ],
    },
    install_requires=[
        'regex>=2025.7.34',
        'unicodeblock>=0.3.1',
        'uroman>=1.3.1.1',
        'wheel>=0.45.1',
    ],
    include_package_data=True,
    zip_safe=False,
)
