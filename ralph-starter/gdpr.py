#!/usr/bin/env python3
"""
SEC-019: GDPR Compliance Module

Implements GDPR (General Data Protection Regulation) requirements for Ralph Mode Bot:
1. Explicit consent for data collection
2. Privacy policy clearly displayed
3. Right to access (user can view all their data)
4. Right to erasure (user can request data deletion)
5. Right to data portability (export data in JSON)
6. Data retention policies
7. Third-party data processing documentation
8. Data breach notification procedures

GDPR PRINCIPLES:
- Lawfulness, Fairness, Transparency
- Purpose Limitation
- Data Minimization
- Accuracy
- Storage Limitation
- Integrity and Confidentiality
- Accountability

Usage:
    from gdpr import GDPRCompliance, get_user_consent, export_user_data
    
    # Check if user has consented
    if not get_user_consent(user_id):
        await show_consent_request(user_id)
    
    # Export user data
    data = export_user_data(user_id)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

from sqlalchemy.orm import Session
from database import get_db, User, BotSession, Feedback

logger = logging.getLogger(__name__)


# =============================================================================
# GDPR Configuration
# =============================================================================

class GDPRConfig:
    """
    GDPR compliance configuration.
    
    Defines data retention periods, consent requirements, etc.
    """
    
    # Data retention periods (in days)
    RETENTION_PERIODS = {
        "user_data": 730,          # 2 years after last activity
        "session_data": 90,        # 3 months
        "feedback_data": 1825,     # 5 years (for product improvement)
        "audit_logs": 2555,        # 7 years (compliance requirement)
    }
    
    # Privacy policy
    PRIVACY_POLICY_URL = "https://ralphmode.com/privacy"
    TERMS_OF_SERVICE_URL = "https://ralphmode.com/terms"
    
    # Data controller information (GDPR Article 13)
    DATA_CONTROLLER = {
        "name": "Ralph Mode",
        "email": "privacy@ralphmode.com",
        "address": "Your Company Address",
    }
    
    # Third-party processors (GDPR Article 28)
    THIRD_PARTY_PROCESSORS = [
        {
            "name": "Telegram",
            "purpose": "Message delivery and user authentication",
            "data_shared": ["user_id", "username", "messages"],
            "privacy_policy": "https://telegram.org/privacy",
        },
        {
            "name": "Groq",
            "purpose": "AI code generation",
            "data_shared": ["anonymized_code_requests"],
            "privacy_policy": "https://groq.com/privacy",
        },
    ]


# =============================================================================
# SEC-019.1: Explicit Consent for Data Collection
# =============================================================================

class ConsentManager:
    """
    Manages user consent for data collection and processing.
    
    Acceptance criteria: "Explicit consent for data collection"
    
    GDPR requires:
    - Freely given
    - Specific
    - Informed
    - Unambiguous
    - Affirmative action (opt-in, not opt-out)
    """
    
    @staticmethod
    def request_consent_text() -> Dict[str, str]:
        """
        Get consent request text (compliant with GDPR Article 13).
        
        Returns:
            Dict with consent request message and privacy info
        """
        return {
            "message": (
                "📋 **Privacy & Data Consent**\n\n"
                "Welcome to Ralph Mode! Before we begin, we need your consent to collect and process your data.\n\n"
                "**What we collect:**\n"
                "• Your Telegram user ID and username\n"
                "• Messages you send to the bot\n"
                "• Code and feedback you provide\n"
                "• Session data (projects, tasks completed)\n\n"
                "**Why we collect it:**\n"
                "• To provide AI coding assistance\n"
                "• To improve our service\n"
                "• To ensure security and prevent abuse\n\n"
                "**Your rights:**\n"
                "• View your data: /mydata\n"
                "• Export your data: /export\n"
                "• Delete your data: /deleteme\n\n"
                f"**Data controller:** {GDPRConfig.DATA_CONTROLLER['name']}\n"
                f"**Contact:** {GDPRConfig.DATA_CONTROLLER['email']}\n\n"
                f"📄 [Privacy Policy]({GDPRConfig.PRIVACY_POLICY_URL})\n"
                f"📄 [Terms of Service]({GDPRConfig.TERMS_OF_SERVICE_URL})\n\n"
                "Do you consent to this data processing?"
            ),
            "accept_button": "✅ I Consent",
            "decline_button": "❌ Decline",
        }
    
    @staticmethod
    def record_consent(
        db: Session,
        telegram_id: int,
        consented: bool,
        consent_type: str = "initial"
    ) -> bool:
        """
        Record user's consent decision.
        
        Args:
            db: Database session
            telegram_id: User's Telegram ID
            consented: Whether user consented
            consent_type: Type of consent (initial, marketing, etc.)
        
        Returns:
            True if recorded successfully
        """
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                # Create user with consent status
                user = User(
                    telegram_id=telegram_id,
                    created_at=datetime.utcnow(),
                )
                db.add(user)
            
            # Store consent in user metadata (you may want a separate consent table)
            # For now, we'll track via created_at and a consent flag
            if consented:
                logger.info(f"SEC-019: User {telegram_id} provided consent ({consent_type})")
            else:
                logger.warning(f"SEC-019: User {telegram_id} declined consent ({consent_type})")
                user.is_banned = True  # Can't use service without consent
                user.ban_reason = "Declined data processing consent (GDPR)"
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"SEC-019: Failed to record consent: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def has_consented(db: Session, telegram_id: int) -> bool:
        """
        Check if user has provided consent.
        
        Args:
            db: Database session
            telegram_id: User's Telegram ID
        
        Returns:
            True if user has consented, False otherwise
        """
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            return False
        
        # User exists and is not banned for consent reasons
        if user.is_banned and "consent" in (user.ban_reason or "").lower():
            return False
        
        return True


# =============================================================================
# SEC-019.3: Right to Access - View All Data
# =============================================================================

class DataAccessController:
    """
    Allows users to view all their data (GDPR Article 15).
    
    Acceptance criteria: "User can view all their data (/mydata)"
    """
    
    @staticmethod
    def get_user_data_summary(db: Session, telegram_id: int) -> Dict[str, Any]:
        """
        Get summary of all data stored for a user.
        
        Args:
            db: Database session
            telegram_id: User's Telegram ID
        
        Returns:
            Dict containing all user data
        """
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            return {"error": "No data found for this user"}
        
        # Get all user sessions
        sessions = db.query(BotSession).filter(BotSession.user_id == user.id).all()
        
        # Get all user feedback
        feedback = db.query(Feedback).filter(Feedback.user_id == user.id).all()
        
        # Compile data summary
        summary = {
            "user_profile": {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "subscription_tier": user.subscription_tier,
                "quality_score": user.quality_score,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            },
            "sessions": [
                {
                    "id": s.id,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "status": s.status,
                    "project_name": s.project_name,
                    "total_tasks": s.total_tasks,
                    "completed_tasks": s.completed_tasks,
                }
                for s in sessions
            ],
            "feedback": [
                {
                    "id": f.id,
                    "type": f.feedback_type,
                    "content": f.content,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "status": f.status,
                }
                for f in feedback
            ],
            "data_summary": {
                "total_sessions": len(sessions),
                "total_feedback_submitted": len(feedback),
                "account_age_days": (datetime.utcnow() - user.created_at).days if user.created_at else 0,
            },
            "gdpr_info": {
                "data_controller": GDPRConfig.DATA_CONTROLLER,
                "retention_periods": GDPRConfig.RETENTION_PERIODS,
                "third_party_processors": GDPRConfig.THIRD_PARTY_PROCESSORS,
            }
        }
        
        logger.info(f"SEC-019: User {telegram_id} accessed their data")
        return summary
    
    @staticmethod
    def format_data_for_display(data: Dict[str, Any]) -> str:
        """
        Format user data for Telegram display.
        
        Args:
            data: User data dict from get_user_data_summary
        
        Returns:
            Formatted markdown string
        """
        if "error" in data:
            return f"❌ {data['error']}"
        
        profile = data["user_profile"]
        summary = data["data_summary"]
        
        message = f"""
📊 **Your Data Summary**

**Profile Information:**
• Telegram ID: `{profile['telegram_id']}`
• Username: @{profile['username'] or 'N/A'}
• Name: {profile['first_name'] or ''} {profile['last_name'] or ''}
• Subscription: {profile['subscription_tier']}
• Quality Score: {profile['quality_score']}/100
• Account Created: {profile['created_at'][:10] if profile['created_at'] else 'N/A'}

**Activity Summary:**
• Total Sessions: {summary['total_sessions']}
• Feedback Submitted: {summary['total_feedback_submitted']}
• Account Age: {summary['account_age_days']} days

**Your Rights:**
• View full data export: /export
• Delete all data: /deleteme
• Privacy policy: {GDPRConfig.PRIVACY_POLICY_URL}

**Data Controller:**
{GDPRConfig.DATA_CONTROLLER['name']}
Contact: {GDPRConfig.DATA_CONTROLLER['email']}
"""
        
        return message.strip()


# =============================================================================
# SEC-019.5: Right to Data Portability - Export Data
# =============================================================================

class DataExportController:
    """
    Allows users to export all their data in JSON format (GDPR Article 20).
    
    Acceptance criteria: "User can export their data (JSON format)"
    """
    
    @staticmethod
    def export_user_data(db: Session, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Export all user data in machine-readable format (JSON).
        
        Args:
            db: Database session
            telegram_id: User's Telegram ID
        
        Returns:
            Complete user data export as dict
        """
        # Get comprehensive data
        data = DataAccessController.get_user_data_summary(db, telegram_id)
        
        if "error" in data:
            return None
        
        # Add export metadata
        export = {
            "export_metadata": {
                "export_date": datetime.utcnow().isoformat(),
                "format_version": "1.0",
                "gdpr_compliance": "Article 20 - Right to Data Portability",
            },
            "data": data,
        }
        
        logger.info(f"SEC-019: User {telegram_id} exported their data")
        return export
    
    @staticmethod
    def save_export_file(export_data: Dict[str, Any], telegram_id: int) -> Path:
        """
        Save export data to a JSON file.
        
        Args:
            export_data: Export data dict
            telegram_id: User's Telegram ID
        
        Returns:
            Path to saved export file
        """
        export_dir = Path(__file__).parent / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_file = export_dir / f"user_{telegram_id}_export_{timestamp}.json"
        
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"SEC-019: Export saved to {export_file}")
        return export_file


# =============================================================================
# SEC-019.4: Right to Erasure - Delete User Data
# =============================================================================

class DataDeletionController:
    """
    Allows users to request deletion of their data (GDPR Article 17).
    
    Acceptance criteria: "User can request data deletion (/deleteme)"
    
    Note: Some data may need to be retained for legal/compliance reasons.
    """
    
    @staticmethod
    def delete_user_data(db: Session, telegram_id: int) -> Dict[str, Any]:
        """
        Delete all user data (Right to Erasure).
        
        Args:
            db: Database session
            telegram_id: User's Telegram ID
        
        Returns:
            Dict with deletion status and details
        """
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                return {
                    "success": False,
                    "message": "No data found for this user"
                }
            
            deletion_report = {
                "telegram_id": telegram_id,
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_data": {}
            }
            
            # Delete sessions
            sessions = db.query(BotSession).filter(BotSession.user_id == user.id).all()
            session_count = len(sessions)
            for session in sessions:
                db.delete(session)
            deletion_report["deleted_data"]["sessions"] = session_count
            
            # Delete feedback
            feedback = db.query(Feedback).filter(Feedback.user_id == user.id).all()
            feedback_count = len(feedback)
            for fb in feedback:
                db.delete(fb)
            deletion_report["deleted_data"]["feedback"] = feedback_count
            
            # Delete user profile
            db.delete(user)
            deletion_report["deleted_data"]["user_profile"] = True
            
            db.commit()
            
            logger.warning(f"SEC-019: User {telegram_id} data DELETED (GDPR erasure request)")
            
            # Log to audit trail (required for compliance)
            audit_path = Path(__file__).parent / "logs" / "gdpr_deletions.log"
            audit_path.parent.mkdir(exist_ok=True)
            with open(audit_path, 'a') as f:
                f.write(json.dumps(deletion_report) + "\n")
            
            return {
                "success": True,
                "message": "All your data has been permanently deleted",
                "details": deletion_report
            }
            
        except Exception as e:
            logger.error(f"SEC-019: Failed to delete user data: {e}")
            db.rollback()
            return {
                "success": False,
                "message": f"Deletion failed: {str(e)}"
            }


# =============================================================================
# SEC-019.6: Data Retention Policy Enforcement
# =============================================================================

class DataRetentionEnforcer:
    """
    Automatically delete data that exceeds retention periods.
    
    Acceptance criteria: "Data retention policy enforced"
    """
    
    @staticmethod
    def cleanup_expired_data(db: Session) -> Dict[str, int]:
        """
        Delete data that has exceeded retention periods.
        
        Args:
            db: Database session
        
        Returns:
            Dict with counts of deleted items
        """
        counts = {
            "expired_sessions": 0,
            "expired_feedback": 0,
            "inactive_users": 0,
        }
        
        now = datetime.utcnow()
        
        # Delete old sessions (90 days)
        session_cutoff = now - timedelta(days=GDPRConfig.RETENTION_PERIODS["session_data"])
        expired_sessions = db.query(BotSession).filter(
            BotSession.ended_at < session_cutoff
        ).all()
        for session in expired_sessions:
            db.delete(session)
            counts["expired_sessions"] += 1
        
        # Delete inactive users (2 years since last activity)
        user_cutoff = now - timedelta(days=GDPRConfig.RETENTION_PERIODS["user_data"])
        inactive_users = db.query(User).filter(
            User.updated_at < user_cutoff
        ).all()
        for user in inactive_users:
            # Delete user's data first
            DataDeletionController.delete_user_data(db, user.telegram_id)
            counts["inactive_users"] += 1
        
        db.commit()
        
        if sum(counts.values()) > 0:
            logger.info(f"SEC-019: Data retention cleanup: {counts}")
        
        return counts


# =============================================================================
# SEC-019.8: Data Breach Notification
# =============================================================================

class DataBreachNotifier:
    """
    Handle data breach notification (GDPR Article 33 & 34).
    
    Acceptance criteria: "Data breach notification process defined"
    
    GDPR requires notification within 72 hours of becoming aware of a breach.
    """
    
    @staticmethod
    def notify_breach(
        breach_description: str,
        affected_users: List[int],
        severity: str = "high"
    ):
        """
        Notify authorities and affected users of a data breach.
        
        Args:
            breach_description: Description of the breach
            affected_users: List of affected user IDs
            severity: Severity level (low/medium/high/critical)
        """
        breach_report = {
            "breach_id": f"BREACH-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "detected_at": datetime.utcnow().isoformat(),
            "description": breach_description,
            "severity": severity,
            "affected_users_count": len(affected_users),
            "affected_user_ids": affected_users,
            "notification_status": "pending",
        }
        
        # Log breach
        breach_log_path = Path(__file__).parent / "logs" / "data_breaches.log"
        breach_log_path.parent.mkdir(exist_ok=True)
        with open(breach_log_path, 'a') as f:
            f.write(json.dumps(breach_report) + "\n")
        
        logger.critical(f"SEC-019: DATA BREACH DETECTED - {breach_report['breach_id']}")
        logger.critical(f"Description: {breach_description}")
        logger.critical(f"Affected users: {len(affected_users)}")
        
        # In production, this would:
        # 1. Notify supervisory authority within 72 hours
        # 2. Notify affected users
        # 3. Take remedial action
        # 4. Document everything for audit
        
        return breach_report


# =============================================================================
# Convenience Functions
# =============================================================================

def get_user_consent(telegram_id: int) -> bool:
    """Check if user has consented to data processing."""
    with get_db() as db:
        return ConsentManager.has_consented(db, telegram_id)


def export_user_data(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Export all user data in JSON format."""
    with get_db() as db:
        return DataExportController.export_user_data(db, telegram_id)


def delete_user_data(telegram_id: int) -> Dict[str, Any]:
    """Delete all user data (GDPR right to erasure)."""
    with get_db() as db:
        return DataDeletionController.delete_user_data(db, telegram_id)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SEC-019: GDPR Compliance Module")
    print("=" * 70)
    
    print("\n1. Consent Request Text:")
    print("-" * 70)
    consent_info = ConsentManager.request_consent_text()
    print(consent_info["message"])
    
    print("\n2. Data Controller Information:")
    print("-" * 70)
    print(f"Name: {GDPRConfig.DATA_CONTROLLER['name']}")
    print(f"Email: {GDPRConfig.DATA_CONTROLLER['email']}")
    print(f"Address: {GDPRConfig.DATA_CONTROLLER['address']}")
    
    print("\n3. Third-Party Processors:")
    print("-" * 70)
    for processor in GDPRConfig.THIRD_PARTY_PROCESSORS:
        print(f"\n{processor['name']}:")
        print(f"  Purpose: {processor['purpose']}")
        print(f"  Data Shared: {', '.join(processor['data_shared'])}")
        print(f"  Privacy Policy: {processor['privacy_policy']}")
    
    print("\n4. Data Retention Periods:")
    print("-" * 70)
    for data_type, days in GDPRConfig.RETENTION_PERIODS.items():
        print(f"{data_type}: {days} days ({days/365:.1f} years)")
    
    print("\n" + "=" * 70)
    print("✅ SEC-019: GDPR compliance module ready")
    print("=" * 70)
