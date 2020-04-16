#!/usr/bin/env python

import importlib
import os
import sys

import click
from dotenv import load_dotenv, find_dotenv

from github_team_organizer.classes.github import GitHubWrapper
from github_team_organizer.classes.project import GitHubProject
from github_team_organizer.classes.settings import settings
from github_team_organizer.classes.team import GitHubTeam
from github_team_organizer.classes.repository import GitHubRepositoryWrapper

sys.path.append(os.getcwd())
load_dotenv(find_dotenv(usecwd=True), verbose=True)


@click.command(help='GitHub Config Applier')
@click.option('--api-key', '-k', default=os.getenv('GITHUB_API_KEY'), help='GitHub API Key')
@click.option('--org', '-o', default=os.getenv('GITHUB_ORGANIZATION'), help='GitHub Organization')
@click.option('--apply/--test', '-a/-t', default=False, help='Perform changes or just test them')
def run(**kwargs):
    for k, v in kwargs.items():
        setattr(settings, k, v)

    all_repositories = [
        r.full_name
        for r in GitHubWrapper().default_organization.get_repos(type='all')
    ]

    click.echo(f'Starting Team Organizer for {settings.org}...')
    if settings.apply:
        click.secho(f'In apply mode script will make real changes!', fg='red')
        click.pause(f'Press enter to continue...')
    else:
        click.secho(f'To apply changes - use "--apply" switch', fg='black')

    importlib.import_module('config')

    for t in GitHubTeam.instances():  # type:GitHubTeam
        click.secho(f'Processing team {t}...', bg='blue')
        t.run()

    for p in GitHubProject.instances():
        click.secho(f'Project: {p}', blink=True, bold=True, bg='blue')
        p.run()

    for r in GitHubRepositoryWrapper.instances():
        click.secho(f'Repository {r}', bg='blue')
        r.run()
        all_repositories.remove(r.full_name)

    for r in all_repositories:
        click.secho(f'Settings for the repository: {r} not found', bold=True, bg='yellow')
