#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="virtsudo",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "virtsudo=virtsudo.cli:main",
        ],
    },
    description="Virtual sudo environment inside a container",
    license="MIT",
)
