"""
Git Safety Check - OB-052
Prevents accidental secret exposure before git push.
Ralph reviews what will be committed in simple terms.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

try:
    from security_checker import SecurityChecker, SecurityIssue
    SECURITY_CHECKER_AVAILABLE = True
except ImportError:
    SECURITY_CHECKER_AVAILABLE = False


@dataclass
class FilePreview:
    """Preview of a file to be pushed."""
    path: str
    size_bytes: int
    is_binary: bool
    is_large: bool  # > 1MB
    file_type: str


@dataclass
class GitSafetyResult:
    """Result of git safety check."""
    is_safe: bool
    secrets_found: List[SecurityIssue]
    files_to_push: List[FilePreview]
    large_files: List[str]
    binary_files: List[str]
    warnings: List[str]
    total_size_bytes: int


class GitSafetyChecker:
    """
    Performs safety checks before git push during onboarding.

    Checks:
    - Scans staged files for potential secrets
    - Warns about large files (> 1MB)
    - Warns about binary files
    - Shows preview of what will be pushed
    - Provides Ralph-style explanations
    """

    # Large file threshold (1MB)
    LARGE_FILE_THRESHOLD = 1024 * 1024

    # Binary file extensions to warn about
    BINARY_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
        '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
        '.exe', '.dll', '.so', '.dylib',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.db', '.sqlite', '.sqlite3',
    }

    def __init__(self, repo_path: str):
        """Initialize git safety checker."""
        self.repo_path = Path(repo_path)

    def check_before_push(self) -> GitSafetyResult:
        """
        Run all safety checks before git push.

        Returns:
            GitSafetyResult with all findings
        """
        # Get list of files to be pushed
        files_to_push = self._get_staged_files()

        # Analyze each file
        file_previews = []
        large_files = []
        binary_files = []
        total_size = 0

        for file_path in files_to_push:
            preview = self._analyze_file(file_path)
            file_previews.append(preview)
            total_size += preview.size_bytes

            if preview.is_large:
                large_files.append(file_path)
            if preview.is_binary:
                binary_files.append(file_path)

        # Scan for secrets in staged files
        secrets_found = []
        if SECURITY_CHECKER_AVAILABLE:
            secrets_found = self._scan_staged_for_secrets(files_to_push)

        # Generate warnings
        warnings = self._generate_warnings(large_files, binary_files, secrets_found)

        # Determine if safe to push
        is_safe = len(secrets_found) == 0

        return GitSafetyResult(
            is_safe=is_safe,
            secrets_found=secrets_found,
            files_to_push=file_previews,
            large_files=large_files,
            binary_files=binary_files,
            warnings=warnings,
            total_size_bytes=total_size
        )

    def _get_staged_files(self) -> List[str]:
        """Get list of files staged for commit."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            return files
        except subprocess.CalledProcessError:
            return []

    def _analyze_file(self, file_path: str) -> FilePreview:
        """Analyze a single file."""
        full_path = self.repo_path / file_path

        # Get file size
        try:
            size_bytes = full_path.stat().st_size
        except (OSError, FileNotFoundError):
            size_bytes = 0

        # Check if binary
        is_binary = self._is_binary_file(file_path)

        # Check if large
        is_large = size_bytes > self.LARGE_FILE_THRESHOLD

        # Determine file type
        file_type = self._get_file_type(file_path)

        return FilePreview(
            path=file_path,
            size_bytes=size_bytes,
            is_binary=is_binary,
            is_large=is_large,
            file_type=file_type
        )

    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary based on extension."""
        ext = Path(file_path).suffix.lower()
        return ext in self.BINARY_EXTENSIONS

    def _get_file_type(self, file_path: str) -> str:
        """Get human-readable file type."""
        ext = Path(file_path).suffix.lower()

        type_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React',
            '.tsx': 'React TypeScript',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.sh': 'Shell Script',
            '.env': 'Environment',
            '.gitignore': 'Git Ignore',
            '.jpg': 'Image',
            '.png': 'Image',
            '.pdf': 'PDF',
            '.zip': 'Archive',
        }

        return type_map.get(ext, 'File')

    def _scan_staged_for_secrets(self, files: List[str]) -> List[SecurityIssue]:
        """Scan staged files for secrets using SecurityChecker."""
        if not SECURITY_CHECKER_AVAILABLE:
            return []

        # Use SecurityChecker to scan the project
        checker = SecurityChecker(str(self.repo_path))
        results = checker.scan_project()

        # Filter to only include secrets in staged files
        staged_secrets = []
        for issue in results.get('secrets_found', []):
            # Normalize paths for comparison
            issue_path = Path(issue.file_path).relative_to(self.repo_path) if Path(issue.file_path).is_absolute() else Path(issue.file_path)
            if str(issue_path) in files:
                staged_secrets.append(issue)

        return staged_secrets

    def _generate_warnings(
        self,
        large_files: List[str],
        binary_files: List[str],
        secrets: List[SecurityIssue]
    ) -> List[str]:
        """Generate warning messages."""
        warnings = []

        if secrets:
            warnings.append(f"🚨 Found {len(secrets)} potential secret(s) in your code!")

        if large_files:
            warnings.append(f"⚠️ {len(large_files)} large file(s) detected (> 1MB)")

        if binary_files:
            warnings.append(f"📦 {len(binary_files)} binary file(s) detected")

        return warnings

    def get_ralph_explanation(self) -> str:
        """Get Ralph's explanation of what git push does."""
        return """*🚀 Ralph Explains Git Push!*

**What is "push"?**
Ralph say: Push means "send your code to GitHub cloud!" ☁️

**What happens:**
1. Git takes your commit (the saved work)
2. Uploads it to GitHub servers
3. Now everyone can see it! (if repo is public)

**Why Ralph check first?**
Because once you push:
→ Code is LIVE on the internet! 🌍
→ Can't unpush a secret! (very hard to undo!)
→ Everyone can see everything! 👀

**Ralph's job:**
Me check for:
→ Passwords or API keys in code
→ Big files that slow down repo
→ Stuff that shouldn't be public

*Better safe than sorry! Me help you!* 🦺
"""

    def get_public_repo_warning(self) -> str:
        """Get warning about public repositories."""
        return """*⚠️ Public Repos Mean PUBLIC!*

**What "public repo" means:**
→ ANYONE on the internet can see your code
→ Google can index it (show in search results!)
→ No password needed to read it
→ It's like posting on social media! 📢

**Things that should NEVER be public:**
→ API keys (like GROQ_API_KEY)
→ Passwords (any password!)
→ Secret tokens (like TELEGRAM_BOT_TOKEN)
→ Private data (customer info, etc.)

**How to keep secrets safe:**
1. Put secrets in `.env` file
2. Add `.env` to `.gitignore`
3. Use `.env.example` with fake values
4. Never commit the real `.env` file!

*Ralph says:*
"If you not sure if it secret, treat it like secret!" 🔒
"""

    def get_emergency_abort_message(self) -> str:
        """Get message for when secrets are detected."""
        return """*🚨 EMERGENCY BRAKE! 🚨*

**Ralph found secrets in your code!**

Me CANNOT let you push this! Here why:

**What happens if you push secrets:**
1. Bad people find them (bots scan GitHub 24/7!) 🤖
2. They use YOUR API keys
3. You get big bill 💸
4. Or they break your stuff 💥

**Ralph gonna help you fix:**
1. Me show you where the secrets are
2. You move them to `.env` file
3. Me check `.gitignore` has `.env`
4. Then we try push again! ✅

*Don't worry! Ralph here to protect you!* 🦸
"""

    def format_file_preview(self, files: List[FilePreview]) -> str:
        """Format file list for display."""
        if not files:
            return "*No files to push!*"

        lines = ["*📋 Files to be pushed:*\n"]

        for file in files:
            size_str = self._format_size(file.size_bytes)
            icon = "📦" if file.is_binary else "📄"
            warning = " ⚠️ LARGE" if file.is_large else ""

            lines.append(f"{icon} `{file.path}`")
            lines.append(f"   Type: {file.file_type} | Size: {size_str}{warning}")

        return "\n".join(lines)

    def format_secret_warnings(self, secrets: List[SecurityIssue]) -> str:
        """Format secret warnings for display."""
        if not secrets:
            return ""

        lines = ["\n*🚨 SECRETS DETECTED! 🚨*\n"]

        for i, secret in enumerate(secrets, 1):
            lines.append(f"{i}. **{secret.issue_type}** in `{secret.file_path}:{secret.line_number}`")
            lines.append(f"   → {secret.description}")
            lines.append(f"   💡 Fix: {secret.suggestion}\n")

        return "\n".join(lines)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


# Singleton instance
_git_safety_checker: Optional[GitSafetyChecker] = None


def get_git_safety_checker(repo_path: str) -> GitSafetyChecker:
    """Get or create git safety checker instance."""
    global _git_safety_checker
    if _git_safety_checker is None or str(_git_safety_checker.repo_path) != repo_path:
        _git_safety_checker = GitSafetyChecker(repo_path)
    return _git_safety_checker
