from github import Github as PyGithub
from github.Organization import Organization as PyGithubOrganization

from github_team_organizer.classes.github import GitHubWrapper


class Organization:

    __instance = None

    def __new__(cls, *args, **kwargs):
        if Organization.__instance is None:
            Organization.__instance = super().__new__(cls, *args, **kwargs)
        return Organization.__instance

    def __init__(self, name: str, github: PyGithub = None):
        if not github:
            github = GitHubWrapper()

        self.github_organization: PyGithubOrganization = github.get_organization(name)
