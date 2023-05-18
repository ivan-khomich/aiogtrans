#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path

from setuptools import find_packages, setup


def get_file(*paths):
    path = os.path.join(*paths)
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf8")
    except IOError:
        pass


def get_version():
    version = "2.0.0"
    return version


def get_description():
    description = """An async and updated version of the googletrans package."""
    return description


def get_readme():
    return get_file(os.path.dirname(__file__), "README.md")


def get_requirements():
    requirements = ["httpx<=0.23.0", "setuptools==58.1.0"]
    return requirements


def install():
    setup(
        name="aiogtrans",
        version=get_version(),
        description=get_description(),
        long_description=get_readme(),
        long_description_content_type="text/markdown",
        license="MIT",
        author="Ben Z",
        author_email="bleg3ndary@gmail.com",
        url="https://github.com/Leg3ndary/aiogtrans",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Education",
            "Intended Audience :: End Users/Desktop",
            "License :: Freeware",
            "Operating System :: POSIX",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: MacOS :: MacOS X",
            "Topic :: Education",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3.9",
        ],
        packages=find_packages(exclude=["docs", "tests"]),
        keywords="google translate translator async",
        install_requires=get_requirements(),
        python_requires=">=3.9",
    )


if __name__ == "__main__":
    install()
