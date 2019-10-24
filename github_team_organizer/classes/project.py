import typing

from github import Github as PyGithub
from github.Organization import Organization as PyGithubOrganization
from github.NamedUser import NamedUser

from github_team_organizer.classes.base import BaseClass
from github_team_organizer.classes.github import GitHubWrapper
from github_team_organizer.classes.repository import GitHubRepositoryWrapper
from github_team_organizer.classes.team import GitHubTeam


class GitHubProject(BaseClass):

    def __init__(
            self,
            name: str,

            repositories: list = None,
            repository_defaults: dict = None,

            subprojects: typing.List['GitHubProject'] = None,
            parent_project: 'GitHubProject' = None,

            master_teams: typing.List['GitHubTeam'] = None,
            master_team_members: typing.List[typing.Union[str, 'NamedUser']] = None,

            dev_teams: typing.List['GitHubTeam'] = None,
            dev_team_members: typing.List[typing.Union[str, 'NamedUser']] = None,

            qa_teams: typing.List['GitHubTeam'] = None,
            qa_team_members: typing.List[typing.Union[str, 'NamedUser']] = None,

            github: PyGithub = None,
            organization: PyGithubOrganization = None
    ):
        super().__init__()

        self.github = github or GitHubWrapper()
        self.organization = organization or self.github.default_organization

        self.name = name

        self.subprojects = []
        if subprojects:
            for subproject in subprojects:
                self.subprojects.append(subproject)

        self.master_teams = master_teams or []
        if master_team_members:
            self.master_teams.append(
                GitHubTeam(
                    name=f'projects/{self.name}/masters',
                    description=f'{self.name} / Masters',
                    team_members=master_team_members,
                )
            )

        self.dev_teams = dev_teams or []
        if dev_team_members:
            self.dev_teams.append(
                GitHubTeam(
                    name=f'project/{self.name}/developers',
                    description=f'{self.name} / Developers',
                    team_members=dev_team_members,
                )
            )

        self.qa_teams = qa_teams or []
        if qa_team_members:
            self.qa_teams.append(
                GitHubTeam(
                    name=f'project/{self.name}/qa',
                    description=f'{self.name} / QA',
                    team_members=qa_team_members,
                )
            )

        self.repository_defaults = repository_defaults or {}
        self.repositories = [self.init_repository(r) for r in repositories]

        # for r in self.repositories:
        #     r.verify_teams(self.master_teams, 'push')
        #     r.verify_teams(self.master_teams, 'pull')

    def __str__(self):
        return f'Project: {self.name}'

    def init_repository(self, repository) -> GitHubRepositoryWrapper:
        if isinstance(repository, str):
            # full_name = '/'.join(filter(None, [
            #     self.organization.login,
            #     repository
            # ]))

            return GitHubRepositoryWrapper(
                name=repository,
                organization=self.organization,
                **self.repository_defaults
            )
        else:
            return repository

    def run(self):
        for r in self.repositories:
            r.run()
