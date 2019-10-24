import os

from cached_property import cached_property
from github import Github as PyGithub
from github.Organization import Organization


class GitHubWrapper(PyGithub):

    __instance = None

    def __new__(cls, *args, **kwargs):
        if GitHubWrapper.__instance is None:
            GitHubWrapper.__instance = super().__new__(cls, *args, **kwargs)
        return GitHubWrapper.__instance

    def __init__(self, login_or_token: str = None):
        if not login_or_token:
            login_or_token = os.getenv('GITHUB_API_KEY')

        super().__init__(login_or_token=login_or_token)

    @cached_property
    def default_organization(self) -> Organization:
        return self.get_organization(os.getenv('GITHUB_ORGANIZATION'))
