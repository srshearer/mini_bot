import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mini_bot",
    version="0.0.1",
    author='Steven Shearer',
    author_email='srshearer@gmail.com',
    description='Tools for sending notification messages as a Slack bot user',
    install_requires=[
        'PlexAPI',
        'requests',
        'argparse',
    ],
    license='MIT',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/srshearer/mini_bot",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
