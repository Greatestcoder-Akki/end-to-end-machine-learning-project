from setuptools import find_packages, setup
from typing import List

Hyphen_e_dot = '-e .'

def get_requirements(file_path: str) -> List[str]:
    requirements = []
    with open(file_path) as file:
        requirements = file.readlines()
        requirements = [req.replace("\n", "") for req in requirements]
        if Hyphen_e_dot in requirements:
            requirements.remove(Hyphen_e_dot)
    return requirements

setup(
    name='mlProject',
    version='0.0.1',
    author='Akshat Negi',
    author_email='akshatnegi2005@gmail.com',
    packages=find_packages(),
    install_requires=get_requirements('requirements.txt')
)# The get_requirements function reads a requirements file and returns a list of package names.
# It removes any newline characters from each line.
# If the special entry '-e .' (represented by Hyphen_e_dot) is present, it removes it.
# '-e .' is used in requirements files to install the current project in "editable" mode.
# This is useful for development, but you may want to exclude it from the list of installable packages.