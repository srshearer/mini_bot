import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="minibot",
    version="0.1.0",
    author='Steven Shearer',
    author_email='srshearer@gmail.com',
    description='Tools for managing a Plex server and file transfers',
    install_requires=[
        'PlexAPI',
        'requests',
        'argparse',
        'flask',
        'pysftp',
    ],
    license='MIT',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/srshearer/minibot",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
