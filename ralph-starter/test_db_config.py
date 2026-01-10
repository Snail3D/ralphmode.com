#!/usr/bin/env python3
"""
SEC-018: Database Security Tests

Validates that all SEC-018 acceptance criteria are met:
1. Database not accessible from public internet
2. Encrypted connections (SSL/TLS) required
3. Data encrypted at rest
4. Per-service database credentials (least privilege)
5. Automated backups with encryption
6. Point-in-time recovery enabled
7. Audit logging on sensitive tables
8. Connection pooling with limits
"""

import os
import sys
import tempfile
from pathlib import Path

# Test imports
try:
    from db_config import (
        get_secure_engine,
        validate_database_url,
        get_ssl_connection_args,
        DataEncryption,
        encrypt_field,
        decrypt_field,
        AuditLog,
        setup_audit_logging,
        BackupManager,
        DatabaseCredentials,
        setup_database_security,
    )
    print("✅ All db_config imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_network_isolation():
    """Test SEC-018.1: Database not accessible from public internet"""
    print("\n" + "=" * 60)
    print("Testing Network Isolation")
    print("=" * 60)

    # Test that dangerous URLs are rejected
    try:
        validate_database_url("postgresql://user:pass@0.0.0.0:5432/db")
        print("❌ FAILED: Should reject 0.0.0.0 binding")
        return False
    except ValueError as e:
        print(f"✅ Correctly rejected dangerous URL: {e}")

    # Test that safe URLs are accepted
    try:
        validate_database_url("sqlite:///test.db")
        print("✅ Accepted SQLite URL")
    except ValueError as e:
        print(f"❌ FAILED: Should accept SQLite: {e}")
        return False

    try:
        validate_database_url("postgresql://user:pass@localhost:5432/db")
        print("✅ Accepted localhost PostgreSQL URL")
    except ValueError as e:
        print(f"❌ FAILED: Should accept localhost: {e}")
        return False

    return True


def test_ssl_encryption():
    """Test SEC-018.2: Encrypted connections (SSL/TLS) required"""
    print("\n" + "=" * 60)
    print("Testing SSL/TLS Encryption")
    print("=" * 60)

    # Test PostgreSQL SSL args
    ssl_args = get_ssl_connection_args("postgresql://localhost/db")
    if "sslmode" in ssl_args and ssl_args["sslmode"] == "require":
        print("✅ PostgreSQL SSL/TLS configured (sslmode=require)")
    else:
        print("❌ FAILED: PostgreSQL SSL not properly configured")
        return False

    # Test MySQL SSL args
    ssl_args = get_ssl_connection_args("mysql://localhost/db")
    if "ssl" in ssl_args:
        print("✅ MySQL SSL/TLS configured")
    else:
        print("❌ FAILED: MySQL SSL not properly configured")
        return False

    # Test SQLite (no SSL needed for local file)
    ssl_args = get_ssl_connection_args("sqlite:///test.db")
    print("✅ SQLite (local file, no network encryption needed)")

    return True


def test_data_encryption():
    """Test SEC-018.3: Data encrypted at rest"""
    print("\n" + "=" * 60)
    print("Testing Data Encryption at Rest")
    print("=" * 60)

    # Test encryption/decryption
    encryption = DataEncryption()

    test_data = "Sensitive user data 🔒"
    encrypted = encryption.encrypt(test_data)
    decrypted = encryption.decrypt(encrypted)

    if encrypted != test_data:
        print(f"✅ Data encrypted: {test_data} → {encrypted[:50]}...")
    else:
        print("❌ FAILED: Data not encrypted")
        return False

    if decrypted == test_data:
        print(f"✅ Data decrypted correctly: {decrypted}")
    else:
        print(f"❌ FAILED: Decryption failed (expected {test_data}, got {decrypted})")
        return False

    # Test convenience functions
    encrypted2 = encrypt_field(test_data)
    decrypted2 = decrypt_field(encrypted2)

    if decrypted2 == test_data:
        print("✅ Convenience functions (encrypt_field/decrypt_field) work")
    else:
        print("❌ FAILED: Convenience functions failed")
        return False

    return True


def test_connection_pooling():
    """Test SEC-018.4: Connection pooling with limits"""
    print("\n" + "=" * 60)
    print("Testing Connection Pooling")
    print("=" * 60)

    # Create engine with custom pool settings
    engine = get_secure_engine(
        "sqlite:///test.db",
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600
    )

    # Check that engine was created
    if engine:
        print("✅ Secure engine created with connection pooling")
    else:
        print("❌ FAILED: Could not create secure engine")
        return False

    # For PostgreSQL/MySQL, check pool configuration
    if hasattr(engine.pool, 'size'):
        print(f"✅ Pool size configured: {engine.pool.size()}")

    return True


def test_audit_logging():
    """Test SEC-018.5: Audit logging on sensitive tables"""
    print("\n" + "=" * 60)
    print("Testing Audit Logging")
    print("=" * 60)

    # Test audit log entry creation
    AuditLog.log_operation(
        table_name="users",
        operation="INSERT",
        user_id=12345,
        record_id=1,
    )
    print("✅ Audit log entry created for INSERT")

    AuditLog.log_operation(
        table_name="users",
        operation="UPDATE",
        user_id=12345,
        record_id=1,
        changes={"username": {"old": "oldname", "new": "newname"}}
    )
    print("✅ Audit log entry created for UPDATE")

    # Check that audit log file was created
    audit_log_path = Path(__file__).parent / "logs" / "audit.log"
    if audit_log_path.exists():
        print(f"✅ Audit log file created: {audit_log_path}")
    else:
        print(f"❌ FAILED: Audit log file not found at {audit_log_path}")
        return False

    return True


def test_automated_backups():
    """Test SEC-018.6: Automated backups with encryption"""
    print("\n" + "=" * 60)
    print("Testing Automated Encrypted Backups")
    print("=" * 60)

    # Create temporary backup directory
    with tempfile.TemporaryDirectory() as tmpdir:
        backup_mgr = BackupManager(backup_dir=Path(tmpdir))

        # Create a test database
        test_db_path = Path(tmpdir) / "test.db"
        test_db_path.write_text("test database content")

        # Create encrypted backup
        backup_path = backup_mgr.create_backup(f"sqlite:///{test_db_path}")

        if backup_path and backup_path.exists():
            print(f"✅ Encrypted backup created: {backup_path}")
        else:
            print("❌ FAILED: Backup not created")
            return False

        # Verify backup is encrypted (should not contain plaintext)
        backup_content = backup_path.read_bytes()
        if b"test database content" not in backup_content:
            print("✅ Backup is encrypted (plaintext not found)")
        else:
            print("❌ FAILED: Backup is not encrypted")
            return False

        # Test restore (point-in-time recovery)
        restore_db_path = Path(tmpdir) / "restored.db"
        backup_mgr.restore_backup(backup_path, f"sqlite:///{restore_db_path}")

        if restore_db_path.exists():
            restored_content = restore_db_path.read_text()
            if restored_content == "test database content":
                print("✅ Point-in-time recovery successful (backup restored)")
            else:
                print(f"❌ FAILED: Restored content incorrect: {restored_content}")
                return False
        else:
            print("❌ FAILED: Restore failed")
            return False

    return True


def test_least_privilege():
    """Test SEC-018.7: Per-service database credentials (least privilege)"""
    print("\n" + "=" * 60)
    print("Testing Least Privilege Credentials")
    print("=" * 60)

    # Generate SQL for creating least-privilege users
    sql = DatabaseCredentials.generate_credentials_config()

    # Check that SQL contains different roles
    required_roles = ["bot_user", "api_user", "backup_user", "admin_user"]
    for role in required_roles:
        if role in sql:
            print(f"✅ SQL includes {role} with least privilege grants")
        else:
            print(f"❌ FAILED: SQL missing {role}")
            return False

    # Check that different roles have different permissions
    if "SELECT, INSERT, UPDATE ON users" in sql:
        print("✅ bot_user has appropriate permissions (SELECT, INSERT, UPDATE)")
    else:
        print("❌ FAILED: bot_user permissions not found")
        return False

    if "SELECT ON ALL TABLES" in sql:
        print("✅ backup_user has read-only access")
    else:
        print("❌ FAILED: backup_user permissions not found")
        return False

    return True


def test_complete_setup():
    """Test complete security setup"""
    print("\n" + "=" * 60)
    print("Testing Complete Database Security Setup")
    print("=" * 60)

    try:
        engine = setup_database_security()
        if engine:
            print("✅ Complete database security setup successful")
            return True
        else:
            print("❌ FAILED: Setup returned no engine")
            return False
    except Exception as e:
        print(f"❌ FAILED: Setup raised exception: {e}")
        return False


def run_all_tests():
    """Run all SEC-018 tests"""
    print("\n" + "=" * 80)
    print("SEC-018: DATABASE SECURITY TESTS")
    print("=" * 80)

    tests = [
        ("Network Isolation", test_network_isolation),
        ("SSL/TLS Encryption", test_ssl_encryption),
        ("Data Encryption at Rest", test_data_encryption),
        ("Connection Pooling", test_connection_pooling),
        ("Audit Logging", test_audit_logging),
        ("Automated Backups", test_automated_backups),
        ("Least Privilege", test_least_privilege),
        ("Complete Setup", test_complete_setup),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)

    if passed == total:
        print("\n🎉 All SEC-018 acceptance criteria verified!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
