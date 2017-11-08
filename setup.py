from setuptools import setup
import os
import frames

def get_project_metadata():
    metadata_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'frames', '__version__.py')
    metadata = dict()
    with open(metadata_file, 'r', encoding='utf-8') as f:
        exec(f.read(), metadata)
    return metadata

with open('README.rst', 'r', encoding='utf-8') as readme_file:
    readme = readme_file.read()
metadata = get_project_metadata()

setup(
    name=metadata["__title__"],
    version=metadata["__version__"],
    packages=['frames', "frames.ui"],
    url=metadata["__url__"],
    license='University of Illinois/NCSA Open Source License',
    maintainer=metadata["__maintainer__"],
    maintainer_email=metadata["__maintainer_email__"],
    description=metadata["__description__"],
    long_description=readme,
    test_suite="tests",
    install_requires=[
        "pyqt5"
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    entry_points={
         "console_scripts": [
             'frames = frames.__main__:main'
         ]
     },
    zip_safe=False,
)
