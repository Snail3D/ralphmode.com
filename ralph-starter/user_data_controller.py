#!/usr/bin/env python3
"""
SEC-019: User Data Controller - Telegram Bot Integration

Integrates GDPR compliance features with the Telegram bot.

Bot commands:
- /privacy - Show privacy policy and consent info
- /mydata - View all your data (GDPR Article 15)
- /export - Export your data in JSON format (GDPR Article 20)
- /deleteme - Delete all your data (GDPR Article 17)

Usage in ralph_bot.py:
    from user_data_controller import (
        handle_privacy_command,
        handle_mydata_command,
        handle_export_command,
        handle_deleteme_command,
        check_user_consent
    )
    
    # Add handlers in main()
    application.add_handler(CommandHandler("privacy", handle_privacy_command))
    application.add_handler(CommandHandler("mydata", handle_mydata_command))
    application.add_handler(CommandHandler("export", handle_export_command))
    application.add_handler(CommandHandler("deleteme", handle_deleteme_command))
"""

import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import get_db
from gdpr import (
    ConsentManager,
    DataAccessController,
    DataExportController,
    DataDeletionController,
    GDPRConfig,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Consent Management
# =============================================================================

async def check_user_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user has consented to data processing.
    
    If not, show consent request.
    
    Args:
        update: Telegram update
        context: Bot context
    
    Returns:
        True if user has consented, False otherwise
    """
    user_id = update.effective_user.id
    
    with get_db() as db:
        if not ConsentManager.has_consented(db, user_id):
            await show_consent_request(update, context)
            return False
    
    return True


async def show_consent_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show GDPR consent request to user.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    consent_info = ConsentManager.request_consent_text()
    
    # Create consent buttons
    keyboard = [
        [
            InlineKeyboardButton(
                consent_info["accept_button"],
                callback_data="consent_accept"
            ),
            InlineKeyboardButton(
                consent_info["decline_button"],
                callback_data="consent_decline"
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        consent_info["message"],
        reply_markup=reply_markup,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


async def handle_consent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle consent button callbacks.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    with get_db() as db:
        if data == "consent_accept":
            # User accepted
            ConsentManager.record_consent(db, user_id, consented=True)
            
            await query.edit_message_text(
                "✅ **Thank you for your consent!**\n\n"
                "You can now use Ralph Mode. Your data rights:\n"
                "• View your data: /mydata\n"
                "• Export your data: /export\n"
                "• Delete your data: /deleteme\n\n"
                "Start a session with /ralph or /code"
            )
            
        elif data == "consent_decline":
            # User declined
            ConsentManager.record_consent(db, user_id, consented=False)
            
            await query.edit_message_text(
                "❌ **Consent Declined**\n\n"
                "We respect your choice. However, we cannot provide our service "
                "without processing your data.\n\n"
                "If you change your mind, you can restart the bot with /start."
            )


# =============================================================================
# Privacy Policy Command
# =============================================================================

async def handle_privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /privacy command - show privacy policy and data info.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    message = f"""
🔒 **Privacy & Data Protection**

**Data Controller:**
{GDPRConfig.DATA_CONTROLLER['name']}
{GDPRConfig.DATA_CONTROLLER['email']}

**What We Collect:**
We collect only the minimum data necessary:
• Your Telegram user ID and username
• Messages and code you send to the bot
• Session data (projects, tasks)
• Feedback you provide

**Why We Collect It:**
• To provide AI coding assistance
• To improve our service through feedback
• To ensure security and prevent abuse

**Third-Party Services:**
"""
    
    for processor in GDPRConfig.THIRD_PARTY_PROCESSORS:
        message += f"\n• **{processor['name']}**: {processor['purpose']}"
    
    message += f"""

**Data Retention:**
• User data: {GDPRConfig.RETENTION_PERIODS['user_data']} days after last activity
• Session data: {GDPRConfig.RETENTION_PERIODS['session_data']} days
• Feedback: {GDPRConfig.RETENTION_PERIODS['feedback_data']} days

**Your Rights (GDPR):**
• Right to Access: /mydata
• Right to Data Portability: /export
• Right to Erasure: /deleteme

📄 Full Privacy Policy: {GDPRConfig.PRIVACY_POLICY_URL}
📄 Terms of Service: {GDPRConfig.TERMS_OF_SERVICE_URL}
"""
    
    await update.message.reply_text(
        message.strip(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


# =============================================================================
# My Data Command (GDPR Article 15 - Right to Access)
# =============================================================================

async def handle_mydata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /mydata command - show user all their data.
    
    Implements GDPR Article 15: Right to Access
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user_id = update.effective_user.id
    
    # Check consent first
    if not await check_user_consent(update, context):
        return
    
    with get_db() as db:
        data = DataAccessController.get_user_data_summary(db, user_id)
        formatted_message = DataAccessController.format_data_for_display(data)
    
    await update.message.reply_text(
        formatted_message,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


# =============================================================================
# Export Data Command (GDPR Article 20 - Right to Data Portability)
# =============================================================================

async def handle_export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /export command - export user data in JSON format.
    
    Implements GDPR Article 20: Right to Data Portability
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user_id = update.effective_user.id
    
    # Check consent first
    if not await check_user_consent(update, context):
        return
    
    await update.message.reply_text(
        "📦 Preparing your data export...\n\n"
        "This may take a moment."
    )
    
    try:
        with get_db() as db:
            export_data = DataExportController.export_user_data(db, user_id)
        
        if export_data is None:
            await update.message.reply_text(
                "❌ No data found for your account."
            )
            return
        
        # Save export to file
        export_file = DataExportController.save_export_file(export_data, user_id)
        
        # Send file to user
        with open(export_file, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"ralph_mode_data_export_{user_id}.json",
                caption=(
                    "✅ **Data Export Complete**\n\n"
                    "Your complete data export in JSON format.\n"
                    "This file contains all data we have stored about you.\n\n"
                    "📋 GDPR Article 20: Right to Data Portability"
                )
            )
        
        # Clean up file after sending
        export_file.unlink()
        
    except Exception as e:
        logger.error(f"Failed to export data for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Failed to export data. Please try again later or contact support."
        )


# =============================================================================
# Delete Me Command (GDPR Article 17 - Right to Erasure)
# =============================================================================

async def handle_deleteme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /deleteme command - delete all user data.
    
    Implements GDPR Article 17: Right to Erasure ("Right to be Forgotten")
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user_id = update.effective_user.id
    
    # Show confirmation warning
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Delete Everything", callback_data="delete_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="delete_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ **Delete All Data - Confirmation Required**\n\n"
        "This will **permanently delete**:\n"
        "• Your user profile\n"
        "• All your sessions\n"
        "• All your feedback\n"
        "• All other associated data\n\n"
        "**This action cannot be undone!**\n\n"
        "📋 GDPR Article 17: Right to Erasure\n\n"
        "Are you absolutely sure?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle delete confirmation callbacks.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "delete_confirm":
        # User confirmed deletion
        with get_db() as db:
            result = DataDeletionController.delete_user_data(db, user_id)
        
        if result["success"]:
            await query.edit_message_text(
                "✅ **Data Deletion Complete**\n\n"
                "All your data has been permanently deleted from our systems.\n\n"
                "If you want to use Ralph Mode again in the future, you'll need to "
                "provide consent again when you restart the bot.\n\n"
                "Thank you for using Ralph Mode!"
            )
        else:
            await query.edit_message_text(
                f"❌ **Deletion Failed**\n\n{result['message']}\n\n"
                "Please contact support if this issue persists."
            )
    
    elif data == "delete_cancel":
        # User cancelled
        await query.edit_message_text(
            "❌ **Deletion Cancelled**\n\n"
            "No data was deleted. Your account remains active."
        )


# =============================================================================
# Register Handlers
# =============================================================================

def register_gdpr_handlers(application):
    """
    Register all GDPR-related command handlers.
    
    Call this from ralph_bot.py main() to add GDPR commands.
    
    Args:
        application: Telegram application instance
    """
    from telegram.ext import CommandHandler
    
    # Command handlers
    application.add_handler(CommandHandler("privacy", handle_privacy_command))
    application.add_handler(CommandHandler("mydata", handle_mydata_command))
    application.add_handler(CommandHandler("export", handle_export_command))
    application.add_handler(CommandHandler("deleteme", handle_deleteme_command))
    
    # Callback handlers for consent and deletion
    application.add_handler(CallbackQueryHandler(
        handle_consent_callback,
        pattern="^consent_(accept|decline)$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_delete_callback,
        pattern="^delete_(confirm|cancel)$"
    ))
    
    logger.info("SEC-019: GDPR command handlers registered")


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SEC-019: User Data Controller - GDPR Bot Commands")
    print("=" * 70)
    print("\nAvailable Commands:")
    print("  /privacy    - View privacy policy and data info")
    print("  /mydata     - View all your data (GDPR Article 15)")
    print("  /export     - Export data in JSON (GDPR Article 20)")
    print("  /deleteme   - Delete all data (GDPR Article 17)")
    print("\nTo integrate with ralph_bot.py:")
    print("  from user_data_controller import register_gdpr_handlers")
    print("  register_gdpr_handlers(application)")
    print("=" * 70)
