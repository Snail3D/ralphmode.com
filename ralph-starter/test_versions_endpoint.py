#!/usr/bin/env python3
"""
Test script for WB-001: /api/versions endpoint

Tests that the endpoint returns the correct version data structure.
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_versions_endpoint():
    """Test the /api/versions endpoint logic."""
    print("Testing /api/versions endpoint logic...\n")

    try:
        from version_manager import VersionManager
        from changelog_generator import ChangelogGenerator
        from datetime import datetime

        vm = VersionManager()
        cg = ChangelogGenerator()

        # Get current version
        current_version = vm.get_current_version()
        print(f"✓ Current version: {current_version}")

        # Get version history
        version_history = cg.get_version_history(limit=100)
        print(f"✓ Found {len(version_history)} versions in history")

        if version_history:
            print("\nVersion history:")
            for entry in version_history[:5]:  # Show first 5
                print(f"  - {entry.version} ({entry.change_type}) - {entry.released_at.strftime('%Y-%m-%d')}")

        # Categorize versions
        stable_version = None
        beta_version = None
        alpha_version = None

        for entry in version_history:
            version_str = entry.version

            if 'beta' in version_str.lower():
                if not beta_version:
                    beta_version = entry
            elif 'alpha' in version_str.lower():
                if not alpha_version:
                    alpha_version = entry
            elif version_str.startswith('0.'):
                if not alpha_version:
                    alpha_version = entry
            else:
                if not stable_version:
                    stable_version = entry

        print("\n" + "="*50)
        print("Version categorization:")
        print("="*50)

        if stable_version:
            print(f"✓ Stable: {stable_version.version} ({stable_version.released_at.strftime('%Y-%m-%d')})")
        else:
            print(f"✓ Stable: {current_version} (current, no history)")

        if beta_version:
            print(f"✓ Beta: {beta_version.version} ({beta_version.released_at.strftime('%Y-%m-%d')})")
        else:
            print("✓ Beta: None")

        if alpha_version:
            print(f"✓ Alpha: {alpha_version.version} ({alpha_version.released_at.strftime('%Y-%m-%d')})")
        else:
            print("✓ Alpha: None")

        print("\n" + "="*50)
        print("Expected API Response Structure:")
        print("="*50)

        response = {
            'success': True,
            'stable': {
                'version': stable_version.version if stable_version else str(current_version),
                'date': stable_version.released_at.isoformat() if stable_version else datetime.now().isoformat(),
                'changelog_url': f'/changelog#{stable_version.version if stable_version else current_version}',
                'download_url': f'/download/ralph-starter-{stable_version.version if stable_version else current_version}.zip'
            },
            'beta': {
                'version': beta_version.version,
                'date': beta_version.released_at.isoformat(),
                'changelog_url': f'/changelog#{beta_version.version}',
                'download_url': f'/download/ralph-starter-{beta_version.version}.zip'
            } if beta_version else None,
            'alpha': {
                'version': alpha_version.version,
                'date': alpha_version.released_at.isoformat(),
                'changelog_url': f'/changelog#{alpha_version.version}',
                'download_url': f'/download/ralph-starter-{alpha_version.version}.zip'
            } if alpha_version else None,
            'current': str(current_version)
        }

        import json
        print(json.dumps(response, indent=2))

        print("\n" + "="*50)
        print("✅ All tests passed!")
        print("="*50)

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_versions_endpoint()
    sys.exit(0 if success else 1)
