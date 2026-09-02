import os
import sys
import argparse
from urllib.parse import urlparse
from datetime import datetime, timezone
import requests
import pandas as pd


def read_repositories(file_path):
    """
    Reads the input CSV file and extracts repository URLs.
    
    Args:
        file_path (str): Path to the CSV file.
        
    Returns:
        list: A list of repository URL strings.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")
        
    # Check if 'repository' column exists (case-insensitive check)
    column_map = {col.lower().strip(): col for col in df.columns}
    if 'repository' not in column_map:
        raise KeyError("Input CSV must contain a 'repository' column.")
        
    repo_column = column_map['repository']
    # Filter out empty rows and strip whitespace
    urls = df[repo_column].dropna().astype(str).str.strip().tolist()
    return urls


def parse_github_url(url):
    """
    Extracts owner and repo name from a GitHub URL.
    Handles trailing slashes and non-standard URL formats safely.
    
    Args:
        url (str): Full GitHub repository URL.
        
    Returns:
        tuple: (owner, repo) strings if valid, else (None, None).
    """
    try:
        parsed = urlparse(url)
        if parsed.netloc not in ["github.com", "www.github.com"]:
            return None, None
            
        # Split path segments and filter out empty strings (handles trailing slashes)
        path_parts = [part for part in parsed.path.split("/") if part]
        
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo = path_parts[1]
            # Strip '.git' if present at the end of the repository name
            if repo.endswith(".git"):
                repo = repo[:-4]
            return owner, repo
        return None, None
    except Exception:
        return None, None


def get_headers():
    """
    Retrieves request headers with GITHUB_TOKEN if present in environment variables.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    
    # Only attach Authorization header if token is a valid non-empty string
    if token and token.strip():
        headers["Authorization"] = f"token {token.strip()}"
        
    return headers


def fetch_commits_from_api(owner, repo):
    """
    Fetches the commit history for a repository using GitHub REST API.
    
    Args:
        owner (str): GitHub repository owner.
        repo (str): GitHub repository name.
        
    Returns:
        tuple: (commits_list, error_message)
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    headers = get_headers()
    
    try:
        # Fetch up to 100 recent commits (default branch)
        response = requests.get(url, headers=headers, params={"per_page": 100}, timeout=10)
        
        if response.status_code == 200:
            return response.json(), None
        elif response.status_code == 404:
            return None, "Repository not found or private without token access"
        elif response.status_code == 403:
            if "rate limit" in response.text.lower():
                return None, "GitHub API rate limit exceeded. Set GITHUB_TOKEN environment variable."
            return None, "Access forbidden (check permissions/token)"
        elif response.status_code == 409:
            return None, "Repository is empty (no commits)"
        else:
            return None, f"GitHub API Error HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return None, "Network request timed out"
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"


def parse_commit_date(date_str):
    """
    Parses ISO 8601 date strings returned by GitHub API into standard UTC datetime objects.
    """
    # Handles ISO formats like '2026-08-20T14:30:00Z'
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc)


def process_repository(url, cutoff_utc):
    """
    Evaluates commit history for a single repository against the cutoff date.
    
    Args:
        url (str): GitHub repository URL.
        cutoff_utc (datetime): Timezone-aware cutoff datetime object.
        
    Returns:
        dict: Processed output information record.
    """
    record = {
        "repository": url,
        "latest_commit_date": "N/A",
        "latest_commit_sha": "N/A",
        "latest_commit_message": "N/A",
        "latest_commit_url": "N/A",
        "last_commit_before_cutoff_date": "N/A",
        "last_commit_before_cutoff_sha": "N/A",
        "last_commit_before_cutoff_message": "N/A",
        "last_commit_before_cutoff_url": "N/A",
        "status": "ERROR"
    }

    owner, repo = parse_github_url(url)
    if not owner or not repo:
        record["status"] = "INVALID_URL"
        return record

    commits, error = fetch_commits_from_api(owner, repo)
    if error:
        record["status"] = f"ERROR: {error}"
        return record

    if not commits or not isinstance(commits, list):
        record["status"] = "NO_COMMITS_FOUND"
        return record

    # GitHub REST API returns commits ordered from most recent to oldest
    latest_commit = commits[0]
    latest_date_utc = parse_commit_date(latest_commit["commit"]["committer"]["date"])
    full_latest_sha = latest_commit["sha"]
    
    record["latest_commit_date"] = latest_date_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    record["latest_commit_sha"] = full_latest_sha[:7]  # Shortened to 7 chars
    record["latest_commit_message"] = latest_commit["commit"]["message"].split("\n")[0]  # First line only
    record["latest_commit_url"] = f"https://github.com/{owner}/{repo}/commit/{full_latest_sha}"

    # Check if latest commit happened AFTER cutoff date
    if latest_date_utc > cutoff_utc:
        record["status"] = "LATE"
    else:
        record["status"] = "ON_TIME"

    # Find the most recent commit on or before the cutoff date
    commit_before_cutoff = None
    for commit in commits:
        c_date = parse_commit_date(commit["commit"]["committer"]["date"])
        if c_date <= cutoff_utc:
            commit_before_cutoff = commit
            break

    if commit_before_cutoff:
        c_date = parse_commit_date(commit_before_cutoff["commit"]["committer"]["date"])
        full_cutoff_sha = commit_before_cutoff["sha"]
        record["last_commit_before_cutoff_date"] = c_date.strftime("%Y-%m-%d %H:%M:%S UTC")
        record["last_commit_before_cutoff_sha"] = full_cutoff_sha[:7]  # Shortened to 7 chars
        record["last_commit_before_cutoff_message"] = commit_before_cutoff["commit"]["message"].split("\n")[0]
        record["last_commit_before_cutoff_url"] = f"https://github.com/{owner}/{repo}/commit/{full_cutoff_sha}"
    else:
        record["last_commit_before_cutoff_date"] = "NONE"
        record["last_commit_before_cutoff_url"] = "NONE"

    return record


def write_results(results, output_file):
    """
    Saves scan results into a formatted CSV output file using pandas.
    """
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"\n[+] Results successfully written to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Scan GitHub repositories to check submission dates against a cutoff deadline.",
        epilog="Example usage: python scanner.py repositories.csv 2026-08-20 --output late_repos.csv"
    )
    
    parser.add_argument("csv_file", help="Path to input CSV file containing 'repository' column.")
    parser.add_argument("cutoff_date", help="Cutoff date in YYYY-MM-DD format.")
    parser.add_argument(
        "-o", "--output", 
        default="late_repositories.csv", 
        help="Path for saving output CSV (default: late_repositories.csv)"
    )

    args = parser.parse_args()

    # Validate cutoff date format
    try:
        base_date = datetime.strptime(args.cutoff_date, "%Y-%m-%d")
        # Define cutoff as end-of-day (23:59:59 UTC)
        cutoff_utc = datetime(
            base_date.year, base_date.month, base_date.day, 
            23, 59, 59, tzinfo=timezone.utc
        )
    except ValueError:
        print(f"[-] Error: Invalid date format '{args.cutoff_date}'. Please use YYYY-MM-DD format.")
        sys.exit(1)

    # Read CSV
    try:
        urls = read_repositories(args.csv_file)
    except Exception as e:
        print(f"[-] Error reading CSV file: {e}")
        sys.exit(1)

    print(f"[*] Loaded {len(urls)} repositories from {args.csv_file}")
    print(f"[*] Cutoff Date set to: {cutoff_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("-" * 60)

    results = []
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] Scanning: {url} ...", end=" ", flush=True)
        record = process_repository(url, cutoff_utc)
        print(f"[{record['status']}]")
        results.append(record)

    write_results(results, args.output)


if __name__ == "__main__":
    main()