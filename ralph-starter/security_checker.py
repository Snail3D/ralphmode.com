"""
Security Checker - OB-051
Scans projects for hardcoded secrets and security misconfigurations.
Ralph walks users through fixing security issues during onboarding.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class SecurityIssue:
    """Represents a security issue found during scanning."""
    severity: str  # "critical", "warning", "info"
    file_path: str
    line_number: int
    issue_type: str
    description: str
    suggestion: str


class SecurityChecker:
    """
    Scans projects for security issues and provides Ralph-style guidance.

    Checks:
    - Hardcoded API keys, passwords, tokens
    - .env file existence and content
    - .gitignore configuration
    - Secrets in tracked files
    """

    # Patterns for common secrets (case-insensitive)
    SECRET_PATTERNS = [
        (r'api[_-]?key\s*=\s*["\']([^"\']{20,})["\']', 'API Key'),
        (r'password\s*=\s*["\']([^"\']{8,})["\']', 'Password'),
        (r'secret[_-]?key\s*=\s*["\']([^"\']{20,})["\']', 'Secret Key'),
        (r'token\s*=\s*["\']([^"\']{20,})["\']', 'Token'),
        (r'auth[_-]?token\s*=\s*["\']([^"\']{20,})["\']', 'Auth Token'),
        (r'bearer\s+([a-zA-Z0-9_\-\.]{20,})', 'Bearer Token'),
        (r'aws[_-]?access[_-]?key[_-]?id\s*=\s*["\']([^"\']+)["\']', 'AWS Access Key'),
        (r'aws[_-]?secret[_-]?access[_-]?key\s*=\s*["\']([^"\']+)["\']', 'AWS Secret Key'),
        (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API Key'),
        (r'gsk_[a-zA-Z0-9]{20,}', 'Groq API Key'),
        (r'ghp_[a-zA-Z0-9]{36,}', 'GitHub Personal Access Token'),
        (r'glpat-[a-zA-Z0-9_\-]{20,}', 'GitLab Personal Access Token'),
        (r'[0-9]{10}:[A-Za-z0-9_-]{35}', 'Telegram Bot Token'),
        (r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}', 'Slack Token'),
        (r'AIza[0-9A-Za-z_\-]{35}', 'Google API Key'),
    ]

    # Files/dirs to skip during scanning
    SKIP_PATHS = {
        '.git', 'node_modules', 'venv', '__pycache__', '.env',
        'dist', 'build', '.next', '.vscode', '.idea',
        'security_checker.py',  # Don't scan ourselves!
        'sanitizer.py',  # Contains regex patterns for secrets, not actual secrets
        'test_',  # Skip test files prefix
    }

    # File extensions to scan
    SCAN_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
        '.env.example', '.env.template', '.sh', '.bash', '.zsh'
    }

    def __init__(self, project_root: str):
        """Initialize security checker for a project."""
        self.project_root = Path(project_root)
        self.issues: List[SecurityIssue] = []

    def scan_project(self) -> Dict[str, any]:
        """
        Run full security scan on the project.

        Returns:
            Dict with scan results:
            - has_env_file: bool
            - has_gitignore: bool
            - gitignore_configured: bool
            - secrets_found: List[SecurityIssue]
            - critical_issues: int
            - warnings: int
        """
        results = {
            'has_env_file': self._check_env_file(),
            'has_gitignore': self._check_gitignore(),
            'gitignore_configured': self._check_gitignore_config(),
            'secrets_found': [],
            'critical_issues': 0,
            'warnings': 0,
        }

        # Scan for hardcoded secrets
        self.issues = []
        self._scan_for_secrets()

        results['secrets_found'] = self.issues
        results['critical_issues'] = len([i for i in self.issues if i.severity == 'critical'])
        results['warnings'] = len([i for i in self.issues if i.severity == 'warning'])

        return results

    def _check_env_file(self) -> bool:
        """Check if .env file exists."""
        return (self.project_root / '.env').exists()

    def _check_gitignore(self) -> bool:
        """Check if .gitignore file exists."""
        return (self.project_root / '.gitignore').exists()

    def _check_gitignore_config(self) -> bool:
        """Check if .gitignore is properly configured for secrets."""
        gitignore_path = self.project_root / '.gitignore'
        if not gitignore_path.exists():
            return False

        try:
            content = gitignore_path.read_text()

            # Required patterns
            required_patterns = ['.env', '__pycache__', 'venv']

            for pattern in required_patterns:
                if pattern not in content:
                    return False

            return True
        except Exception:
            return False

    def _scan_for_secrets(self):
        """Scan all relevant files for hardcoded secrets."""
        for file_path in self._get_files_to_scan():
            self._scan_file(file_path)

    def _get_files_to_scan(self) -> List[Path]:
        """Get list of files to scan, respecting skip rules."""
        files_to_scan = []

        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_PATHS]

            root_path = Path(root)

            for file in files:
                # Skip test files and sanitizer
                if file.startswith('test_') or file == 'sanitizer.py':
                    continue

                file_path = root_path / file

                # Check if file should be scanned
                if file_path.suffix in self.SCAN_EXTENSIONS:
                    files_to_scan.append(file_path)
                elif file in {'.env.example', '.env.template'}:
                    files_to_scan.append(file_path)

        return files_to_scan

    def _scan_file(self, file_path: Path):
        """Scan a single file for secrets."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            for line_num, line in enumerate(lines, start=1):
                # Skip comments in Python and JavaScript
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('//'):
                    continue

                # Check each pattern
                for pattern, secret_type in self.SECRET_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # Skip if it's an example value
                        if self._is_example_value(match.group(0)):
                            continue

                        # Determine severity
                        severity = 'critical' if file_path.name != '.env.example' else 'warning'

                        issue = SecurityIssue(
                            severity=severity,
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            issue_type=secret_type,
                            description=f"Potential {secret_type} found in code",
                            suggestion=f"Move this {secret_type} to .env file"
                        )
                        self.issues.append(issue)

        except Exception as e:
            # Skip files we can't read
            pass

    def _is_example_value(self, value: str) -> bool:
        """Check if a value is clearly an example/placeholder."""
        example_indicators = [
            'your_', 'example', 'placeholder', 'xxx', 'yyy', 'zzz',
            'test_', 'fake_', 'dummy_', 'sample_', 'my_', 'replace_',
            '***', '...', 'todo', 'changeme', 'insert_here'
        ]

        value_lower = value.lower()
        return any(indicator in value_lower for indicator in example_indicators)

    def get_ralph_security_message(self, results: Dict) -> str:
        """
        Generate Ralph-style security checkpoint message.
        Kid-friendly but accurate.
        """
        messages = []

        # Ralph's intro
        messages.append("🔒 *RALPH'S SEKURITY CHEKKPOINT* 🔒\n")
        messages.append("Hi! I'm Ralph, and I gotta make sure your secrets stay secret!\n")
        messages.append("My cat ate a password once. It was unpossible to fix. Let's not do that.\n")

        # Check .env file
        if results['has_env_file']:
            messages.append("✅ You have a .env file! That's where secrets live!")
        else:
            messages.append("❌ No .env file found! Secrets need a home!")
            messages.append("   💡 I can make one for you! Just say yes!")

        # Check .gitignore
        if results['has_gitignore']:
            if results['gitignore_configured']:
                messages.append("✅ Your .gitignore is protecting secrets!")
            else:
                messages.append("⚠️  You have .gitignore but it needs fixing!")
                messages.append("   💡 I can add the secret stuff to it!")
        else:
            messages.append("❌ No .gitignore file! GitHub will see EVERYTHING!")
            messages.append("   💡 I can create one to hide your secrets!")

        # Check for hardcoded secrets
        if results['critical_issues'] == 0:
            messages.append("✅ No hardcoded secrets found in your code! You're smart!")
        else:
            messages.append(f"❌ Found {results['critical_issues']} secrets in your code files!")
            messages.append("   This is like writing your password on your forehead!")
            messages.append("   💡 I can help move these to .env where they belong!")

        # Ralph's explanation
        messages.append("\n*Why This Matters (Ralph Explains):*")
        messages.append("Imagine if you put your house key under the doormat,")
        messages.append("then took a picture of it and posted it on the internet.")
        messages.append("That's what happens when secrets are in code on GitHub!")
        messages.append("\nGitHub is PUBLIC. Anyone can see it.")
        messages.append("Bad guys look for API keys to steal.")
        messages.append("Then they use YOUR keys to do bad stuff and you get the bill!")

        # Critical blocking
        if results['critical_issues'] > 0:
            messages.append("\n⛔ *RALPH SAYS: FIX THESE FIRST!*")
            messages.append("I can't let you continue until secrets are safe.")
            messages.append("Want me to auto-fix them? (Recommended!)")

        return "\n".join(messages)

    def auto_fix_issues(self, results: Dict) -> Dict[str, bool]:
        """
        Automatically fix common security issues.

        Returns:
            Dict of what was fixed:
            - created_env: bool
            - created_gitignore: bool
            - updated_gitignore: bool
        """
        fixed = {
            'created_env': False,
            'created_gitignore': False,
            'updated_gitignore': False,
        }

        # Create .env if missing
        if not results['has_env_file']:
            self._create_env_file()
            fixed['created_env'] = True

        # Create or update .gitignore
        if not results['has_gitignore']:
            self._create_gitignore()
            fixed['created_gitignore'] = True
        elif not results['gitignore_configured']:
            self._update_gitignore()
            fixed['updated_gitignore'] = True

        return fixed

    def _create_env_file(self):
        """Create a .env file with common placeholders."""
        env_content = """# Environment Variables
# Keep this file LOCAL - never commit to GitHub!

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# AI Services
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional Services
OPENWEATHER_API_KEY=your_weather_key_here

# Database (if needed)
DATABASE_URL=sqlite:///ralph.db

# Add your secrets below this line
"""
        (self.project_root / '.env').write_text(env_content)

    def _create_gitignore(self):
        """Create a .gitignore file with security best practices."""
        gitignore_content = """# Security - Never commit these!
.env
.env.local
.env.*.local
*.pem
*.key
*.crt
secrets.json
credentials.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Build
dist/
build/
*.egg-info/
"""
        (self.project_root / '.gitignore').write_text(gitignore_content)

    def _update_gitignore(self):
        """Update existing .gitignore with missing security patterns."""
        gitignore_path = self.project_root / '.gitignore'
        current_content = gitignore_path.read_text()

        # Patterns to ensure
        required = [
            '.env',
            '.env.local',
            '*.pem',
            '*.key',
            '__pycache__/',
            'venv/',
        ]

        additions = []
        for pattern in required:
            if pattern not in current_content:
                additions.append(pattern)

        if additions:
            updated_content = current_content.rstrip() + '\n\n# Security additions\n' + '\n'.join(additions) + '\n'
            gitignore_path.write_text(updated_content)

    def get_secrets_documentation_link(self) -> str:
        """Return link to security best practices."""
        return "https://docs.github.com/en/code-security/getting-started/best-practices-for-preventing-data-leaks-in-your-organization"


# Quick test
if __name__ == "__main__":
    import sys

    # Test in current directory
    checker = SecurityChecker(os.getcwd())
    results = checker.scan_project()

    print(checker.get_ralph_security_message(results))

    if results['critical_issues'] > 0:
        print("\n" + "="*50)
        print("CRITICAL ISSUES FOUND:")
        for issue in results['secrets_found']:
            if issue.severity == 'critical':
                print(f"\n  {issue.file_path}:{issue.line_number}")
                print(f"  Type: {issue.issue_type}")
                print(f"  {issue.description}")
                print(f"  💡 {issue.suggestion}")
