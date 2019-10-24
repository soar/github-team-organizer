# github-team-organizer

Python way to organize permissions in your organization

## Settings

Some options can be set via an environment variable (real or [dotenv](https://github.com/theskumar/python-dotenv)) or command line flag.

| Environment variable name | Command line flag | Description |
| --- | --- | --- |
| `GITHUB_API_KEY` | `-k` / `--api-key` | GitHub API key |
| `GITHUB_ORGANIZATION` | `-o` / `--org` | GitHub Organization which we will operate on |

## Usage

You have two options to execute this script:

- **Apply mode** (`-a` or `--apply`) - real changes will be done through execution
- **Test mode** (`-t` or `--test`, default) - API will be scanned and proposed changes will be reported as output, no real changes will be performed
