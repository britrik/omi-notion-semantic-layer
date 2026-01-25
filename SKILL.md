# GitHub PR Auto-Responder Agent Skill

## Skill Metadata

**Skill Name**: GitHub PR Auto-Responder
**Version**: 1.0.0
**Category**: Development Automation
**Complexity**: Advanced
**Estimated Duration**: Continuous (monitors PR lifecycle)
**Last Updated**: January 2026

## Description

An automated agent skill that monitors GitHub pull requests, responds to reviewer feedback, automatically fixes formatting and style issues, escalates design decisions to the PR author, and iterates until all reviewers are satisfied.

This skill implements a collaborative PR review workflow that balances automation (for mechanical fixes) with human judgment (for architectural decisions).

## Prerequisites

### Required Tools
- `gh` (GitHub CLI) - version 2.0+
- `git` - version 2.30+
- Code formatting tools appropriate for the repository:
  - Python: `black`, `isort`, `flake8`, `mypy`
  - JavaScript/TypeScript: `prettier`, `eslint`
  - Go: `gofmt`, `golangci-lint`
  - Rust: `rustfmt`, `clippy`

### Installing GitHub CLI (`gh`)

**IMPORTANT**: The GitHub CLI is essential for this skill. Install it before proceeding.

#### macOS
```bash
brew install gh
```

#### Linux (Debian/Ubuntu)
```bash
# Add GitHub CLI repository
sudo mkdir -p -m 755 /etc/apt/keyrings
wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null

# Install
sudo apt update
sudo apt install gh
```

#### Linux (Fedora/RHEL/CentOS)
```bash
sudo dnf install gh
```

#### Linux (Manual Installation - No sudo required)
```bash
# Download and extract to user bin directory
mkdir -p ~/bin
cd /tmp
wget https://github.com/cli/cli/releases/download/v2.62.0/gh_2.62.0_linux_amd64.tar.gz
tar -xzf gh_2.62.0_linux_amd64.tar.gz
cp gh_2.62.0_linux_amd64/bin/gh ~/bin/
export PATH=~/bin:$PATH

# Add to shell profile for persistence
echo 'export PATH=~/bin:$PATH' >> ~/.bashrc
```

#### Windows
```powershell
# Using winget
winget install --id GitHub.cli

# Or using scoop
scoop install gh

# Or download installer from https://cli.github.com/
```

#### Verify Installation
```bash
gh --version
# Should output: gh version 2.0.0 or higher
```

#### Authenticate with GitHub
```bash
# Interactive login
gh auth login

# Or using a personal access token
export GITHUB_TOKEN="ghp_your_token_here"
gh auth login --with-token <<< "$GITHUB_TOKEN"
```

**Token Scopes Required**:
- `repo` (Full control of private repositories)
- `workflow` (Update GitHub Action workflows)
- `read:org` (Read org and team membership)

#### Alternative: Using GitHub API Directly

If `gh` installation is problematic, you can use the GitHub API with `curl`:

```bash
# Set token
export GITHUB_TOKEN="ghp_your_token_here"

# Example: List PRs
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/repos/OWNER/REPO/pulls

# Example: Post comment
curl -X POST \
     -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/repos/OWNER/REPO/issues/PR_NUMBER/comments \
     -d '{"body": "Comment text"}'
```

However, `gh` CLI is strongly recommended as it simplifies authentication and provides better error handling.

### Required Permissions
- GitHub authentication configured (`gh auth login`)
- Write access to the repository
- Ability to push commits to PR branches
- Ability to comment on pull requests

### Environment Variables
```bash
GITHUB_TOKEN          # GitHub personal access token (if not using gh auth)
PR_CHECK_INTERVAL     # Seconds between checks (default: 300)
INITIAL_WAIT_TIME     # Seconds to wait after PR creation (default: 300)
MAX_ITERATIONS        # Maximum auto-fix iterations (default: 10)
```

## Inputs

### Required Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `pr_number` | integer | Pull request number to monitor |
| `repository` | string | Repository in format `owner/repo` |

### Optional Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initial_wait` | integer | 300 | Seconds to wait after PR creation before first check |
| `check_interval` | integer | 300 | Seconds between subsequent checks |
| `auto_fix_enabled` | boolean | true | Enable automatic fixes for style/formatting |
| `escalation_keywords` | array | See below | Keywords that trigger human escalation |
| `max_iterations` | integer | 10 | Maximum number of auto-fix iterations |
| `reviewers_required` | array | [] | Specific reviewers whose approval is required |

### Default Escalation Keywords
```yaml
escalation_keywords:
  - "design"
  - "architecture"
  - "approach"
  - "pattern"
  - "structure"
  - "refactor"
  - "breaking change"
  - "API"
  - "interface"
  - "performance concern"
  - "security concern"
  - "alternative"
  - "consider"
  - "should we"
  - "why"
  - "rationale"
```

## Outputs

### Success Outputs
| Output | Type | Description |
|--------|------|-------------|
| `status` | string | Final status: `approved`, `needs_human_input`, `max_iterations_reached` |
| `iterations_count` | integer | Number of auto-fix iterations performed |
| `fixes_applied` | array | List of automatic fixes applied |
| `escalations` | array | List of comments escalated to PR author |
| `final_approvals` | array | List of reviewers who approved |

### Error Outputs
| Output | Type | Description |
|--------|------|-------------|
| `error_type` | string | Type of error encountered |
| `error_message` | string | Detailed error description |
| `failed_at_iteration` | integer | Iteration number where failure occurred |

## Process Flow

### Phase 1: Initial Wait Period
```
1. PR is created
2. Start timer for initial_wait duration (default: 5 minutes)
3. Log: "Waiting 5 minutes for initial reviewer feedback on PR #${pr_number}"
4. After wait period, proceed to Phase 2
```

**Rationale**: Allows reviewers time to provide comprehensive feedback before automated interventions begin.

### Phase 2: Review Comment Analysis
```
1. Fetch all review comments using gh CLI:
   gh pr view ${pr_number} --repo ${repository} --json reviews,comments

2. Categorize each comment:
   a. FORMATTING/STYLE: Automated fix candidates
      - Indentation issues
      - Missing semicolons
      - Import ordering
      - Line length violations
      - Trailing whitespace
      - Code style violations

   b. DESIGN DECISIONS: Human escalation required
      - Comments containing escalation keywords
      - Questions about approach
      - Architectural concerns
      - Performance/security concerns

   c. INFORMATIONAL: Acknowledge only
      - "LGTM" comments
      - "Approved" status
      - Questions already answered

3. Build action plan based on categorization
```

### Phase 3: Automatic Fixes
```
For each FORMATTING/STYLE issue:
  1. Identify the file and line numbers from comment

  2. Determine appropriate formatter:
     - *.py → black, isort
     - *.js, *.ts, *.tsx → prettier, eslint --fix
     - *.go → gofmt
     - *.rs → rustfmt

  3. Apply formatter to affected files:
     # Example for Python
     black ${affected_files}
     isort ${affected_files}

  4. Verify changes address the comment:
     - Run linter/formatter in check mode
     - Compare before/after diff

  5. Commit changes:
     git add ${affected_files}
     git commit -m "fix: apply formatting fixes for review comments

     Addresses formatting issues raised in review:
     - ${comment_url_1}
     - ${comment_url_2}

     Applied: black, isort"

  6. Push to PR branch:
     git push origin ${branch_name}

  7. Reply to review comment:
     gh pr comment ${pr_number} --body "✅ Formatting issue fixed in commit ${commit_sha}"
```

### Phase 4: Design Decision Escalation
```
For each DESIGN DECISION issue:
  1. Extract the question/concern from comment

  2. Format escalation message to PR author:
     Subject: "Design Decision Needed: ${brief_summary}"

     Body:
     "Hi @${pr_author},

     A reviewer has raised a design question that requires your input:

     **Reviewer**: @${reviewer_username}
     **Comment**: ${comment_body}
     **File**: ${file_path}:${line_number}
     **Link**: ${comment_url}

     **Question Summary**: ${ai_generated_summary}

     **Suggested Actions**:
     ${ai_generated_suggestions}

     Please respond to this comment directly on the PR, and I'll continue
     monitoring for additional feedback.

     ---
     🤖 Automated by GitHub PR Auto-Responder"

  3. Post escalation as PR comment:
     gh pr comment ${pr_number} --body "${escalation_message}"

  4. Mark escalation in tracking system:
     - Record comment ID
     - Track whether author has responded
     - Set flag to re-check this comment
```

### Phase 5: Iteration and Monitoring
```
1. Wait for check_interval duration (default: 5 minutes)

2. Re-fetch PR status:
   - Check for new comments
   - Check review approval status
   - Check if PR author responded to escalations

3. Evaluate exit conditions:

   a. ALL REVIEWERS APPROVED:
      - Log success
      - Post summary comment
      - Exit with status: approved

   b. NEW COMMENTS DETECTED:
      - Return to Phase 2 (Review Comment Analysis)
      - Increment iteration counter

   c. AWAITING HUMAN RESPONSE:
      - Continue monitoring
      - Do not increment iteration counter

   d. MAX ITERATIONS REACHED:
      - Post summary of remaining issues
      - Exit with status: max_iterations_reached

4. If not exiting, repeat Phase 5
```

### Phase 6: Completion and Summary
```
When exit condition is met:

1. Generate comprehensive summary:
   - Total iterations performed
   - Number of auto-fixes applied
   - Number of escalations created
   - Final approval status
   - Remaining open comments (if any)

2. Post summary comment on PR:
   "## 🤖 PR Auto-Responder Summary

   **Status**: ${final_status}
   **Iterations**: ${iteration_count}
   **Auto-fixes Applied**: ${fixes_count}
   **Design Decisions Escalated**: ${escalation_count}

   ### Fixes Applied
   ${list_of_fixes}

   ### Escalations Created
   ${list_of_escalations}

   ### Final Reviewer Status
   ${reviewer_approval_list}

   ${additional_context}"

3. Return structured output for logging/metrics
```

## Implementation Example

### Python Implementation Skeleton
```python
import time
import subprocess
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PRComment:
    id: str
    author: str
    body: str
    path: Optional[str]
    line: Optional[int]
    url: str
    category: str  # 'formatting', 'design', 'informational'

class GitHubPRAutoResponder:
    def __init__(self, pr_number: int, repository: str, **kwargs):
        self.pr_number = pr_number
        self.repository = repository
        self.initial_wait = kwargs.get('initial_wait', 300)
        self.check_interval = kwargs.get('check_interval', 300)
        self.max_iterations = kwargs.get('max_iterations', 10)
        self.escalation_keywords = kwargs.get('escalation_keywords', self._default_keywords())
        self.reviewers_required = kwargs.get('reviewers_required', [])
        self.auto_fix_enabled = kwargs.get('auto_fix_enabled', True)
        self.iteration_count = 0

    def _default_keywords(self) -> List[str]:
        return [
            'design', 'architecture', 'approach', 'pattern',
            'structure', 'refactor', 'breaking change', 'API',
            'interface', 'performance concern', 'security concern',
            'alternative', 'consider', 'should we', 'why', 'rationale'
        ]

    def run(self) -> Dict:
        """Main execution loop"""
        # Phase 1: Initial wait
        print(f"⏳ Waiting {self.initial_wait}s for initial feedback...")
        time.sleep(self.initial_wait)

        # Main monitoring loop
        while self.iteration_count < self.max_iterations:
            # Phase 2: Fetch and analyze comments
            comments = self.fetch_comments()
            categorized = self.categorize_comments(comments)

            # Check for approval
            if self.check_all_approved():
                return self.complete_success()

            # Phase 3: Apply auto-fixes
            if categorized['formatting']:
                self.apply_formatting_fixes(categorized['formatting'])

            # Phase 4: Escalate design decisions
            if categorized['design']:
                self.escalate_to_author(categorized['design'])

            # Phase 5: Wait and iterate
            self.iteration_count += 1
            if self.iteration_count < self.max_iterations:
                time.sleep(self.check_interval)

        return self.complete_max_iterations()

    def fetch_comments(self) -> List[PRComment]:
        """Fetch all PR review comments using gh CLI"""
        result = subprocess.run(
            ['gh', 'pr', 'view', str(self.pr_number),
             '--repo', self.repository,
             '--json', 'reviews,comments'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to fetch PR data: {result.stderr}")

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from gh CLI: {e}")

        # Transform to PRComment objects
        comments = []

        # Process review comments (inline code review comments)
        for review in data.get('reviews', []):
            # Defensive check for review structure
            if not isinstance(review, dict):
                continue

            author_login = review.get('author', {}).get('login', 'unknown')

            for comment in review.get('comments', []):
                if not isinstance(comment, dict):
                    continue

                comments.append(PRComment(
                    id=str(comment.get('id', '')),
                    author=author_login,
                    body=comment.get('body', ''),
                    path=comment.get('path'),
                    line=comment.get('line'),
                    url=comment.get('url', ''),
                    category='unknown'
                ))

        # Process top-level PR conversation comments (not inline)
        for comment in data.get('comments', []):
            if not isinstance(comment, dict):
                continue

            user_info = comment.get('user', {})
            comments.append(PRComment(
                id=str(comment.get('id', '')),
                author=user_info.get('login', 'unknown'),
                body=comment.get('body', ''),
                path=None,  # Top-level comments don't have file paths
                line=None,
                url=comment.get('html_url', ''),
                category='unknown'
            ))

        return comments

    def categorize_comments(self, comments: List[PRComment]) -> Dict[str, List[PRComment]]:
        """Categorize comments into formatting, design, or informational"""
        result = {
            'formatting': [],
            'design': [],
            'informational': []
        }

        for comment in comments:
            body_lower = comment.body.lower()

            # Skip approval/positive comments
            approval_patterns = ['lgtm', 'looks good', 'approved', '✅', 'nice work',
                                'great', 'awesome', 'perfect', 'well done', '👍']
            if any(pattern in body_lower for pattern in approval_patterns):
                comment.category = 'informational'
                result['informational'].append(comment)
                continue

            # Check for escalation keywords (design decisions)
            if any(keyword in body_lower for keyword in self.escalation_keywords):
                comment.category = 'design'
                result['design'].append(comment)
            # Check for formatting indicators (with negative context)
            elif any(indicator in body_lower for indicator in
                    ['formatting', 'style', 'indent', 'whitespace', 'lint']) and \
                 any(negative in body_lower for negative in
                     ['fix', 'need', 'should', 'must', 'please', 'incorrect', 'wrong', 'issue']):
                comment.category = 'formatting'
                result['formatting'].append(comment)
            else:
                comment.category = 'informational'
                result['informational'].append(comment)

        return result

    def apply_formatting_fixes(self, comments: List[PRComment]) -> None:
        """Apply automatic formatting fixes"""
        if not self.auto_fix_enabled:
            print("Auto-fix disabled, skipping formatting fixes")
            return

        affected_files = set()
        formatters_used = set()

        for comment in comments:
            if comment.path:
                affected_files.add(comment.path)

        for file_path in affected_files:
            try:
                formatters = self._format_file(file_path)
                formatters_used.update(formatters)
            except Exception as e:
                print(f"Error formatting {file_path}: {e}")
                continue

        if affected_files:
            self._commit_and_push(list(affected_files), comments, list(formatters_used))

    def _format_file(self, file_path: str) -> List[str]:
        """Format a single file based on its extension"""
        formatters_run = []

        try:
            if file_path.endswith('.py'):
                result = subprocess.run(['black', file_path], capture_output=True, check=False)
                if result.returncode != 0:
                    print(f"Warning: black failed on {file_path}: {result.stderr.decode()}")
                else:
                    formatters_run.append('black')

                result = subprocess.run(['isort', file_path], capture_output=True, check=False)
                if result.returncode != 0:
                    print(f"Warning: isort failed on {file_path}: {result.stderr.decode()}")
                else:
                    formatters_run.append('isort')

            elif file_path.endswith(('.js', '.ts', '.tsx', '.jsx')):
                result = subprocess.run(['prettier', '--write', file_path], capture_output=True, check=False)
                if result.returncode != 0:
                    print(f"Warning: prettier failed on {file_path}: {result.stderr.decode()}")
                else:
                    formatters_run.append('prettier')

                result = subprocess.run(['eslint', '--fix', file_path], capture_output=True, check=False)
                if result.returncode != 0:
                    print(f"Warning: eslint failed on {file_path}: {result.stderr.decode()}")
                else:
                    formatters_run.append('eslint')

            elif file_path.endswith('.go'):
                result = subprocess.run(['gofmt', '-w', file_path], capture_output=True, check=False)
                if result.returncode != 0:
                    print(f"Warning: gofmt failed on {file_path}: {result.stderr.decode()}")
                else:
                    formatters_run.append('gofmt')

            elif file_path.endswith('.rs'):
                result = subprocess.run(['rustfmt', file_path], capture_output=True, check=False)
                if result.returncode != 0:
                    print(f"Warning: rustfmt failed on {file_path}: {result.stderr.decode()}")
                else:
                    formatters_run.append('rustfmt')

        except FileNotFoundError as e:
            print(f"Error: Formatter not found: {e}")
            raise

        return formatters_run

    def _commit_and_push(self, files: List[str], comments: List[PRComment], formatters_used: List[str]) -> None:
        """Commit and push formatting changes"""
        # Check if there are actually changes to commit
        diff_check = subprocess.run(['git', 'diff', '--quiet'] + files, check=False)
        if diff_check.returncode == 0:
            print("No formatting changes detected, skipping commit")
            return

        result = subprocess.run(['git', 'add'] + files, capture_output=True, check=False)
        if result.returncode != 0:
            print(f"Warning: git add failed: {result.stderr.decode()}")
            return

        comment_urls = '\n'.join([f"- {c.url}" for c in comments if c.url])
        formatters_list = ', '.join(formatters_used) if formatters_used else 'automated formatters'

        commit_msg = f"""fix: apply formatting fixes for review comments

Addresses formatting issues raised in review:
{comment_urls}

Applied: {formatters_list}"""

        result = subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            capture_output=True,
            check=False
        )
        if result.returncode != 0:
            print(f"Error: git commit failed: {result.stderr.decode()}")
            return

        # Get current branch
        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            check=False
        )
        if branch_result.returncode != 0:
            print(f"Error: Failed to get current branch: {branch_result.stderr}")
            return

        branch = branch_result.stdout.strip()

        result = subprocess.run(
            ['git', 'push', 'origin', branch],
            capture_output=True,
            check=False
        )
        if result.returncode != 0:
            print(f"Error: git push failed: {result.stderr.decode()}")
            raise RuntimeError(f"Failed to push changes: {result.stderr.decode()}")

    def escalate_to_author(self, comments: List[PRComment]) -> None:
        """Escalate design decisions to PR author"""
        for comment in comments:
            escalation = f"""## 🤔 Design Decision Needed

Hi @{self.get_pr_author()},

A reviewer has raised a design question that requires your input:

**Reviewer**: @{comment.author}
**File**: {comment.path}:{comment.line if comment.line else 'N/A'}
**Link**: {comment.url}

**Comment**:
{comment.body}

Please respond to this comment directly, and I'll continue monitoring for feedback.

---
🤖 Automated by GitHub PR Auto-Responder
"""

            result = subprocess.run(
                ['gh', 'pr', 'comment', str(self.pr_number), '--body', escalation],
                capture_output=True,
                check=False
            )
            if result.returncode != 0:
                print(f"Warning: Failed to post escalation comment: {result.stderr.decode()}")

    def get_pr_author(self) -> str:
        """Get PR author username"""
        result = subprocess.run(
            ['gh', 'pr', 'view', str(self.pr_number),
             '--repo', self.repository,
             '--json', 'author'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to fetch PR author: {result.stderr}")

        try:
            data = json.loads(result.stdout)
            return data.get('author', {}).get('login', 'unknown')
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Invalid response when fetching PR author: {e}")

    def check_all_approved(self) -> bool:
        """Check if all required reviewers have approved"""
        result = subprocess.run(
            ['gh', 'pr', 'view', str(self.pr_number),
             '--repo', self.repository,
             '--json', 'reviewDecision,reviews'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to check approval status: {result.stderr}")

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON when checking approvals: {e}")

        # Check GitHub's overall review decision
        decision = data.get('reviewDecision')

        # If reviewers_required is specified, verify those specific reviewers
        if hasattr(self, 'reviewers_required') and self.reviewers_required:
            approved_reviewers = set()
            for review in data.get('reviews', []):
                if review.get('state') == 'APPROVED':
                    author = review.get('author', {}).get('login')
                    if author:
                        approved_reviewers.add(author)

            # Check if all required reviewers have approved
            required_set = set(self.reviewers_required)
            return required_set.issubset(approved_reviewers)

        # Otherwise, rely on GitHub's decision
        return decision == 'APPROVED'

    def complete_success(self) -> Dict:
        """Handle successful completion"""
        summary = f"""## ✅ PR Auto-Responder Complete

All reviewers have approved!

**Iterations**: {self.iteration_count}
**Status**: Approved

Great work! This PR is ready to merge.
"""
        result = subprocess.run(
            ['gh', 'pr', 'comment', str(self.pr_number), '--body', summary],
            capture_output=True,
            check=False
        )
        if result.returncode != 0:
            print(f"Warning: Failed to post success comment: {result.stderr.decode()}")

        return {
            'status': 'approved',
            'iterations_count': self.iteration_count
        }

    def complete_max_iterations(self) -> Dict:
        """Handle max iterations reached"""
        summary = f"""## ⚠️ PR Auto-Responder - Max Iterations Reached

Reached maximum iteration limit ({self.max_iterations}).

**Iterations Completed**: {self.iteration_count}

Please review remaining comments manually.
"""
        result = subprocess.run(
            ['gh', 'pr', 'comment', str(self.pr_number), '--body', summary],
            capture_output=True,
            check=False
        )
        if result.returncode != 0:
            print(f"Warning: Failed to post max iterations comment: {result.stderr.decode()}")

        return {
            'status': 'max_iterations_reached',
            'iterations_count': self.iteration_count
        }

# Usage
if __name__ == '__main__':
    responder = GitHubPRAutoResponder(
        pr_number=123,
        repository='owner/repo',
        initial_wait=300,  # 5 minutes
        check_interval=300  # 5 minutes
    )
    result = responder.run()
    print(json.dumps(result, indent=2))
```

### Bash Script Alternative
```bash
#!/bin/bash
# GitHub PR Auto-Responder - Bash Implementation

set -eo pipefail  # Removed -u to allow error recovery with || patterns

PR_NUMBER="${1}"
REPOSITORY="${2}"
INITIAL_WAIT="${3:-300}"
CHECK_INTERVAL="${4:-300}"
MAX_ITERATIONS="${5:-10}"

iteration=0

# Phase 1: Initial wait
echo "⏳ Waiting ${INITIAL_WAIT}s for initial reviewer feedback on PR #${PR_NUMBER}..."
sleep "${INITIAL_WAIT}"

# Main loop
while [ $iteration -lt $MAX_ITERATIONS ]; do
    echo "🔍 Iteration $((iteration + 1)): Checking PR #${PR_NUMBER}..."

    # Fetch review status
    review_decision=$(gh pr view "${PR_NUMBER}" \
        --repo "${REPOSITORY}" \
        --json reviewDecision \
        --jq '.reviewDecision')

    # Check if approved
    if [ "${review_decision}" = "APPROVED" ]; then
        echo "✅ All reviewers approved!"
        gh pr comment "${PR_NUMBER}" --body "## ✅ PR Auto-Responder Complete

All reviewers have approved!

**Iterations**: $((iteration + 1))
**Status**: Approved"
        exit 0
    fi

    # Fetch review comments with file paths
    gh pr view "${PR_NUMBER}" \
        --repo "${REPOSITORY}" \
        --json reviews \
        --jq '.reviews[].comments[]? | "\(.path)|\(.body)"' > /tmp/pr_review_comments.txt

    # Fetch general PR comments
    gh pr view "${PR_NUMBER}" \
        --repo "${REPOSITORY}" \
        --json comments \
        --jq '.comments[] | "|\(.body)"' >> /tmp/pr_review_comments.txt

    # Process formatting issues (only on files mentioned in reviews)
    if grep -qi "formatting\|style\|lint" /tmp/pr_review_comments.txt; then
        echo "🔧 Applying formatting fixes..."

        # Extract unique file paths from review comments that mention formatting
        affected_files=$(grep -i "formatting\|style\|lint" /tmp/pr_review_comments.txt | \
            cut -d'|' -f1 | \
            grep -v '^$' | \
            sort -u)

        if [ -n "${affected_files}" ]; then
            # Run formatters only on affected files
            for file in ${affected_files}; do
                if [ -f "${file}" ]; then
                    case "${file}" in
                        *.py)
                            black "${file}" 2>&1 || echo "Warning: black failed on ${file}"
                            isort "${file}" 2>&1 || echo "Warning: isort failed on ${file}"
                            ;;
                        *.js|*.ts|*.tsx|*.jsx)
                            prettier --write "${file}" 2>&1 || echo "Warning: prettier failed on ${file}"
                            ;;
                        *.go)
                            gofmt -w "${file}" 2>&1 || echo "Warning: gofmt failed on ${file}"
                            ;;
                        *.rs)
                            rustfmt "${file}" 2>&1 || echo "Warning: rustfmt failed on ${file}"
                            ;;
                    esac
                fi
            done

            # Commit if changes exist
            if ! git diff --quiet; then
                git add -A
                git commit -m "fix: apply formatting fixes for review comments"
                git push origin "$(git rev-parse --abbrev-ref HEAD)"

                gh pr comment "${PR_NUMBER}" --body "✅ Applied formatting fixes to reviewed files"
            fi
        fi
    fi

    # Check for design decision keywords
    if grep -qiE "design|architecture|approach|why|rationale" /tmp/pr_review_comments.txt; then
        echo "🤔 Design decisions detected - escalating to PR author"

        pr_author=$(gh pr view "${PR_NUMBER}" \
            --repo "${REPOSITORY}" \
            --json author \
            --jq '.author.login')

        gh pr comment "${PR_NUMBER}" --body "## 🤔 Design Decision Needed

Hi @${pr_author}, some reviewers have raised design questions that need your input.

Please review the comments and respond directly."
    fi

    iteration=$((iteration + 1))

    if [ $iteration -lt $MAX_ITERATIONS ]; then
        echo "⏳ Waiting ${CHECK_INTERVAL}s before next check..."
        sleep "${CHECK_INTERVAL}"
    fi
done

echo "⚠️ Max iterations reached"
gh pr comment "${PR_NUMBER}" --body "## ⚠️ Max Iterations Reached

Completed ${MAX_ITERATIONS} iterations. Please review remaining comments manually."
```

## Error Handling

### Common Errors and Resolutions

| Error | Cause | Resolution |
|-------|-------|------------|
| `gh: command not found` | GitHub CLI not installed | Install gh CLI: `brew install gh` or equivalent |
| `gh auth required` | Not authenticated | Run `gh auth login` |
| `Permission denied (push)` | No write access to branch | Verify repository permissions |
| `Formatter not found` | Missing code formatter | Install required formatter for file type |
| `PR not found` | Invalid PR number or repo | Verify PR number and repository format |
| `API rate limit exceeded` | Too many GitHub API calls | Increase check_interval, wait for rate limit reset |
| `Merge conflict` | Branch conflicts with base | Escalate to human - cannot auto-resolve |

### Escalation Triggers

Automatically escalate to human intervention when:
- Merge conflicts detected
- Tests fail after auto-fix
- Unable to determine appropriate formatter
- Same comment appears in 3+ iterations (infinite loop)
- PR author explicitly requests manual review
- Security-related comments detected

## Best Practices

1. **Conservative Auto-Fixing**: Only fix formatting/style issues that are mechanical and unambiguous
2. **Clear Communication**: Always explain what was changed and why
3. **Respect Human Input**: Never override explicit reviewer requests
4. **Graceful Degradation**: If uncertain, escalate rather than guess
5. **Audit Trail**: Maintain clear commit messages linking to review comments
6. **Rate Limiting**: Respect GitHub API limits with appropriate intervals
7. **Idempotency**: Ensure running multiple times doesn't cause duplicate actions

## Metrics and Monitoring

Track the following metrics for optimization:
- Average iterations to approval
- Auto-fix success rate (fixes accepted without further comments)
- Escalation rate
- Time to resolution
- Formatter coverage (% of file types supported)
- False positive rate (incorrect categorizations)

## Security Considerations

- **Code Execution**: Only run trusted formatters; verify formatter binaries
- **Credentials**: Use GitHub tokens with minimal required scopes
- **Secrets**: Never commit or expose GitHub tokens in logs
- **Validation**: Validate all input from GitHub API
- **Sandboxing**: Run formatters in isolated environment when possible

## Customization

### Adding New Formatters
```python
FORMATTERS = {
    '.py': ['black', 'isort'],
    '.js': ['prettier --write'],
    '.go': ['gofmt -w'],
    '.rs': ['rustfmt'],
    # Add custom formatters here
    '.java': ['google-java-format --replace'],
    '.rb': ['rubocop --auto-correct'],
}
```

### Custom Escalation Rules
```python
def should_escalate(comment: PRComment) -> bool:
    """Custom escalation logic"""
    # Example: Escalate comments from specific reviewers
    if comment.author in ['tech-lead', 'architect']:
        return True

    # Example: Escalate based on comment length (complex discussions)
    if len(comment.body) > 500:
        return True

    # Default keyword matching
    return any(kw in comment.body.lower() for kw in ESCALATION_KEYWORDS)
```

## Integration Examples

### GitHub Actions Workflow
```yaml
name: PR Auto-Responder

on:
  pull_request:
    types: [opened, synchronize]
  pull_request_review:
    types: [submitted]
  pull_request_review_comment:
    types: [created]

jobs:
  auto-respond:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.ref }}

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install black isort flake8
          npm install -g prettier eslint

      - name: Run PR Auto-Responder
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python pr_auto_responder.py \
            --pr-number ${{ github.event.pull_request.number }} \
            --repository ${{ github.repository }} \
            --initial-wait 300 \
            --check-interval 300
```

### Standalone Service
```python
# pr_service.py - Run as a continuous service
from github_pr_auto_responder import GitHubPRAutoResponder
import os
import time
import subprocess
import json
from threading import Thread, Lock
from typing import Set, Tuple

# Global tracking to prevent duplicate operations
_active_prs_lock = Lock()
_active_prs: Set[Tuple[str, int]] = set()

def monitor_repository(repo: str):
    """Monitor all open PRs in a repository"""
    while True:
        try:
            # Get all open PRs
            result = subprocess.run(
                ['gh', 'pr', 'list', '--repo', repo, '--json', 'number'],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"Error fetching PRs for {repo}: {result.stderr}")
                time.sleep(600)
                continue

            prs = json.loads(result.stdout)

            # Launch responder for each PR (with deduplication)
            for pr in prs:
                pr_number = pr.get('number')
                if not pr_number:
                    continue

                pr_key = (repo, pr_number)

                # Check if already being monitored
                with _active_prs_lock:
                    if pr_key in _active_prs:
                        continue  # Skip, already being handled
                    _active_prs.add(pr_key)

                # Launch monitoring thread for this PR
                def run_responder(repository, pr_num, key):
                    try:
                        GitHubPRAutoResponder(
                            pr_number=pr_num,
                            repository=repository
                        ).run()
                    finally:
                        # Remove from active set when done
                        with _active_prs_lock:
                            _active_prs.discard(key)

                thread = Thread(
                    target=run_responder,
                    args=(repo, pr_number, pr_key),
                    daemon=True
                )
                thread.start()

        except Exception as e:
            print(f"Error in monitor_repository for {repo}: {e}")

        time.sleep(600)  # Check for new PRs every 10 minutes

if __name__ == '__main__':
    repos = os.getenv('WATCHED_REPOS', '').split(',')
    repos = [r.strip() for r in repos if r.strip()]

    if not repos:
        print("No repositories configured in WATCHED_REPOS")
        exit(1)

    print(f"Starting PR auto-responder service for: {repos}")

    threads = []
    for repo in repos:
        thread = Thread(target=monitor_repository, args=(repo,), daemon=True)
        thread.start()
        threads.append(thread)

    # Keep main thread alive
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nShutting down PR auto-responder service")
```

## Testing

### Unit Test Example
```python
import unittest
from unittest.mock import patch, MagicMock
from github_pr_auto_responder import GitHubPRAutoResponder, PRComment

class TestPRAutoResponder(unittest.TestCase):
    def setUp(self):
        self.responder = GitHubPRAutoResponder(
            pr_number=123,
            repository='test/repo',
            initial_wait=0,
            check_interval=0
        )

    def test_categorize_formatting_comment(self):
        comment = PRComment(
            id='1',
            author='reviewer',
            body='Please fix the formatting in this file',
            path='test.py',
            line=10,
            url='https://github.com/test/repo/pull/123#comment-1',
            category='unknown'
        )

        result = self.responder.categorize_comments([comment])
        self.assertEqual(len(result['formatting']), 1)
        self.assertEqual(result['formatting'][0].category, 'formatting')

    def test_categorize_design_comment(self):
        comment = PRComment(
            id='2',
            author='reviewer',
            body='Why did you choose this architecture approach?',
            path='test.py',
            line=20,
            url='https://github.com/test/repo/pull/123#comment-2',
            category='unknown'
        )

        result = self.responder.categorize_comments([comment])
        self.assertEqual(len(result['design']), 1)
        self.assertEqual(result['design'][0].category, 'design')

    @patch('subprocess.run')
    def test_apply_formatting_fixes(self, mock_run):
        comment = PRComment(
            id='3',
            author='reviewer',
            body='Format this file',
            path='test.py',
            line=30,
            url='https://github.com/test/repo/pull/123#comment-3',
            category='formatting'
        )

        self.responder.apply_formatting_fixes([comment])

        # Verify black and isort were called
        calls = [str(call) for call in mock_run.call_args_list]
        self.assertTrue(any('black' in call for call in calls))
        self.assertTrue(any('isort' in call for call in calls))

if __name__ == '__main__':
    unittest.main()
```

## Troubleshooting

### Debug Mode
Enable verbose logging by setting environment variable:
```bash
export PR_AUTO_RESPONDER_DEBUG=1
```

### Manual Override
To pause the auto-responder on a specific PR, add a label:
```bash
gh pr edit ${PR_NUMBER} --add-label "no-auto-respond"
```

### Reviewing Auto-Responder Actions
Check the audit log by viewing commits and comments from the bot account:
```bash
gh pr view ${PR_NUMBER} --json commits,comments \
  | jq '.commits[] | select(.author.login == "github-actions[bot]")'
```

## Related Skills

- **CI/CD Pipeline Manager**: Monitors test results and deployment status
- **Code Review Assistant**: Provides AI-powered code review suggestions
- **Dependency Update Manager**: Automatically updates and tests dependency changes
- **Documentation Sync**: Keeps documentation in sync with code changes

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01 | Initial release with core functionality |

## License

MIT License - See repository LICENSE file for details

## Support

For issues or questions:
- Open an issue in the repository
- Tag with `skill:pr-auto-responder`
- Provide PR number and repository for context

---

**Note**: This is an agent skill specification designed to be executed by AI agents or automated systems with appropriate permissions and safety controls. Always review auto-generated commits before merging to production.
