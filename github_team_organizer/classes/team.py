import logging
import typing
from collections.abc import Iterable

from cached_property import cached_property
from github import Github as PyGithub
from github.GithubObject import NotSet
from github.NamedUser import NamedUser
from github.Organization import Organization
from github.Team import Team

from github_team_organizer.classes.base import BaseClass
from github_team_organizer.classes.github import GitHubWrapper
from github_team_organizer.classes.settings import settings


logger = logging.getLogger(__name__)


class GitHubTeam(BaseClass):

    def __init__(
            self,

            name: str,
            description: str,
            privacy: str = 'closed',

            team_maintainers: typing.List[typing.Union[str, NamedUser]] = None,
            team_members: typing.List[typing.Union[str, NamedUser]] = None,

            github: PyGithub = None,
            organization: Organization = None
    ):
        super().__init__()

        self._team_maintainers = []
        self._team_members = []

        self.github = github if github else GitHubWrapper()
        self.organization = organization if organization else GitHubWrapper().default_organization

        self.name = name
        self.description = description
        self.privacy = privacy if privacy else NotSet

        self.team_maintainers = team_maintainers
        self.team_members = team_members

    def __str__(self):
        return f'{self.__class__.__name__} "{self.name}": {self.obj}'

    def run(self):
        self.sync_team_members('maintainer', self.team_maintainers)
        self.sync_team_members('member', self.team_members)
        return self

    @cached_property
    def obj(self) -> Team:
        for org_team in self.organization.get_teams():  # type:Team
            if org_team.name == self.name:
                if org_team.description != self.description or org_team.privacy != self.privacy:
                    logger.warning(f'Team {self.name} meta should be updated...')
                    if settings.apply:
                        org_team.edit(
                            self.name,
                            self.description,
                            privacy=self.privacy
                        )
                    else:
                        logger.info(f' ... skipping')
                return org_team

        logger.warning(f'Team {self.name} not found, should be created...')
        if settings.apply:
            org_team = self.organization.create_team(
                self.name,
                privacy=self.privacy
            )
            org_team.edit(
                self.name,
                self.description,
                privacy=self.privacy
            )
            logger.info(f' ... created')
            return org_team

    @property
    def team_members(self) -> typing.List[NamedUser]:
        return self._team_members

    @property
    def team_maintainers(self) -> typing.List[NamedUser]:
        return self._team_maintainers

    @team_members.setter
    def team_members(self, value):
        if value is not None and isinstance(value, Iterable):
            for m in value:
                self.add_member(self._team_members, m)
        else:
            logger.info(f'No members for team {self}')
            # raise ValueError(f"Should be a list of users")

    @team_maintainers.setter
    def team_maintainers(self, value):
        if value is not None and isinstance(value, Iterable):
            for m in value:
                self.add_member(self._team_maintainers, m)
        else:
            logger.info(f'No maintainers for team {self}')
            # raise ValueError(f"Should be a list of users")

    def add_member(self, member_list: typing.List[NamedUser], member):
        if isinstance(member, str):
            member_list.append(self.github.get_user(member))
        elif isinstance(member, NamedUser):
            member_list.append(member)
        else:
            raise ValueError(f'Wrong team member passed: {member}')

    def sync_team_members(self, member_type: str, member_list: typing.List[NamedUser]):
        """
        Synchronize defined and real team members

        :param member_type: str = 'member' or 'maintainer'
        :param member_list:
        :return:
        """
        if not self.obj:
            logger.warning(f'Team {self.name} has no reference, exiting...')
            return self

        # Remove unlisted members
        for actual_member in self.obj.get_members(member_type):  # type:NamedUser
            if actual_member not in member_list:
                logger.warning(f'Found wrong {member_type} {actual_member} in team {self.obj}, removing')
                if settings.apply:
                    self.obj.remove_membership(actual_member)

        # Add required members
        actual_members = self.obj.get_members(member_type)
        for team_member in member_list:
            if team_member not in actual_members:
                logger.warning(f'Not found {member_type} {team_member} in team {self.obj}, adding')
                if settings.apply:
                    self.obj.add_membership(team_member, member_type)

        return self
