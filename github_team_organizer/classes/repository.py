import logging
import os
import typing
from collections import defaultdict
from fnmatch import fnmatch

import click
from cached_property import cached_property
from github import Github as PyGithub, GithubObject
from github.GithubException import GithubException, UnknownObjectException
from github.Organization import Organization as PyGithubOrganization
from github.Repository import Repository as PyGithubRepository
from github.Team import Team as PyGithubTeam
from sgqlc.operation import Operation

from github_team_organizer.classes.base import BaseClass
from github_team_organizer.classes.github import GitHubWrapper
from github_team_organizer.graphql.github_schema import github_schema as schema
from github_team_organizer.classes.ghgql import GitHubGraphQL
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
            triage_teams: typing.List[GitHubTeam] = None,

            precreated_branches: list = None,
            protection: dict = None,
            default_branch_name: str = 'master',
            master_branch_name: str = 'master',
            auto_cicd_protection_mode: str = None,

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
        self.triage_teams = triage_teams or []

        self.name = name

        self.precreated_branches = precreated_branches or []
        self.protection = protection or {}
        self.default_branch_name = default_branch_name
        self.master_branch_name = master_branch_name
        self.auto_cicd_protection_mode = auto_cicd_protection_mode or os.getenv('AUTO_CICD_PROTECTION_MODE')

    def __str__(self):
        return str(self.obj)

    @cached_property
    def full_name(self) -> str:
        return f'{self.organization.login}/{self.name}'

    @cached_property
    def obj(self) -> PyGithubRepository:
        return self.github.get_repo(self.full_name)

    @cached_property
    def gq_repository(self) -> schema.Repository:
        op = Operation(schema.Query)
        r = op.repository(owner=self.organization.login, name=self.name)
        r.id()
        r.branch_protection_rules(first=100)
        r.branch_protection_rules.nodes.id()
        r.branch_protection_rules.nodes.pattern()
        data = GitHubGraphQL().call(op)
        return (op + data).repository

    @cached_property
    def gq_node_id(self) -> str:
        return self.gq_repository.id

    @cached_property
    def gq_branch_protection_rules(self):
        return self.gq_repository.branch_protection_rules.nodes

    def gq_get_branch_protection_rule_id(self, pattern: str):
        for rule in self.gq_branch_protection_rules:
            if rule.pattern == pattern:
                return rule.id

    def get_default_protection(self):
        return {
            'requires_approving_reviews': True,
            'required_approving_review_count': 1,

            'requires_commit_signatures': False,

            'is_admin_enforced': False,
            'dismisses_stale_reviews': True,
            'requires_code_owner_reviews': False,

            'requires_status_checks': True,
            'requires_strict_status_checks': True,
            'required_status_check_contexts': [],

            'restricts_review_dismissals': False,
            'review_dismissal_actor_ids': [t.gq_node_id for t in self.master_teams],

            'restricts_pushes': True,
            'push_actor_ids': [t.gq_node_id for t in self.master_teams],
        }

    @property
    def protection(self):
        return self._protection

    @protection.setter
    def protection(self, value: dict):
        self._protection = {k: {**self.get_default_protection(), **v} for k, v in value.items()}

    def run(self):
        self.update_settings()
        self.clean_direct_collaborators()

        self.sync_teams(self.admin_teams, 'admin')
        self.sync_teams([x for x in self.master_teams + self.push_teams if x not in self.admin_teams], 'push')
        self.sync_teams(self.pull_teams, 'pull')
        self.sync_teams(self.triage_teams, 'triage')

        if settings.apply:
            current_protected_branches = {rule.pattern: rule.id for rule in self.gq_branch_protection_rules}

            for protection_pattern in self.protection.keys():
                self.apply_protection(protection_pattern)
                current_protected_branches.pop(protection_pattern)

            for rule_pattern, rule_id in current_protected_branches.items():
                click.secho(f'Removing old protection rule: {rule_pattern} / {rule_id}', bg='yellow')
                self.remove_protection(rule_id)

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

    def apply_protection(self, protection_pattern: str):
        protection = dict(self.protection.get(protection_pattern))
        if fnmatch(self.master_branch_name, protection_pattern):
            protection['push_actor_ids'] += [t.gq_node_id for t in self.master_teams]

        for branch_name in self.precreated_branches:
            try:
                _ = self.obj.get_branch(branch_name)
            except GithubException:
                logger.warning(f'Branch {branch_name} not found, will be created')
                if settings.apply:
                    master_branch = self.obj.get_branch('master')
                    self.obj.create_git_ref(
                        ref='refs/heads/' + branch_name,
                        sha=master_branch.commit.sha
                    )

        if self.auto_cicd_protection_mode == 'jenkins':
            try:
                if self.obj.get_contents('Jenkinsfile').size != 0:
                    if protection.get('required_status_check_contexts') is None:
                        protection['required_status_check_contexts'] = []
                    protection['required_status_check_contexts'] += [
                        'continuous-integration/jenkins/branch',
                        'continuous-integration/jenkins/pr-merge',
                    ]
                else:
                    click.secho(f'Jenkinsfile is empty for {self.obj}', bold=True, bg='yellow')
            except UnknownObjectException:
                click.secho(f'Jenkinsfile not found for {self.obj}', bold=True, bg='yellow')

        protection['pattern'] = protection_pattern

        op = Operation(schema.Mutation)

        if self.gq_get_branch_protection_rule_id(protection_pattern):
            protection['branch_protection_rule_id'] = self.gq_get_branch_protection_rule_id(protection_pattern)
            op.update_branch_protection_rule(input=schema.UpdateBranchProtectionRuleInput(
                **protection
            ))
        else:
            protection['repository_id'] = self.gq_node_id
            op.create_branch_protection_rule(input=schema.CreateBranchProtectionRuleInput(
                **protection
            ))

        if settings.apply:
            GitHubGraphQL().call(op)

    def remove_protection(self, protection_rule_id):
        op = Operation(schema.Mutation)
        op.delete_branch_protection_rule(input=schema.DeleteBranchProtectionRuleInput(
            branch_protection_rule_id=protection_rule_id
        ))
        if settings.apply:
            GitHubGraphQL().call(op)
