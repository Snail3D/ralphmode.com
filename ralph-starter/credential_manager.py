#!/usr/bin/env python3
"""
OB-022: Credential Manager

Secure storage for API keys and passwords. Encrypted at rest, easy to update.

Features:
- Encrypts credentials before storing (AES-256-GCM)
- Easy update/rotate functionality
- List configured credentials (masked)
- Delete credential option
- Export/import for backup
"""

import os
import json
import base64
import secrets
from typing import Dict, Optional, List, Any
from datetime import datetime
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class CredentialManager:
    """
    Secure credential storage with encryption at rest.

    Stores credentials in an encrypted JSON file. Uses AES-256-GCM for encryption.
    """

    def __init__(self, storage_path: str = '.credentials.enc', master_key: Optional[str] = None):
        """
        Initialize the credential manager.

        Args:
            storage_path: Path to the encrypted credentials file
            master_key: Master encryption key (base64 encoded). If not provided,
                       will use DB_ENCRYPTION_KEY from environment or generate new one
        """
        self.storage_path = Path(storage_path)

        # Get or generate master key
        if master_key:
            self.master_key = base64.b64decode(master_key)
        else:
            # Try to get from environment (same key as DB encryption for consistency)
            env_key = os.getenv('DB_ENCRYPTION_KEY')
            if env_key:
                self.master_key = base64.b64decode(env_key)
            else:
                # Generate new key
                self.master_key = AESGCM.generate_key(bit_length=256)
                print(f"⚠️  Generated new master key: {base64.b64encode(self.master_key).decode()}")
                print("   Add this to your .env file as DB_ENCRYPTION_KEY")

        # Initialize AESGCM cipher
        self.cipher = AESGCM(self.master_key)

        # Load existing credentials
        self.credentials: Dict[str, Dict[str, Any]] = self._load_credentials()

    def _encrypt(self, data: str) -> str:
        """
        Encrypt data using AES-256-GCM.

        Args:
            data: Plain text to encrypt

        Returns:
            Base64 encoded encrypted data with nonce
        """
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        ciphertext = self.cipher.encrypt(nonce, data.encode(), None)

        # Combine nonce + ciphertext and base64 encode
        encrypted = base64.b64encode(nonce + ciphertext).decode()
        return encrypted

    def _decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data using AES-256-GCM.

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted plain text
        """
        # Decode base64
        data = base64.b64decode(encrypted_data)

        # Split nonce and ciphertext
        nonce = data[:12]
        ciphertext = data[12:]

        # Decrypt
        plaintext = self.cipher.decrypt(nonce, ciphertext, None)
        return plaintext.decode()

    def _load_credentials(self) -> Dict[str, Dict[str, Any]]:
        """
        Load credentials from encrypted storage.

        Returns:
            Dictionary of credentials
        """
        if not self.storage_path.exists():
            return {}

        try:
            with open(self.storage_path, 'r') as f:
                encrypted_data = f.read()

            # Decrypt the entire file
            decrypted_json = self._decrypt(encrypted_data)
            return json.loads(decrypted_json)
        except Exception as e:
            print(f"⚠️  Error loading credentials: {e}")
            return {}

    def _save_credentials(self) -> None:
        """Save credentials to encrypted storage."""
        # Convert to JSON
        json_data = json.dumps(self.credentials, indent=2)

        # Encrypt
        encrypted_data = self._encrypt(json_data)

        # Write to file
        with open(self.storage_path, 'w') as f:
            f.write(encrypted_data)

    def set(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a credential (encrypted).

        Args:
            key: Credential name (e.g., 'TELEGRAM_BOT_TOKEN', 'GROQ_API_KEY')
            value: Credential value (will be encrypted)
            metadata: Optional metadata (description, created_at, etc.)
        """
        self.credentials[key] = {
            'value': value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self._save_credentials()

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a credential.

        Args:
            key: Credential name
            default: Default value if not found

        Returns:
            Decrypted credential value or default
        """
        if key not in self.credentials:
            return default

        return self.credentials[key]['value']

    def update(self, key: str, value: str) -> bool:
        """
        Update/rotate a credential.

        Args:
            key: Credential name
            value: New credential value

        Returns:
            True if updated, False if credential doesn't exist
        """
        if key not in self.credentials:
            return False

        # Keep existing metadata
        old_cred = self.credentials[key]
        self.credentials[key] = {
            'value': value,
            'created_at': old_cred.get('created_at', datetime.now().isoformat()),
            'updated_at': datetime.now().isoformat(),
            'metadata': old_cred.get('metadata', {})
        }
        self._save_credentials()
        return True

    def delete(self, key: str) -> bool:
        """
        Delete a credential.

        Args:
            key: Credential name

        Returns:
            True if deleted, False if credential doesn't exist
        """
        if key not in self.credentials:
            return False

        del self.credentials[key]
        self._save_credentials()
        return True

    def list(self, show_values: bool = False) -> List[Dict[str, Any]]:
        """
        List all stored credentials.

        Args:
            show_values: If True, shows actual values. If False, masks them.

        Returns:
            List of credential info dictionaries
        """
        result = []

        for key, cred in self.credentials.items():
            value = cred['value']

            # Mask value unless explicitly requested
            if not show_values:
                if len(value) <= 4:
                    masked_value = '****'
                else:
                    # Show first 4 chars and last 4 chars
                    masked_value = f"{value[:4]}...{value[-4:]}"
            else:
                masked_value = value

            result.append({
                'key': key,
                'value': masked_value,
                'created_at': cred.get('created_at', 'N/A'),
                'updated_at': cred.get('updated_at', 'N/A'),
                'metadata': cred.get('metadata', {})
            })

        return result

    def export(self, export_path: str, include_values: bool = True) -> None:
        """
        Export credentials to a backup file (encrypted).

        Args:
            export_path: Path to export file
            include_values: If True, exports actual values (encrypted).
                          If False, exports structure only.
        """
        if include_values:
            # Export encrypted credentials as-is
            backup_data = self.credentials.copy()
        else:
            # Export structure without values
            backup_data = {
                key: {
                    'value': '*** REDACTED ***',
                    'created_at': cred.get('created_at', 'N/A'),
                    'updated_at': cred.get('updated_at', 'N/A'),
                    'metadata': cred.get('metadata', {})
                }
                for key, cred in self.credentials.items()
            }

        # Encrypt backup
        json_data = json.dumps(backup_data, indent=2)
        encrypted_data = self._encrypt(json_data)

        # Write to file
        with open(export_path, 'w') as f:
            f.write(encrypted_data)

        print(f"✅ Credentials exported to {export_path}")

    def import_from(self, import_path: str, overwrite: bool = False) -> None:
        """
        Import credentials from a backup file.

        Args:
            import_path: Path to import file
            overwrite: If True, overwrites existing credentials.
                      If False, only adds new ones.
        """
        try:
            with open(import_path, 'r') as f:
                encrypted_data = f.read()

            # Decrypt
            decrypted_json = self._decrypt(encrypted_data)
            imported_creds = json.loads(decrypted_json)

            # Merge with existing credentials
            count = 0
            for key, cred in imported_creds.items():
                if key not in self.credentials or overwrite:
                    self.credentials[key] = cred
                    count += 1

            self._save_credentials()
            print(f"✅ Imported {count} credentials from {import_path}")

        except Exception as e:
            print(f"❌ Error importing credentials: {e}")

    def rotate_master_key(self, new_master_key: str) -> None:
        """
        Rotate the master encryption key.

        Re-encrypts all credentials with a new master key.

        Args:
            new_master_key: New master key (base64 encoded)
        """
        # Decrypt all credentials with old key (already loaded)
        old_credentials = self.credentials.copy()

        # Update to new key
        self.master_key = base64.b64decode(new_master_key)
        self.cipher = AESGCM(self.master_key)

        # Re-encrypt with new key
        self.credentials = old_credentials
        self._save_credentials()

        print("✅ Master key rotated successfully")
        print(f"⚠️  Update DB_ENCRYPTION_KEY in .env to: {new_master_key}")


# CLI interface for testing
if __name__ == '__main__':
    import sys

    cm = CredentialManager()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python credential_manager.py set <key> <value>")
        print("  python credential_manager.py get <key>")
        print("  python credential_manager.py update <key> <value>")
        print("  python credential_manager.py delete <key>")
        print("  python credential_manager.py list [--show-values]")
        print("  python credential_manager.py export <path> [--no-values]")
        print("  python credential_manager.py import <path> [--overwrite]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'set':
        if len(sys.argv) < 4:
            print("Usage: python credential_manager.py set <key> <value>")
            sys.exit(1)
        key = sys.argv[2]
        value = sys.argv[3]
        cm.set(key, value)
        print(f"✅ Set credential: {key}")

    elif command == 'get':
        if len(sys.argv) < 3:
            print("Usage: python credential_manager.py get <key>")
            sys.exit(1)
        key = sys.argv[2]
        value = cm.get(key)
        if value:
            print(f"{key}: {value}")
        else:
            print(f"❌ Credential not found: {key}")

    elif command == 'update':
        if len(sys.argv) < 4:
            print("Usage: python credential_manager.py update <key> <value>")
            sys.exit(1)
        key = sys.argv[2]
        value = sys.argv[3]
        if cm.update(key, value):
            print(f"✅ Updated credential: {key}")
        else:
            print(f"❌ Credential not found: {key}")

    elif command == 'delete':
        if len(sys.argv) < 3:
            print("Usage: python credential_manager.py delete <key>")
            sys.exit(1)
        key = sys.argv[2]
        if cm.delete(key):
            print(f"✅ Deleted credential: {key}")
        else:
            print(f"❌ Credential not found: {key}")

    elif command == 'list':
        show_values = '--show-values' in sys.argv
        creds = cm.list(show_values=show_values)
        if not creds:
            print("No credentials stored")
        else:
            print("\nStored Credentials:")
            print("-" * 80)
            for cred in creds:
                print(f"\n🔑 {cred['key']}")
                print(f"   Value: {cred['value']}")
                print(f"   Created: {cred['created_at']}")
                print(f"   Updated: {cred['updated_at']}")
                if cred['metadata']:
                    print(f"   Metadata: {cred['metadata']}")

    elif command == 'export':
        if len(sys.argv) < 3:
            print("Usage: python credential_manager.py export <path> [--no-values]")
            sys.exit(1)
        path = sys.argv[2]
        include_values = '--no-values' not in sys.argv
        cm.export(path, include_values=include_values)

    elif command == 'import':
        if len(sys.argv) < 3:
            print("Usage: python credential_manager.py import <path> [--overwrite]")
            sys.exit(1)
        path = sys.argv[2]
        overwrite = '--overwrite' in sys.argv
        cm.import_from(path, overwrite=overwrite)

    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)
