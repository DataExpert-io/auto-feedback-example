import os
import sys
import requests
from util import get_logger, get_changed_files
from openai import OpenAI
from github import Github

GIT_TOKEN = os.environ.get('GIT_TOKEN')
GIT_REPO = os.environ.get('GITHUB_REPOSITORY')
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
    raise ValueError("You need to specify OPENAI_API_KEY environment variable!")

logger = get_logger()
client = OpenAI(api_key=OPENAI_API_KEY)

def get_pr_files(pr_number):
    g = Github(os.getenv('GITHUB_TOKEN'))
    repo = g.get_repo(os.getenv('GITHUB_REPOSITORY'))
    pr = repo.get_pull(pr_number)
    files = pr.get_files()
    changes = [f.filename for f in files]
    return changes


def get_feedback(filename: str, system_prompt: str, user_prompt: str) -> str:
  comment = ''
  response = client.chat.completions.create(
      model="gpt-4",
      messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt},
      ],
      temperature=0,
  )
  comment = response.choices[0].message.content
  text = f"This is a LLM-generated comment for `{filename}`: \n{comment if comment else 'Tests passed. No feedback generated for testing purposes.'}"
  return text


def post_github_comment(git_token, repo, pr_number, comment, filename):
  url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
  headers = {
      "Accept": "application/vnd.github+json",
      "Authorization": f"Bearer {git_token}",
      "X-GitHub-Api-Version": "2022-11-28"
  }
  data = {"body": comment}
  response = requests.post(url, headers=headers, json=data)
  if response.status_code != 201:
    logger.error(f"Failed to create comment. Status code: {response.status_code} \n{response.text}")
    raise Exception(f"Failed to create comment. Status code: {response.status_code} \n{response.text}")
  logger.info(f"✅ Added review comment for {filename} at https://github.com/{repo}/pull/{pr_number}")


def main(files_to_process: list):
  if not files_to_process:
    logger.warning('No file changes were detected in the current push so no comments were generated. Please modify one or more of your submission files to receive LLM-generated feedback.')
    return None
  local_solutions_dir = os.path.join(os.getcwd(), 'src')
  os.makedirs(local_solutions_dir, exist_ok=True)
  system_prompt = """
    You are a senior software engineer looking to give feedback on every PR you see in this repo
  
  """
  for filename in files_to_process:
    file_path = os.path.join('src', filename)
    if file_path in files_to_process:
      prompt = f"Make sure this file {file_path} follows all the right naming and python conventions. Make any call outs you see!"
      comment = get_feedback(filename, system_prompt, prompt)
      if GIT_TOKEN and GIT_REPO and pr_number:
          post_github_comment(GIT_TOKEN, GIT_REPO, pr_number, comment, filename)

if __name__ == "__main__":
  pr_number = int(sys.argv[1])
  changes = get_pr_files(pr_number)
  files_to_process = get_changed_files()
  main(files_to_process)