import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

class RepoAnalyzer:
    def __init__(self, repo_url, branch_name):
        self.repo_url = repo_url
        self.branch = branch_name
        self.provider = self._identify_provider()
        self.headers = self._setup_headers()
        self.repo_info = self._parse_repo_url()
        
        print(f"Initialized analyzer for {self.provider} repo: {self.repo_url} on branch: {self.branch}")

    def _identify_provider(self):
        if "github.com" in self.repo_url:
            return "github"
        elif "gitlab.com" in self.repo_url:
            return "gitlab"
        raise ValueError("Unsupported Git provider")

    def _setup_headers(self):
        if self.provider == "github":
            return {
                "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
                "Accept": "application/vnd.github+json"
            }
        elif self.provider == "gitlab":
            return {
                "PRIVATE-TOKEN": os.getenv("GITLAB_TOKEN"),
                "Accept": "application/json"
            }
        return {}

    def _parse_repo_url(self):
        parsed = urlparse(self.repo_url)
        path = parsed.path.strip("/")
        
        if self.provider == "github":
            parts = path.split("/")
            return {"owner": parts[0], "repo": parts[1]}
        
        elif self.provider == "gitlab":
            project_path = path
            if project_path.endswith(".git"):
                project_path = project_path[:-4]
            return {"project_id": project_path.replace("/", "%2F")}

    def get_commit_history(self, max_commits=10):
        if self.provider == "github":
            return self._get_github_commits(max_commits)
        elif self.provider == "gitlab":
            return self._get_gitlab_commits(max_commits)
        return []

    def get_merge_requests(self, max_requests=5):
        if self.provider == "github":
            return self._get_github_pull_requests(max_requests)
        elif self.provider == "gitlab":
            return self._get_gitlab_merge_requests(max_requests)
        return []

    def _get_github_commits(self, max_commits):
        url = f"https://api.github.com/repos/{self.repo_info['owner']}/{self.repo_info['repo']}/commits"
        params = {
            "per_page": max_commits,
            "sha": self.branch
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        commits = []
        for commit in response.json():
            commit_details = self._get_github_commit_details(commit['sha'])
            commits.append({
                "sha": commit['sha'],
                "message": commit_details['commit']['message'],
                "author": commit_details['commit']['author']['name'],
                "date": commit_details['commit']['author']['date'],
                "files": self._format_file_changes(commit_details['files']),
                "diff": self._get_github_commit_diff(commit['sha'])
            })
        return commits

    def _get_gitlab_commits(self, max_commits):
        url = f"https://gitlab.com/api/v4/projects/{self.repo_info['project_id']}/repository/commits"
        params = {
            "per_page": max_commits,
            "ref_name": self.branch
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        commits = []
        for commit in response.json():
            commit_details = self._get_gitlab_commit_details(commit['id'])
            commits.append({
                "sha": commit['id'],
                "message": commit['message'],
                "author": commit['author_name'],
                "date": commit['committed_date'],
                "files": self._format_gitlab_file_changes(commit_details['diff']),
                "diff": self._get_gitlab_commit_diff(commit['id'])
            })
        return commits

    def _get_github_pull_requests(self, max_requests):
        url = f"https://api.github.com/repos/{self.repo_info['owner']}/{self.repo_info['repo']}/pulls"
        params = {
            "per_page": max_requests,
            "state": "closed",
            "base": self.branch
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        prs = []
        for pr in response.json():
            pr_details = self._get_github_pr_details(pr['number'])
            prs.append({
                "id": pr['number'],
                "title": pr['title'],
                "author": pr['user']['login'],
                "merged_at": pr['merged_at'],
                "files": self._format_file_changes(pr_details['files']),
                "diff": self._get_github_pr_diff(pr['number'])
            })
        return prs

    def _get_gitlab_merge_requests(self, max_requests):
        url = f"https://gitlab.com/api/v4/projects/{self.repo_info['project_id']}/merge_requests"
        params = {
            "per_page": max_requests,
            "state": "merged",
            "target_branch": self.branch
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        mrs = []
        for mr in response.json():
            mr_details = self._get_gitlab_mr_details(mr['iid'])
            mrs.append({
                "id": mr['iid'],
                "title": mr['title'],
                "author": mr['author']['username'],
                "merged_at": mr['merged_at'],
                "files": self._format_gitlab_file_changes(mr_details['changes']),
                "diff": self._get_gitlab_mr_diff(mr['iid'])
            })
        return mrs

    def _format_file_changes(self, files):
        return [{
            "filename": f['filename'],
            "status": f['status'],
            "additions": f.get('additions', 0),
            "deletions": f.get('deletions', 0),
            "changes": f.get('changes', 0)
        } for f in files]

    def _format_gitlab_file_changes(self, changes):
        return [{
            "filename": f['new_path'],
            "status": self._gitlab_change_type(f),
            "additions": f['diff'].count("\n+") - 1,
            "deletions": f['diff'].count("\n-") - 1,
            "changes": f['diff'].count("\n+") + f['diff'].count("\n-") - 2
        } for f in changes]

    def _gitlab_change_type(self, file_diff):
        if file_diff['new_file']: return "added"
        if file_diff['deleted_file']: return "deleted"
        if file_diff['renamed_file']: return "renamed"
        return "modified"

    def _get_github_commit_details(self, sha):
        url = f"https://api.github.com/repos/{self.repo_info['owner']}/{self.repo_info['repo']}/commits/{sha}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _get_gitlab_commit_details(self, sha):
        url = f"https://gitlab.com/api/v4/projects/{self.repo_info['project_id']}/repository/commits/{sha}/diff"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return {"diff": response.json()}

    def _get_github_pr_details(self, pr_number):
        url = f"https://api.github.com/repos/{self.repo_info['owner']}/{self.repo_info['repo']}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return {"files": response.json()}

    def _get_gitlab_mr_details(self, mr_iid):
        url = f"https://gitlab.com/api/v4/projects/{self.repo_info['project_id']}/merge_requests/{mr_iid}/changes"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _get_github_commit_diff(self, sha):
        url = f"https://api.github.com/repos/{self.repo_info['owner']}/{self.repo_info['repo']}/commits/{sha}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def _get_gitlab_commit_diff(self, sha):
        url = f"https://gitlab.com/api/v4/projects/{self.repo_info['project_id']}/repository/commits/{sha}/diff"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return "\n".join([d['diff'] for d in response.json()])

    def _get_github_pr_diff(self, pr_number):
        url = f"https://api.github.com/repos/{self.repo_info['owner']}/{self.repo_info['repo']}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return "\n".join([f['patch'] for f in response.json() if 'patch' in f])

    def _get_gitlab_mr_diff(self, mr_iid):
        url = f"https://gitlab.com/api/v4/projects/{self.repo_info['project_id']}/merge_requests/{mr_iid}/diffs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return "\n".join([d['diff'] for d in response.json()])

def generate_release_notes(commits, merge_requests):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.2)
    
    prompt = f"""Analyze these Git commits and merge requests to generate professional release notes. 
    Focus on:
    - Code changes in diffs
    - File modifications (added/modified/deleted)
    - Commit message patterns
    - Impact analysis of changes

    Structure:(JUST FOLLOW THE BELOW GIVEN SECTIONS AND STRUCTURE)
    1. Overview of changes
    2. Technical breakdown by category
    3. Notable code modifications
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
    MAX_COMMITS = int(os.getenv("MAX_COMMITS", 5))
    MAX_MERGE_REQUESTS = int(os.getenv("MAX_MERGE_REQUESTS", 5))
    BRANCH_NAME = os.getenv("BRANCH_NAME")
    
    if not all([REPO_URL, BRANCH_NAME]):
        raise ValueError("Missing required environment variables: REPO_URL, BRANCH_NAME")
    
    analyzer = RepoAnalyzer(repo_url=REPO_URL, branch_name=BRANCH_NAME)
    commits = analyzer.get_commit_history(max_commits=MAX_COMMITS)
    merge_requests = analyzer.get_merge_requests(max_requests=MAX_MERGE_REQUESTS)

    print("\nCommits Analyzed:")
    for commit in commits:
        print(f"- [{commit['sha'][:7]}] {commit['message']}")
        print(f"  By {commit['author']} on {commit['date']}")
        print(f"  Files: {', '.join([f['filename'] for f in commit['files']])}\n")
    
    print("\nMerge Requests Analyzed:")
    for mr in merge_requests:
        print(f"- [!{mr['id']}] {mr['title']}")
        print(f"  By {mr['author']} on {mr['merged_at']}")
        print(f"  Files: {', '.join([f['filename'] for f in mr['files']])}\n")
    
    release_notes = generate_release_notes(commits, merge_requests)
    
    print(f"\nGenerated Release Notes for {REPO_URL} (Branch: {BRANCH_NAME})")
    print(release_notes)
    
    with open("release_notes.md", "w") as f:
        f.write(release_notes)