import logging
import typing
from collections import defaultdict

from cached_property import cached_property
from github import Github as PyGithub, GithubObject
from github.GithubException import GithubException
from github.Organization import Organization as PyGithubOrganization
from github.Repository import Repository as PyGithubRepository
from github.Team import Team as PyGithubTeam

from github_team_organizer.classes.base import BaseClass
from github_team_organizer.classes.github import GitHubWrapper
from github_team_organizer.classes.settings import settings
from github_team_organizer.classes.team import GitHubTeam


logger = logging.getLogger(__name__)


class GitHubRepositoryWrapper(BaseClass):

    cicd_enabled = True
    cicd_master_branch = 'master'
    cicd_develop_branch = 'develop'

    # def __new__(cls, name: str, *args, **kwargs):
    #     github = kwargs.get('github') or GitHubWrapper()
    #     return github.get_repo(name)

    def __init__(
            self,

            name: str,

            admin_teams: typing.List[GitHubTeam] = None,
            master_teams: typing.List[GitHubTeam] = None,
            push_teams: typing.List[GitHubTeam] = None,
            pull_teams: typing.List[GitHubTeam] = None,

            protection: dict = None,
            default_branch_name: str = 'master',
            master_branch_name: str = 'master',

            github: PyGithub = None,
            organization: PyGithubOrganization = None
    ):
        super().__init__()
        self._protection = defaultdict(dict)

        self.github = github or GitHubWrapper()
        self.organization = organization if organization else GitHubWrapper().default_organization

        self.admin_teams = admin_teams or []
        self.master_teams = master_teams or []
        self.push_teams = push_teams or []
        self.pull_teams = pull_teams or []

        self.name = name

        self.protection = protection or {}
        self.default_branch_name = default_branch_name
        self.master_branch_name = master_branch_name

    def __str__(self):
        return str(self.obj)

    @cached_property
    def full_name(self) -> str:
        return f'{self.organization.login}/{self.name}'

    @cached_property
    def obj(self) -> PyGithubRepository:
        return self.github.get_repo(self.full_name)

    @property
    def protection(self):
        return self._protection

    @protection.setter
    def protection(self, value: dict):
        default_protection = {
            'strict': True,
            'contexts': [],
            'enforce_admins': False,
            'dismiss_stale_reviews': True,
            'dismissal_teams': [t.name for t in self.master_teams],
            'required_approving_review_count': 1,
        }
        self._protection = {k: {**default_protection, **v} for k, v in value.items()}

    def run(self):
        self.update_settings()
        self.clean_direct_collaborators()

        self.sync_teams(self.admin_teams, 'admin')
        self.sync_teams([x for x in self.master_teams + self.push_teams if x not in self.admin_teams], 'push')
        self.sync_teams(self.pull_teams, 'pull')

        if settings.apply:
            for branch in self.protection.keys():
                self.apply_protection(branch)

        return self

    def update_settings(self):
        if settings.apply:
            repository_settings = {
                'allow_merge_commit': True,
                'allow_squash_merge': False,
                'allow_rebase_merge': False,
            }

            if self.default_branch_name != 'master':
                repository_settings['default_branch'] = self.default_branch_name

            self.obj.edit(**repository_settings)
            self.obj.enable_vulnerability_alert()
            self.obj.enable_automated_security_fixes()
        return self

    def clean_direct_collaborators(self):
        collaborators = self.obj.get_collaborators(affiliation='direct')
        if collaborators.totalCount:
            logger.warning(f"Found direct collaborators in repository: {self}, cleaning")
            for collaborator in collaborators:
                logger.warning(f" - {collaborator}")
                if settings.apply:
                    self.obj.remove_from_collaborators(collaborator)

    def sync_teams(self, teams: typing.List[GitHubTeam], permission: str):
        # Remove not listed teams
        for actual_team in [t for t in self.obj.get_teams() if t.permission == permission]:  # type:PyGithubTeam
            if actual_team.slug not in [t.name for t in teams]:
                logger.warning(f'Found wrong team {actual_team} with {permission} access to {self}, removing')

                # logger.warning(f'Teams: {teams}')
                # logger.warning(f'A Team: {actual_team}')

                if settings.apply:
                    actual_team.remove_from_repos(self.obj)
        # Add required teams
        actual_teams = [t for t in self.obj.get_teams() if t.permission == permission]
        for team in teams:
            if team.name not in [t.slug for t in actual_teams]:
                logger.warning(f'Not found {team} with {permission} access to {self}, adding')
                if settings.apply:
                    # team.obj.add_to_repos(self.obj)
                    team.obj.set_repo_permission(self.obj, permission)

    def apply_protection(self, branch_name: str):
        protection = dict(self.protection.get(branch_name))
        if branch_name == self.master_branch_name:
            protection.update({
                'team_push_restrictions': [t.name for t in self.master_teams]
            })

        try:
            branch = self.obj.get_branch(branch_name)
        except GithubException:
            logger.warning(f'Branch {branch_name} not found, will be created')
            if settings.apply:
                master_branch = self.obj.get_branch('master')
                self.obj.create_git_ref(
                    ref='refs/heads/' + branch_name,
                    sha=master_branch.commit.sha
                )
                branch = self.obj.get_branch(branch_name)
            else:
                branch = None
        if settings.apply:
            branch.edit_protection(**protection)

            if protection.get('required_approving_review_count') == GithubObject.NotSet:
                branch.remove_required_pull_request_reviews()
