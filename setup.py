"""Minut Point API."""
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pypoint",
    version="2.1.0",
    author="Fredrik Erlandsson",
    author_email="fredrik.e@gmail.com",
    description="API for Minut Point",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fredrike/pypoint",
    packages=["pypoint"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "authlib",
    ],
)
