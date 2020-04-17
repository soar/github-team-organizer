from cached_property import cached_property
from sgqlc.endpoint.http import HTTPEndpoint

from github_team_organizer.classes.github import GitHubWrapper


class GitHubGraphQL:

    __instance = None

    url = 'https://api.github.com/graphql'

    def __new__(cls, *args, **kwargs):
        if GitHubGraphQL.__instance is None:
            GitHubGraphQL.__instance = super().__new__(cls, *args, **kwargs)
        return GitHubGraphQL.__instance

    @cached_property
    def headers(self):
        return {
            'Authorization': f'bearer {GitHubWrapper().login_or_token}',
        }

    @cached_property
    def endpoint(self):
        return HTTPEndpoint(self.url, self.headers)

    def call(self, *args, **kwargs):
        return self.endpoint(*args, **kwargs)
