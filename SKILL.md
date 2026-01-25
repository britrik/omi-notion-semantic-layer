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
            text=True
        )
        data = json.loads(result.stdout)

        # Transform to PRComment objects
        comments = []
        # Process reviews
        for review in data.get('reviews', []):
            for comment in review.get('comments', []):
                comments.append(PRComment(
                    id=comment['id'],
                    author=review['author']['login'],
                    body=comment['body'],
                    path=comment.get('path'),
                    line=comment.get('line'),
                    url=comment['url'],
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

            # Check for escalation keywords (design decisions)
            if any(keyword in body_lower for keyword in self.escalation_keywords):
                comment.category = 'design'
                result['design'].append(comment)
            # Check for formatting indicators
            elif any(indicator in body_lower for indicator in
                    ['formatting', 'style', 'indent', 'whitespace', 'lint']):
                comment.category = 'formatting'
                result['formatting'].append(comment)
            else:
                comment.category = 'informational'
                result['informational'].append(comment)

        return result

    def apply_formatting_fixes(self, comments: List[PRComment]) -> None:
        """Apply automatic formatting fixes"""
        affected_files = set()

        for comment in comments:
            if comment.path:
                affected_files.add(comment.path)

        for file_path in affected_files:
            self._format_file(file_path)

        if affected_files:
            self._commit_and_push(list(affected_files), comments)

    def _format_file(self, file_path: str) -> None:
        """Format a single file based on its extension"""
        if file_path.endswith('.py'):
            subprocess.run(['black', file_path])
            subprocess.run(['isort', file_path])
        elif file_path.endswith(('.js', '.ts', '.tsx', '.jsx')):
            subprocess.run(['prettier', '--write', file_path])
            subprocess.run(['eslint', '--fix', file_path])
        elif file_path.endswith('.go'):
            subprocess.run(['gofmt', '-w', file_path])
        elif file_path.endswith('.rs'):
            subprocess.run(['rustfmt', file_path])

    def _commit_and_push(self, files: List[str], comments: List[PRComment]) -> None:
        """Commit and push formatting changes"""
        subprocess.run(['git', 'add'] + files)

        comment_urls = '\n'.join([f"- {c.url}" for c in comments])
        commit_msg = f"""fix: apply formatting fixes for review comments

Addresses formatting issues raised in review:
{comment_urls}

Applied automated formatting."""

        subprocess.run(['git', 'commit', '-m', commit_msg])

        # Get current branch
        branch = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True
        ).stdout.strip()

        subprocess.run(['git', 'push', 'origin', branch])

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

            subprocess.run([
                'gh', 'pr', 'comment', str(self.pr_number),
                '--body', escalation
            ])

    def get_pr_author(self) -> str:
        """Get PR author username"""
        result = subprocess.run(
            ['gh', 'pr', 'view', str(self.pr_number),
             '--repo', self.repository,
             '--json', 'author'],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)['author']['login']

    def check_all_approved(self) -> bool:
        """Check if all required reviewers have approved"""
        result = subprocess.run(
            ['gh', 'pr', 'view', str(self.pr_number),
             '--repo', self.repository,
             '--json', 'reviewDecision'],
            capture_output=True,
            text=True
        )
        decision = json.loads(result.stdout).get('reviewDecision')
        return decision == 'APPROVED'

    def complete_success(self) -> Dict:
        """Handle successful completion"""
        summary = f"""## ✅ PR Auto-Responder Complete

All reviewers have approved!

**Iterations**: {self.iteration_count}
**Status**: Approved

Great work! This PR is ready to merge.
"""
        subprocess.run([
            'gh', 'pr', 'comment', str(self.pr_number),
            '--body', summary
        ])

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
        subprocess.run([
            'gh', 'pr', 'comment', str(self.pr_number),
            '--body', summary
        ])

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

set -euo pipefail

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

    # Fetch comments
    gh pr view "${PR_NUMBER}" \
        --repo "${REPOSITORY}" \
        --json comments \
        --jq '.comments[] | "\(.author.login)|\(.body)"' > /tmp/pr_comments.txt

    # Process formatting issues (simplified)
    if grep -qi "formatting\|style\|lint" /tmp/pr_comments.txt; then
        echo "🔧 Applying formatting fixes..."

        # Run formatters based on repository
        find . -name "*.py" -exec black {} +
        find . -name "*.py" -exec isort {} +

        # Commit if changes exist
        if ! git diff --quiet; then
            git add -A
            git commit -m "fix: apply formatting fixes for review comments"
            git push origin "$(git rev-parse --abbrev-ref HEAD)"

            gh pr comment "${PR_NUMBER}" --body "✅ Applied formatting fixes"
        fi
    fi

    # Check for design decision keywords
    if grep -qiE "design|architecture|approach|why|rationale" /tmp/pr_comments.txt; then
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
from threading import Thread

def monitor_repository(repo: str):
    """Monitor all open PRs in a repository"""
    while True:
        # Get all open PRs
        result = subprocess.run(
            ['gh', 'pr', 'list', '--repo', repo, '--json', 'number'],
            capture_output=True, text=True
        )
        prs = json.loads(result.stdout)

        # Launch responder for each PR
        for pr in prs:
            thread = Thread(target=lambda: GitHubPRAutoResponder(
                pr_number=pr['number'],
                repository=repo
            ).run())
            thread.start()

        time.sleep(600)  # Check for new PRs every 10 minutes

if __name__ == '__main__':
    repos = os.getenv('WATCHED_REPOS', '').split(',')
    for repo in repos:
        Thread(target=monitor_repository, args=(repo,)).start()
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
