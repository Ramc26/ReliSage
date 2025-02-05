import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from urllib.parse import urlparse


# Load environment variables
load_dotenv()


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class GitHubRepoAnalyzer:
   def __init__(self, repo_url):
       self.repo_url = repo_url
       self.headers = {
           "Authorization": f"Bearer {GITHUB_TOKEN}",
           "Accept": "application/vnd.github+json"
       }
       self.owner, self.repo = self._parse_repo_url()


   def _parse_repo_url(self):
       path = urlparse(self.repo_url).path.strip("/")
       parts = path.split("/")
       return parts[0], parts[1]


   def get_commit_history(self, max_commits=10):
       url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits"
       print(f"Repo URL:{url}")
       params = {"per_page": max_commits}
       response = requests.get(url, headers=self.headers, params=params)
       response.raise_for_status()
      
       commits = []
       for commit in response.json():
           commit_details = self._get_commit_details(commit['sha'])
           commits.append({
               "sha": commit['sha'],
               "message": commit_details['commit']['message'],
               "author": commit_details['commit']['author']['name'],
               "date": commit_details['commit']['author']['date'],
               "files": [f"{f['filename']} ({f['changes']} changes)" for f in commit_details['files']],
               "diff": self._get_commit_diff(commit['sha'])
           })
        #    print("Commits: {}".format(commits))
       return commits


   def _get_commit_details(self, sha):
       url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/{sha}"
       response = requests.get(url, headers=self.headers)
       response.raise_for_status()
       return response.json()


   def _get_commit_diff(self, sha):
       url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/{sha}"
       headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
       response = requests.get(url, headers=headers)
       response.raise_for_status()
       return response.text


def generate_release_notes(commits):
   llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.3)
  
   prompt = f"""Generate comprehensive release notes from these GitHub commits. Analyze code changes and commit messages to create detailed, organized release notes.


   For each significant change, include:
   - Purpose of the change
   - Affected files/components
   - Technical implementation details
   - User impact
  
   Structure the notes with:
   1. Summary
   2. New Features
   3. Improvements
   4. Bug Fixes
   5. Technical Changes
   6. Full File Change List
  
   Commit Details:
   {commits}


   Output in markdown with clear section headers and bullet points. Be technical but maintain readability.
   """
  
   response = llm.invoke(prompt)
   return response.content


if __name__ == "__main__":
   # Configuration
   REPO_URL = "https://github.com/Ramc26/RN-AI"  # Replace with your repo URL
   MAX_COMMITS = 2  # Number of commits to analyze


   # Initialize analyzer
   analyzer = GitHubRepoAnalyzer(REPO_URL)
  
   # Get detailed commit history
   commits = analyzer.get_commit_history(MAX_COMMITS)
   print("Commits:", commits)
   # Generate release notes
   release_notes = generate_release_notes(commits)
  
   # Save and print results
   print("Generated Release Notes:")
   print(release_notes)
   with open("../RELEASE_NOTES.md", "w") as f:
       f.write(release_notes)
