# Repo Analyzer & Release Notes Generator

## Overview
This Python script analyzes a GitHub or GitLab repository, retrieves recent commit history and merge requests (PRs), and generates structured release notes. It leverages APIs to fetch repository data and uses a language model (Gemini-1.5-Flash) to generate human-readable release notes.

## Features
- **Supports GitHub & GitLab** - Automatically detects the repository provider.
- **Fetches Commits & Merge Requests** - Retrieves detailed commit messages, file changes, and diffs.
- **Generates Release Notes** - Uses an AI model to create well-structured markdown-based release notes.
- **Markdown Output** - Saves release notes in a `release_notes.md` file.

## Prerequisites
Ensure you have the following installed:
- Python 3.x
- `requests` library (for API calls)
- `python-dotenv` (for loading environment variables)
- `langchain-google-genai` (for AI-generated release notes)

Install dependencies using:
```sh
pip install requests python-dotenv langchain-google-genai
```

## Environment Variables
Create a `.env` file and add the following variables:
```
REPO_URL=<your-repository-url>
BRANCH_NAME=<branch-to-analyze>
MAX_COMMITS=5  # Number of commits to fetch (default: 5)
MAX_MERGE_REQUESTS=5  # Number of merge requests to fetch (default: 5)
GITHUB_TOKEN=<your-github-api-token>  # Required for GitHub repos
GITLAB_TOKEN=<your-gitlab-api-token>  # Required for GitLab repos
```

## Usage
Run the script with:
```sh
python repo_release_notes.py
```

### How It Works:
1. **Identifies Provider:** Determines if the repo is on GitHub or GitLab.
2. **Fetches Repository Data:**
   - Retrieves commit history and detailed commit changes.
   - Fetches merged pull/merge requests and file modifications.
3. **Formats Data:**
   - Extracts commit messages, file changes, diffs, and author details.
4. **Generates Release Notes:**
   - AI model structures release notes into an easy-to-read markdown format.
   - Includes an overview, categorized changes, and a file modification table.
5. **Outputs Results:**
   - Displays commit and merge request summaries.
   - Saves release notes to `release_notes.md`.

## Example Output
### Commits Analyzed:
```
- [3a4b5c] Fixed authentication bug
  By John Doe on 2024-02-01
  Files: auth.py, utils.py
```

### Merge Requests Analyzed:
```
- [!42] Added OAuth support
  By Jane Smith on 2024-01-29
  Files: auth.py, config.yaml
```

### Generated Release Notes (saved in `release_notes.md`):
```markdown
## Release Notes for Project
### Overview of Changes
- Implemented OAuth login.
- Fixed security issues in authentication.

### Technical Breakdown
#### New Features
- Added OAuth login support.

#### Bug Fixes
- Resolved authentication bypass issue.

### Files Changed Summary
| File      | Changes | Status   | Additions | Deletions |
|-----------|--------|---------|-----------|-----------|
| auth.py   | 3      | modified | 20        | 5         |
| config.yaml | 1    | added    | 10        | 0         |
```

## Troubleshooting
- Ensure your API token is valid and has access to the repository.
- Verify `REPO_URL` and `BRANCH_NAME` are correct.
- Check API rate limits if responses fail.

## Future Improvement Areas
- **Timeline-based Commit Fetching:** Support fetching commits based on specific time ranges (`since`, `until`).
- **Automated Triggers:** Implement webhook-based triggers so that when a commit is pushed to a specific repository or branch, the release notes are automatically generated and stored.
- **Enhanced AI Summarization:** Improve AI-generated release notes by adding impact analysis and categorization enhancements.
- **Multi-Branch Support:** Allow analysis across multiple branches in the same repository.

## License
This project is open-source and available under the MIT License.

