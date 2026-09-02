How to Use
Follow the steps below to run the GitHub Commit Scanner.

1. Check for GitHub Token
Open the terminal in VS Code and run:

DOS
echo %GITHUB_TOKEN%
If your GitHub authentication token is displayed, skip to Step 3.

If nothing is displayed, continue to Step 2.

Note: Never share your GitHub token with anyone or upload it to GitHub.

2. Create and Set a GitHub Token
Create a GitHub Personal Access Token from your GitHub account.

After creating the token, set it in your current terminal session using:

DOS
set GITHUB_TOKEN=YOUR_GITHUB_TOKEN_HERE
For example:

DOS
set GITHUB_TOKEN=github_pat_xxxxxxxxxxxxxxxxx
Verify that the token is set:

DOS
echo %GITHUB_TOKEN%
If the token is displayed, you can proceed to Step 3.

Security: Do not put your token directly inside scanner.py, repositories.csv, or any file that will be uploaded to GitHub.

3. Prepare the Repository CSV
Create a CSV file named:

Plaintext
repositories.csv
The CSV must contain a column named exactly:

Plaintext
repository
New Feature: You can now include any additional columns you want (such as Team Name, Problem Statement, or Submission Date). The scanner will safely preserve all of your original data and attach the GitHub results to the end of each row.

Example format:

Code snippet
Team Name,Problem Statement,repository,Submission Date
Team ByteCraft,SIH1045,https://github.com/octocat/Hello-World,2026-08-25
Team Syntax Error,SIH1092,https://github.com/microsoft/vscode,2026-08-28
Team Null Pointer,SIH1105,https://github.com/user/example-repository,2026-08-30
4. Run the Scanner
Open the terminal in the folder containing scanner.py and run:

DOS
python scanner.py repositories.csv {date} --output {outputcsv}
Replace:

{date} with the cutoff date in YYYY-MM-DD format.

{outputcsv} with the name you want for the output file.

Example
DOS
python scanner.py repositories.csv 2026-08-20 --output custom_report.csv
This means:

Scan all repositories in repositories.csv and check whether their latest commit was made after August 20, 2026.

5. View the Results
After the scan finishes, a new CSV file will be created using the output filename you provided.

For example:

Plaintext
custom_report.csv
The report will contain all of your original columns (like Team Name), plus the newly generated information:

Repository URL

Latest commit date

Latest commit SHA

Latest commit message

Latest commit URL

Last commit before/on the cutoff date

Last commit SHA

Last commit message

Last commit URL

Repository status (ON_TIME, LATE, INVALID_URL, ERROR, etc.)

You can open the generated CSV using Microsoft Excel, Google Sheets, or VS Code.

6. Example Workflow
Your project folder can look like this:

Plaintext
github-commit-scanner/
│
├── scanner.py
├── repositories.csv
└── custom_report.csv
Then run:

DOS
python scanner.py repositories.csv 2026-08-20 --output custom_report.csv
The program will:

Plaintext
CSV file
   ↓
Read repository URLs & preserve row data
   ↓
Connect to GitHub API
   ↓
Check commit history
   ↓
Compare commits with cutoff date
   ↓
Find the last commit before/on cutoff
   ↓
Merge GitHub data with original row data
   ↓
Generate detailed output CSV
7. Get Help
To see all available command-line options, run:

DOS
python scanner.py --help
This displays the available arguments and an example command.

Important
The cutoff date must use the format YYYY-MM-DD.

A valid GitHub token is recommended to avoid GitHub API rate limits.

Do not share your GitHub token.

Do not commit your GitHub token to a public GitHub repository.