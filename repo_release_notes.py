import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

def identify_provider(repo_url):
    """
    Determine if the repo is hosted on GitHub or GitLab.
    """
    if "github.com" in repo_url:
        return "github"
    elif "gitlab.com" in repo_url:
        return "gitlab"
    else:
        raise ValueError("Unsupported Git provider")


def setup_headers(provider):
    """
    Setup HTTP headers required for the API calls based on the provider.
    """
    if provider == "github":
        return {
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github+json"
        }
    elif provider == "gitlab":
        return {
            "PRIVATE-TOKEN": os.getenv("GITLAB_TOKEN"),
            "Accept": "application/json"
        }
    return {}


def parse_repo_url(repo_url, provider):
    """
    Parse the repository URL to extract necessary parts.
    For GitHub: owner and repo name.
    For GitLab: project ID (URL-encoded).
    """
    parsed = urlparse(repo_url)
    path = parsed.path.strip("/")
    if provider == "github":
        parts = path.split("/")
        return {"owner": parts[0], "repo": parts[1]}
    elif provider == "gitlab":
        project_path = path
        if project_path.endswith(".git"):
            project_path = project_path[:-4]
        # GitLab requires '/' to be URL-encoded as '%2F'
        return {"project_id": project_path.replace("/", "%2F")}
    return {}


def format_file_changes(files):
    """
    Format file change information for GitHub.
    """
    return [{
        "filename": f['filename'],
        "status": f['status'],
        "additions": f.get('additions', 0),
        "deletions": f.get('deletions', 0),
        "changes": f.get('changes', 0)
    } for f in files]


def gitlab_change_type(file_diff):
    """
    Determine the change type for GitLab diffs.
    """
    if file_diff['new_file']:
        return "added"
    if file_diff['deleted_file']:
        return "deleted"
    if file_diff['renamed_file']:
        return "renamed"
    return "modified"


def format_gitlab_file_changes(changes):
    """
    Format file change information for GitLab.
    The counts here are derived from the diff text.
    """
    return [{
        "filename": f['new_path'],
        "status": gitlab_change_type(f),
        "additions": f['diff'].count("\n+") - 1,
        "deletions": f['diff'].count("\n-") - 1,
        "changes": f['diff'].count("\n+") + f['diff'].count("\n-") - 2
    } for f in changes]


def get_github_commit_details(owner, repo, sha, headers):
    """
    Retrieve detailed information for a specific GitHub commit.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_github_commit_diff(owner, repo, sha, headers):
    """
    Retrieve the diff of a specific GitHub commit.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    # Change the Accept header to get diff format
    new_headers = headers.copy()
    new_headers["Accept"] = "application/vnd.github.v3.diff"
    response = requests.get(url, headers=new_headers)
    response.raise_for_status()
    return response.text


def get_github_commits(owner, repo, branch, max_commits, headers):
    """
    Get a list of recent commits from a GitHub repository on a specific branch.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {"per_page": max_commits, "sha": branch}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    commits = []
    for commit in response.json():
        sha = commit['sha']
        details = get_github_commit_details(owner, repo, sha, headers)
        commits.append({
            "sha": sha,
            "message": details['commit']['message'],
            "author": details['commit']['author']['name'],
            "date": details['commit']['author']['date'],
            "files": format_file_changes(details['files']),
            "diff": get_github_commit_diff(owner, repo, sha, headers)
        })
    return commits


def get_github_pr_details(owner, repo, pr_number, headers):
    """
    Retrieve file details for a specific GitHub pull request.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return {"files": response.json()}


def get_github_pr_diff(owner, repo, pr_number, headers):
    """
    Retrieve the combined diff from a specific GitHub pull request.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    patches = [f['patch'] for f in response.json() if 'patch' in f]
    return "\n".join(patches)


def get_github_pull_requests(owner, repo, branch, max_requests, headers):
    """
    Get a list of closed pull requests from GitHub for the specified branch.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    params = {"per_page": max_requests, "state": "closed", "base": branch}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    prs = []
    for pr in response.json():
        pr_number = pr['number']
        details = get_github_pr_details(owner, repo, pr_number, headers)
        prs.append({
            "id": pr_number,
            "title": pr['title'],
            "author": pr['user']['login'],
            "merged_at": pr['merged_at'],
            "files": format_file_changes(details['files']),
            "diff": get_github_pr_diff(owner, repo, pr_number, headers)
        })
    return prs


# ------------------------------
# GitLab API Functions
# ------------------------------

def get_gitlab_commit_details(project_id, sha, headers):
    """
    Retrieve diff details for a specific GitLab commit.
    """
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits/{sha}/diff"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return {"diff": response.json()}


def get_gitlab_commit_diff(project_id, sha, headers):
    """
    Retrieve the diff text for a specific GitLab commit.
    """
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits/{sha}/diff"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    diffs = response.json()
    return "\n".join([d['diff'] for d in diffs])


def get_gitlab_commits(project_id, branch, max_commits, headers):
    """
    Get a list of recent commits from a GitLab repository on a specific branch.
    """
    url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits"
    params = {"per_page": max_commits, "ref_name": branch}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    commits = []
    for commit in response.json():
        sha = commit['id']
        details = get_gitlab_commit_details(project_id, sha, headers)
        commits.append({
            "sha": sha,
            "message": commit['message'],
            "author": commit['author_name'],
            "date": commit['committed_date'],
            "files": format_gitlab_file_changes(details['diff']),
            "diff": get_gitlab_commit_diff(project_id, sha, headers)
        })
    return commits


def get_gitlab_mr_details(project_id, mr_iid, headers):
    """
    Retrieve change details for a specific GitLab merge request.
    """
    url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_gitlab_mr_diff(project_id, mr_iid, headers):
    """
    Retrieve the combined diff text for a specific GitLab merge request.
    """
    url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{mr_iid}/diffs"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    diffs = response.json()
    return "\n".join([d['diff'] for d in diffs])


def get_gitlab_merge_requests(project_id, branch, max_requests, headers):
    """
    Get a list of merged merge requests from GitLab for the specified branch.
    """
    url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests"
    params = {"per_page": max_requests, "state": "merged", "target_branch": branch}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    mrs = []
    for mr in response.json():
        mr_iid = mr['iid']
        details = get_gitlab_mr_details(project_id, mr_iid, headers)
        mrs.append({
            "id": mr_iid,
            "title": mr['title'],
            "author": mr['author']['username'],
            "merged_at": mr['merged_at'],
            "files": format_gitlab_file_changes(details['changes']),
            "diff": get_gitlab_mr_diff(project_id, mr_iid, headers)
        })
    return mrs


# ------------------------------
# Release Notes Generation
# ------------------------------

def generate_release_notes(commits, merge_requests):
    """
    Generate release notes using the ChatGoogleGenerativeAI model.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.2)
    
    prompt = f"""Analyze these Git commits and merge requests to generate professional release notes. 
Focus on:
- Code changes in diffs
- File modifications (added/modified/deleted)
- Commit message patterns
- Merge/Pull requests (if available)
- Impact analysis of changes

Structure:(JUST FOLLOW THE BELOW GIVEN SECTIONS AND STRUCTURE)
1. Overview of changes
2. Technical breakdown by category
    a. New Features (if any)
    b. Improvements (if any)
    c. Bug Fixes (if any)
    d. Other (if any)
3. Notable code modifications (categorized points)
4. Files Changed Summary (in markdown table format like below):
    | File | Changes | Status | Additions | Deletions |
    |------|---------|--------|-----------|-----------|

Commits to analyze:
{commits}

Merge Requests to analyze:
{merge_requests}

Output in markdown with technical depth. Highlight significant code changes.
Avoid mentioning AI generation in any form.
"""
    response = llm.invoke(prompt)
    return response.content


if __name__ == "__main__":
    REPO_URL = os.getenv("REPO_URL")
    BRANCH_NAME = os.getenv("BRANCH_NAME")
    MAX_COMMITS = int(os.getenv("MAX_COMMITS", 5))
    MAX_MERGE_REQUESTS = int(os.getenv("MAX_MERGE_REQUESTS", 5))
    
    if not REPO_URL or not BRANCH_NAME:
        raise ValueError("Missing required environment variables: REPO_URL, BRANCH_NAME")
    
    # Determine provider, setup headers, and parse repository info
    provider = identify_provider(REPO_URL)
    headers = setup_headers(provider)
    repo_info = parse_repo_url(REPO_URL, provider)
    
    print(f"Analyzing {provider} repo: {REPO_URL} on branch: {BRANCH_NAME}")
    
    # Fetch commits and merge requests based on the provider
    if provider == "github":
        owner = repo_info["owner"]
        repo = repo_info["repo"]
        commits = get_github_commits(owner, repo, BRANCH_NAME, MAX_COMMITS, headers)
        merge_requests = get_github_pull_requests(owner, repo, BRANCH_NAME, MAX_MERGE_REQUESTS, headers)
    elif provider == "gitlab":
        project_id = repo_info["project_id"]
        commits = get_gitlab_commits(project_id, BRANCH_NAME, MAX_COMMITS, headers)
        merge_requests = get_gitlab_merge_requests(project_id, BRANCH_NAME, MAX_MERGE_REQUESTS, headers)
    
    # Display analyzed commits
    print("\nCommits Analyzed:")
    for commit in commits:
        print(f"- [{commit['sha'][:7]}] {commit['message']}")
        print(f"  By {commit['author']} on {commit['date']}")
        file_list = [f['filename'] for f in commit['files']]
        print(f"  Files: {', '.join(file_list)}\n")
    
    # Display analyzed merge requests
    print("\nMerge Requests Analyzed:")
    for mr in merge_requests:
        print(f"- [!{mr['id']}] {mr['title']}")
        print(f"  By {mr['author']} on {mr['merged_at']}")
        file_list = [f['filename'] for f in mr['files']]
        print(f"  Files: {', '.join(file_list)}\n")
    
    # Generate and display release notes
    release_notes = generate_release_notes(commits, merge_requests)
    print(f"\nGenerated Release Notes for {REPO_URL} (Branch: {BRANCH_NAME})")
    print(release_notes)
    
    # Save release notes to a markdown file
    with open("release_notes.md", "w") as f:
        f.write(release_notes)
