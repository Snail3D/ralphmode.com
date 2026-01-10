#!/usr/bin/env python3
"""
SEC-002: XSS (Cross-Site Scripting) Prevention for Ralph Mode

This module provides comprehensive XSS protection including:
- HTML entity encoding for all user-facing output
- Content Security Policy (CSP) header configuration
- Safe DOM manipulation patterns (for future JS integration)
- Input validation to catch XSS payloads early

SECURITY PRINCIPLES:
1. NEVER render user input as raw HTML
2. ALWAYS encode/escape output for the context (HTML, JS, URL, CSS)
3. USE Content Security Policy as defense-in-depth
4. VALIDATE input to catch XSS attempts early
5. APPLY context-specific encoding (HTML body vs attributes vs JS)

Usage:
    from xss_prevention import (
        html_escape,
        html_attr_escape,
        js_escape,
        url_escape,
        sanitize_html,
        get_csp_headers,
        XSSValidator
    )

    # Escape for HTML body content
    safe_output = html_escape(user_input)

    # Escape for HTML attributes
    safe_attr = html_attr_escape(user_input)

    # Check if input contains XSS attempt
    if not XSSValidator.is_safe(user_input):
        log_security_event("XSS attempt detected")
"""

import re
import html
import logging
import urllib.parse
from typing import Dict, List, Optional, Set
from functools import lru_cache

logger = logging.getLogger(__name__)


# =============================================================================
# SEC-002: HTML ENTITY ENCODING
# =============================================================================

def html_escape(text: str) -> str:
    """
    Escape text for safe insertion into HTML body content.

    This is the PRIMARY defense against XSS. All user input that will
    appear in HTML must go through this function.

    Escapes: < > & " ' (and converts to HTML entities)

    Args:
        text: The untrusted user input

    Returns:
        HTML-safe string with special characters escaped

    Example:
        >>> html_escape("<script>alert('xss')</script>")
        "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Use Python's html.escape which handles < > & "
    escaped = html.escape(text, quote=True)

    # Also escape single quotes (not done by html.escape by default)
    escaped = escaped.replace("'", "&#x27;")

    # Escape forward slash to prevent </script> attacks
    escaped = escaped.replace("/", "&#x2F;")

    # Neutralize javascript: protocol by escaping the colon
    # This is defense-in-depth - tags are already escaped but this adds safety
    escaped = re.sub(r'javascript:', 'javascript&#x3A;', escaped, flags=re.IGNORECASE)
    escaped = re.sub(r'vbscript:', 'vbscript&#x3A;', escaped, flags=re.IGNORECASE)
    escaped = re.sub(r'data:', 'data&#x3A;', escaped, flags=re.IGNORECASE)

    return escaped


def html_attr_escape(text: str) -> str:
    """
    Escape text for safe insertion into HTML attributes.

    More aggressive escaping than html_escape() because attribute
    context has additional attack vectors.

    Args:
        text: The untrusted user input

    Returns:
        String safe for use in HTML attributes

    Example:
        >>> html_attr_escape('" onclick="alert(1)')
        "&quot; onclick=&quot;alert(1)"
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Start with standard HTML escape
    escaped = html_escape(text)

    # Additional escapes for attribute context
    # Escape backticks (template literal injection in some contexts)
    escaped = escaped.replace("`", "&#x60;")

    # Escape equals sign (attribute injection)
    escaped = escaped.replace("=", "&#x3D;")

    return escaped


def js_escape(text: str) -> str:
    """
    Escape text for safe insertion into JavaScript strings.

    Use when you MUST insert user data into inline JS (though CSP
    should prevent inline JS entirely in production).

    Args:
        text: The untrusted user input

    Returns:
        String safe for use in JavaScript string literals

    Example:
        >>> js_escape("'; alert('xss'); //")
        "\\'; alert(\\'xss\\'); //"
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Escape characters that can break out of JS strings
    escapes = {
        '\\': '\\\\',
        "'": "\\'",
        '"': '\\"',
        '\n': '\\n',
        '\r': '\\r',
        '\t': '\\t',
        '<': '\\u003C',  # Prevent </script> in JS
        '>': '\\u003E',
        '&': '\\u0026',
        '/': '\\/',      # Prevent </script> ending
        '\u2028': '\\u2028',  # Line separator
        '\u2029': '\\u2029',  # Paragraph separator
    }

    result = []
    for char in text:
        result.append(escapes.get(char, char))

    return ''.join(result)


def url_escape(text: str) -> str:
    """
    Escape text for safe insertion into URLs.

    Use for URL parameters or any URL context.

    Args:
        text: The untrusted user input

    Returns:
        URL-encoded string safe for URL parameters

    Example:
        >>> url_escape("javascript:alert(1)")
        "javascript%3Aalert%281%29"
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # URL encode everything that's not alphanumeric or safe chars
    return urllib.parse.quote(text, safe='')


def css_escape(text: str) -> str:
    """
    Escape text for safe insertion into CSS values.

    Use when user input must appear in style attributes or CSS.

    Args:
        text: The untrusted user input

    Returns:
        CSS-safe string
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # CSS escaping - escape any non-alphanumeric character
    result = []
    for char in text:
        if char.isalnum():
            result.append(char)
        else:
            # CSS escape format: \XXXXXX (hex code with space or 6 digits)
            result.append(f'\\{ord(char):06X}')

    return ''.join(result)


# =============================================================================
# SEC-002: CONTENT SECURITY POLICY
# =============================================================================

class CSPConfig:
    """
    Content Security Policy configuration for Ralph Mode.

    CSP is a powerful defense-in-depth mechanism that restricts
    what resources can be loaded and executed.

    Default policy:
    - No inline scripts (blocks most XSS)
    - No inline styles (blocks CSS injection)
    - Only load from same origin
    - No eval() or similar dangerous functions
    """

    # Default CSP directives (strict)
    DEFAULT_DIRECTIVES = {
        # Only allow scripts from same origin
        "default-src": "'self'",

        # Script sources - no inline, no eval
        "script-src": "'self'",

        # Style sources - allow inline for dynamic styling (can be made stricter)
        "style-src": "'self' 'unsafe-inline'",

        # Image sources - same origin + data: for base64 images
        "img-src": "'self' data: https:",

        # Font sources
        "font-src": "'self'",

        # Connect sources for API calls
        "connect-src": "'self'",

        # Frame ancestors - prevent clickjacking
        "frame-ancestors": "'none'",

        # Form action - only allow forms to submit to same origin
        "form-action": "'self'",

        # Base URI - prevent base tag hijacking
        "base-uri": "'self'",

        # Object sources - block plugins
        "object-src": "'none'",

        # Upgrade insecure requests in production
        "upgrade-insecure-requests": "",
    }

    # Relaxed CSP for development (allows more for debugging)
    DEV_DIRECTIVES = {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # Allow for dev tools
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: https: http:",
        "font-src": "'self' data:",
        "connect-src": "'self' ws: wss: http: https:",  # Allow WebSocket for hot reload
        "frame-ancestors": "'self'",
        "form-action": "'self'",
        "base-uri": "'self'",
        "object-src": "'none'",
    }

    @classmethod
    def get_header(cls, environment: str = "production") -> str:
        """
        Get the CSP header value for the given environment.

        Args:
            environment: "production", "staging", or "development"

        Returns:
            CSP header value string
        """
        if environment == "development":
            directives = cls.DEV_DIRECTIVES
        else:
            directives = cls.DEFAULT_DIRECTIVES

        # Build header string
        parts = []
        for directive, value in directives.items():
            if value:
                parts.append(f"{directive} {value}")
            else:
                parts.append(directive)

        return "; ".join(parts)

    @classmethod
    def get_report_only_header(cls, report_uri: str) -> str:
        """
        Get CSP in report-only mode for testing before enforcement.

        Args:
            report_uri: URL where violation reports should be sent

        Returns:
            CSP header value string with report-uri
        """
        base = cls.get_header("production")
        return f"{base}; report-uri {report_uri}"

    @classmethod
    def add_nonce(cls, directive: str = "script-src", nonce: str = "") -> dict:
        """
        Add a nonce to the CSP for allowing specific inline scripts.

        Nonces should be generated per-request (cryptographically random).

        Args:
            directive: Which directive to add nonce to
            nonce: The nonce value (must be random per request)

        Returns:
            Updated directives dict
        """
        directives = cls.DEFAULT_DIRECTIVES.copy()
        if directive in directives:
            directives[directive] += f" 'nonce-{nonce}'"
        return directives


def get_csp_headers(environment: str = "production") -> Dict[str, str]:
    """
    Get all security headers including CSP.

    Returns a dict of headers to add to every response.

    Args:
        environment: "production", "staging", or "development"

    Returns:
        Dict of header name -> header value
    """
    headers = {
        # Content Security Policy
        "Content-Security-Policy": CSPConfig.get_header(environment),

        # X-Content-Type-Options - prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",

        # X-Frame-Options - prevent clickjacking (legacy, CSP frame-ancestors is better)
        "X-Frame-Options": "DENY",

        # X-XSS-Protection - legacy XSS filter (some browsers)
        # Setting to 0 is recommended when CSP is in place
        "X-XSS-Protection": "0",

        # Referrer-Policy - control referrer header
        "Referrer-Policy": "strict-origin-when-cross-origin",

        # Permissions-Policy - restrict browser features
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    return headers


# =============================================================================
# SEC-002: XSS PAYLOAD DETECTION (Input Validation)
# =============================================================================

class XSSValidator:
    """
    Detects potential XSS payloads in user input.

    This is a SECONDARY defense - output encoding is primary.
    Input validation helps catch attacks early for logging/alerting.
    """

    # Common XSS payload patterns
    XSS_PATTERNS = [
        # Script tags
        r'<\s*script',
        r'<\s*/\s*script',

        # Event handlers
        r'on\w+\s*=',

        # JavaScript protocol
        r'javascript\s*:',
        r'vbscript\s*:',
        r'data\s*:\s*text/html',

        # Expression (IE CSS)
        r'expression\s*\(',

        # HTML tags that can execute JS
        r'<\s*img[^>]+\s+onerror',
        r'<\s*svg[^>]+\s+onload',
        r'<\s*body[^>]+\s+onload',
        r'<\s*iframe',
        r'<\s*object',
        r'<\s*embed',
        r'<\s*form[^>]+\s+action\s*=\s*["\']?javascript',
        r'<\s*a[^>]+\s+href\s*=\s*["\']?javascript',

        # HTML entities that could be XSS (after decoding)
        r'&#x?0*(?:58|3a);',  # : (colon for javascript:)
        r'&#x?0*(?:60|3c);',  # < (less than)
        r'&#x?0*(?:62|3e);',  # > (greater than)

        # Template injection
        r'\{\{.*\}\}',  # Angular/Vue
        r'\$\{.*\}',    # Template literals

        # SVG-specific
        r'<\s*svg[^>]*>.*?<\s*/\s*svg\s*>',

        # Meta refresh
        r'<\s*meta[^>]+http-equiv\s*=\s*["\']?refresh',

        # Base tag hijacking
        r'<\s*base[^>]+href',

        # Style-based XSS
        r'<\s*style',
        r'style\s*=\s*["\'][^"\']*expression',
        r'style\s*=\s*["\'][^"\']*behavior',
        r'style\s*=\s*["\'][^"\']*url\s*\(',
    ]

    # Compile patterns for efficiency
    _compiled_patterns: List[re.Pattern] = []

    @classmethod
    def _ensure_compiled(cls):
        """Compile patterns on first use."""
        if not cls._compiled_patterns:
            cls._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE | re.DOTALL)
                for pattern in cls.XSS_PATTERNS
            ]

    @classmethod
    def is_safe(cls, text: str) -> bool:
        """
        Check if text appears safe (no XSS payloads detected).

        Note: This is NOT a guarantee of safety! Output encoding
        is still required. This is for early detection and logging.

        Args:
            text: The user input to check

        Returns:
            True if no XSS patterns detected, False otherwise
        """
        if not text:
            return True

        if not isinstance(text, str):
            text = str(text)

        cls._ensure_compiled()

        for pattern in cls._compiled_patterns:
            if pattern.search(text):
                return False

        return True

    @classmethod
    def detect_xss(cls, text: str) -> List[str]:
        """
        Detect and return all XSS patterns found in text.

        Useful for logging and security monitoring.

        Args:
            text: The user input to check

        Returns:
            List of pattern names that matched
        """
        if not text:
            return []

        if not isinstance(text, str):
            text = str(text)

        cls._ensure_compiled()

        matches = []
        for i, pattern in enumerate(cls._compiled_patterns):
            if pattern.search(text):
                matches.append(cls.XSS_PATTERNS[i])

        return matches

    @classmethod
    def sanitize_and_log(cls, text: str, context: str = "unknown") -> str:
        """
        Check for XSS, log if found, and return escaped text.

        Combines detection, logging, and escaping in one call.

        Args:
            text: The user input
            context: Description of where this input came from

        Returns:
            HTML-escaped text
        """
        if not text:
            return ""

        # Check for XSS
        matches = cls.detect_xss(text)
        if matches:
            logger.warning(
                f"XSS attempt detected in {context}: "
                f"patterns={matches}, input_preview={text[:100]}..."
            )

        # Always escape regardless
        return html_escape(text)


# =============================================================================
# SEC-002: HTML SANITIZATION (Allow Safe Subset)
# =============================================================================

class HTMLSanitizer:
    """
    Sanitize HTML by allowing only safe tags and attributes.

    Use when you need to allow SOME HTML (like bold/italic) but
    not arbitrary HTML. For most cases, just use html_escape().
    """

    # Safe tags that don't allow script execution
    SAFE_TAGS = {
        'b', 'i', 'u', 'strong', 'em', 'strike', 's',
        'p', 'br', 'hr',
        'ul', 'ol', 'li',
        'code', 'pre', 'blockquote',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'a',  # With href validation
        'span', 'div',
    }

    # Safe attributes per tag
    SAFE_ATTRS = {
        'a': {'href', 'title'},  # href validated separately
        'span': {'class'},
        'div': {'class'},
        'code': {'class'},  # For syntax highlighting
    }

    # URL schemes allowed in href
    SAFE_URL_SCHEMES = {'http', 'https', 'mailto'}

    @classmethod
    def sanitize(cls, html_content: str) -> str:
        """
        Sanitize HTML, keeping only safe tags and attributes.

        Args:
            html_content: HTML string to sanitize

        Returns:
            Sanitized HTML with only safe elements
        """
        if not html_content:
            return ""

        # For now, use a simple approach - strip all tags
        # In production, use a library like bleach
        # This is a placeholder that's SAFE (just escapes everything)

        # Pattern to match HTML tags
        tag_pattern = re.compile(r'<[^>]+>')

        # For actual HTML sanitization, we'd use bleach:
        # import bleach
        # return bleach.clean(html_content, tags=cls.SAFE_TAGS,
        #                     attributes=cls.SAFE_ATTRS, strip=True)

        # Conservative approach: escape everything
        # This is safe but loses formatting
        logger.warning("HTMLSanitizer.sanitize() using escape fallback - install bleach for full functionality")
        return html_escape(html_content)

    @classmethod
    def is_safe_url(cls, url: str) -> bool:
        """
        Check if a URL is safe (has allowed scheme).

        Args:
            url: URL to validate

        Returns:
            True if URL scheme is in allowed list
        """
        if not url:
            return False

        try:
            parsed = urllib.parse.urlparse(url.strip().lower())
            return parsed.scheme in cls.SAFE_URL_SCHEMES
        except Exception:
            return False


# =============================================================================
# SEC-002: TELEGRAM-SPECIFIC XSS PREVENTION
# =============================================================================

def escape_for_telegram_markdown(text: str) -> str:
    """
    Escape text for safe use in Telegram's Markdown format.

    Telegram uses Markdown for formatting, and unescaped user input
    could break formatting or cause issues.

    Args:
        text: User input to escape

    Returns:
        Text safe for Telegram Markdown
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Telegram Markdown special characters
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def escape_for_telegram_html(text: str) -> str:
    """
    Escape text for safe use in Telegram's HTML format.

    Telegram supports limited HTML. This escapes text to be safely
    inserted into Telegram HTML messages.

    Args:
        text: User input to escape

    Returns:
        Text safe for Telegram HTML
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Telegram HTML special characters
    return html.escape(text, quote=True)


# =============================================================================
# SEC-002: TESTING UTILITIES
# =============================================================================

class XSSTestPayloads:
    """
    Common XSS payloads for security testing.

    Use these to verify your XSS prevention is working.
    """

    PAYLOADS = [
        # Basic script injection
        "<script>alert('xss')</script>",
        "<script src='evil.js'></script>",

        # Event handler injection
        '<img src=x onerror="alert(1)">',
        '<svg onload="alert(1)">',
        "<body onload='alert(1)'>",
        '<div onmouseover="alert(1)">hover me</div>',

        # JavaScript protocol
        '<a href="javascript:alert(1)">click</a>',
        '<iframe src="javascript:alert(1)">',

        # Data protocol
        '<a href="data:text/html,<script>alert(1)</script>">click</a>',

        # Encoded versions
        "<script>alert(String.fromCharCode(88,83,83))</script>",
        "&#60;script&#62;alert(1)&#60;/script&#62;",
        "%3Cscript%3Ealert(1)%3C/script%3E",

        # SVG-based
        '<svg><script>alert(1)</script></svg>',
        '<svg><a xlink:href="javascript:alert(1)"><text>click</text></a></svg>',

        # Style-based
        '<style>body{background:url("javascript:alert(1)")}</style>',
        "<div style=\"background:url('javascript:alert(1)')\">",

        # Template injection
        "{{constructor.constructor('alert(1)')()}}",
        "${alert(1)}",

        # Breaking out of attributes
        '" onclick="alert(1)" data-foo="',
        "' onclick='alert(1)' data-foo='",

        # Null byte injection
        "<scr\x00ipt>alert(1)</script>",

        # Unicode escapes
        "<script>\\u0061lert(1)</script>",

        # Meta refresh
        '<meta http-equiv="refresh" content="0;url=javascript:alert(1)">',

        # Base tag
        '<base href="javascript:alert(1)//">',

        # Form action
        '<form action="javascript:alert(1)"><input type=submit>',
    ]

    @classmethod
    def test_escaping(cls, escape_func) -> dict:
        """
        Test an escape function against all payloads.

        The key test is whether < and > are escaped, because that's what
        prevents the browser from parsing tags. Event handlers like onerror=
        in plain text are harmless without the enclosing tag.

        Args:
            escape_func: The escape function to test

        Returns:
            Dict with test results
        """
        results = {
            "passed": 0,
            "failed": 0,
            "failures": []
        }

        for payload in cls.PAYLOADS:
            escaped = escape_func(payload)

            # The critical check: are < and > properly escaped?
            # If < becomes &lt; and > becomes &gt;, the payload is neutralized
            # Event handlers like onerror= are harmless without tag context
            is_safe = True

            # Check if unescaped < or > remain (the critical XSS vectors)
            if '<' in escaped or '>' in escaped:
                is_safe = False

            # Also check for javascript: protocol (must be escaped or blocked)
            if 'javascript:' in escaped.lower():
                is_safe = False

            if is_safe:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["failures"].append({
                    "payload": payload,
                    "escaped": escaped
                })

        return results

    @classmethod
    def test_detection(cls, validator_func) -> dict:
        """
        Test a detection function catches all payloads.

        Args:
            validator_func: Function that returns False for XSS

        Returns:
            Dict with test results
        """
        results = {
            "detected": 0,
            "missed": 0,
            "missed_payloads": []
        }

        for payload in cls.PAYLOADS:
            if not validator_func(payload):  # is_safe returns False for XSS
                results["detected"] += 1
            else:
                results["missed"] += 1
                results["missed_payloads"].append(payload)

        return results


# =============================================================================
# MAIN - Self Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SEC-002: XSS Prevention Tests")
    print("=" * 60)

    # Test HTML escape
    print("\n1. Testing html_escape()...")
    escape_results = XSSTestPayloads.test_escaping(html_escape)
    print(f"   Passed: {escape_results['passed']}")
    print(f"   Failed: {escape_results['failed']}")
    if escape_results['failures']:
        print("   Failures:")
        for f in escape_results['failures'][:3]:
            print(f"     - {f['payload'][:40]}...")

    # Test XSS detection
    print("\n2. Testing XSSValidator.is_safe()...")
    detection_results = XSSTestPayloads.test_detection(XSSValidator.is_safe)
    print(f"   Detected: {detection_results['detected']}")
    print(f"   Missed: {detection_results['missed']}")
    if detection_results['missed_payloads']:
        print("   Missed payloads (detection is secondary defense, this is informational):")
        for p in detection_results['missed_payloads'][:3]:
            print(f"     - {p[:40]}...")

    # Test CSP headers
    print("\n3. Testing CSP header generation...")
    csp_prod = CSPConfig.get_header("production")
    csp_dev = CSPConfig.get_header("development")
    print(f"   Production CSP: {csp_prod[:60]}...")
    print(f"   Development CSP: {csp_dev[:60]}...")

    # Security headers
    print("\n4. Testing security headers...")
    headers = get_csp_headers("production")
    for header, value in headers.items():
        print(f"   {header}: {value[:50]}...")

    print("\n" + "=" * 60)
    if escape_results['failed'] == 0:
        print("✅ All XSS escape tests PASSED")
    else:
        print("❌ Some escape tests FAILED - review implementation!")

    print(f"ℹ️  XSS detection caught {detection_results['detected']}/{len(XSSTestPayloads.PAYLOADS)} payloads")
    print("   (Detection is secondary defense - escaping is primary)")
    print("=" * 60)
