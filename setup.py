import os
from pathlib import Path
from setuptools import setup, find_namespace_packages


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='github-team-organizer',
    version=Path('version.txt').read_text().strip(),
    packages=find_namespace_packages(include=['github_team_organizer.*']),
    include_package_data=True,
    url='https://soar.name',
    license='MIT',
    author='soar',
    author_email='i@soar.name',
    description='Tool for organizing your GitHub Organization',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    entry_points={
        'console_scripts': [
            'team-organizer = github_team_organizer.scripts.organizer:run'
        ]
    },
    install_requires=[
        'pygithub',
        'python-dotenv',
        'click',
        'cached-property',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
