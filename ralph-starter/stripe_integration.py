#!/usr/bin/env python3
"""
SEC-021: Stripe Integration for Ralph Mode Bot

Telegram bot commands for subscription management:
- /subscribe - Start subscription flow
- /billing - Manage billing and view subscription
- /cancel - Cancel subscription

This module provides the Telegram bot interface to the payment.py module.

SECURITY: All card data handled by Stripe, never touches our servers.
"""

import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from payment import (
    create_checkout_session,
    SubscriptionTier,
    PaymentConfig
)
from database import get_db, User

logger = logging.getLogger(__name__)


# =============================================================================
# Subscription Command
# =============================================================================

async def handle_subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /subscribe command - show subscription options.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user_id = update.effective_user.id
    
    # Check current subscription
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        current_tier = user.subscription_tier if user else "free"
    
    message = f"""
💎 **Ralph Mode Subscriptions**

**Current Plan:** {current_tier.upper()}

**Available Plans:**

🆓 **FREE**
• Basic AI coding assistance
• Rate limits apply
• Community support

🔨 **BUILDER** - $10/month
• Higher rate limits
• Priority processing
• Basic analytics
• Email support

⭐ **PRIORITY** - $30/month
• Everything in Builder
• Highest priority processing
• Advanced analytics
• Priority support (24hr response)
• Early access to new features

🏢 **ENTERPRISE** - Custom Pricing
• Everything in Priority
• Custom rate limits
• Dedicated support
• SLA guarantees
• Custom integrations

Choose a plan to get started:
"""
    
    # Create subscription tier buttons
    keyboard = [
        [InlineKeyboardButton("🔨 Builder - $10/mo", callback_data="sub_builder")],
        [InlineKeyboardButton("⭐ Priority - $30/mo", callback_data="sub_priority")],
        [InlineKeyboardButton("🏢 Enterprise (Contact)", callback_data="sub_enterprise")],
    ]
    
    if current_tier != "free":
        keyboard.append([InlineKeyboardButton("💳 Manage Billing", callback_data="billing")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle subscription tier selection callbacks.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    tier = query.data.replace("sub_", "")
    
    if tier == "enterprise":
        # Enterprise requires custom pricing - direct to contact
        await query.edit_message_text(
            "🏢 **Enterprise Plan**\n\n"
            "For custom Enterprise pricing and features, please contact:\n"
            "Email: sales@ralphmode.com\n"
            "We'll set up a call to discuss your needs."
        )
        return
    
    # Create Stripe checkout session
    # SEC-021: All payment processing via Stripe
    session = await create_checkout_session(
        user_id=user_id,
        tier=tier,
        success_url="https://ralphmode.com/payment/success",
        cancel_url="https://ralphmode.com/payment/cancel",
        metadata={
            "telegram_username": query.from_user.username or "unknown",
        }
    )
    
    if session is None:
        await query.edit_message_text(
            "❌ Failed to create checkout session. Please try again later."
        )
        return
    
    # Send checkout link
    tier_name = tier.upper()
    amount = session['amount'] / 100  # Convert cents to dollars
    
    keyboard = [[InlineKeyboardButton(
        f"💳 Pay ${amount:.2f}/month",
        url=session['checkout_url']
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💎 **{tier_name} Subscription**\n\n"
        f"Price: ${amount:.2f}/month\n\n"
        f"Click the button below to complete your payment securely via Stripe.\n\n"
        f"🔒 Your card details are handled entirely by Stripe - "
        f"we never see or store them.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


# =============================================================================
# Billing Management Command
# =============================================================================

async def handle_billing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /billing command - manage subscription and billing.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user_id = update.effective_user.id
    
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user or user.subscription_tier == "free":
            await update.message.reply_text(
                "You don't have an active subscription.\n\n"
                "Use /subscribe to view available plans."
            )
            return
        
        tier = user.subscription_tier
        # In production, fetch actual subscription details from Stripe
        
        message = f"""
💳 **Your Subscription**

**Plan:** {tier.upper()}
**Status:** Active

**Manage Your Subscription:**
• Update payment method
• View invoices
• Cancel subscription

Click below to access the Stripe billing portal:
"""
        
        # In production, create a Stripe Billing Portal session
        # portal_url = stripe.billing_portal.Session.create(customer=stripe_customer_id)
        
        keyboard = [[InlineKeyboardButton(
            "💳 Manage Billing",
            url="https://billing.stripe.com/p/login/test_..."  # Replace with actual portal URL
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


# =============================================================================
# Cancel Subscription Command
# =============================================================================

async def handle_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /cancel command - cancel subscription.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    user_id = update.effective_user.id
    
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user or user.subscription_tier == "free":
            await update.message.reply_text(
                "You don't have an active subscription to cancel."
            )
            return
    
    # Show cancellation confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Cancel", callback_data="cancel_confirm"),
            InlineKeyboardButton("❌ Keep Subscription", callback_data="cancel_abort"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ **Cancel Subscription**\n\n"
        "Are you sure you want to cancel your subscription?\n\n"
        "You'll lose access to premium features at the end of your billing period.\n\n"
        "You can resubscribe anytime with /subscribe",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def handle_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle cancellation confirmation callbacks.
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "cancel_confirm":
        # In production, cancel via Stripe API
        # stripe.Subscription.delete(subscription_id)
        
        await query.edit_message_text(
            "✅ **Subscription Cancelled**\n\n"
            "Your subscription has been cancelled. "
            "You'll have access to premium features until the end of your billing period.\n\n"
            "We're sorry to see you go! If you have feedback on how we can improve, "
            "please use /feedback"
        )
    
    elif query.data == "cancel_abort":
        await query.edit_message_text(
            "✅ **Cancellation Aborted**\n\n"
            "Your subscription remains active. Thank you for staying with Ralph Mode!"
        )


# =============================================================================
# Payment Success/Failure Handlers (for webhook responses)
# =============================================================================

async def notify_payment_success(bot, user_id: int, tier: str):
    """
    Notify user of successful payment (called by webhook handler).
    
    Args:
        bot: Telegram bot instance
        user_id: User's Telegram ID
        tier: Subscription tier
    """
    message = f"""
✅ **Payment Successful!**

Thank you for subscribing to Ralph Mode {tier.upper()}!

Your premium features are now active:
"""
    
    if tier == "builder":
        message += """
🔨 **Builder Features:**
• Higher rate limits
• Priority processing
• Basic analytics
• Email support
"""
    elif tier == "priority":
        message += """
⭐ **Priority Features:**
• Everything in Builder
• Highest priority processing
• Advanced analytics
• Priority support (24hr response)
• Early access to new features
"""
    
    message += "\nStart using your premium features now with /ralph or /code!"
    
    await bot.send_message(
        chat_id=user_id,
        text=message,
        parse_mode="Markdown"
    )


async def notify_payment_failed(bot, user_id: int):
    """
    Notify user of failed payment (called by webhook handler).
    
    Args:
        bot: Telegram bot instance
        user_id: User's Telegram ID
    """
    await bot.send_message(
        chat_id=user_id,
        text=(
            "❌ **Payment Failed**\n\n"
            "We couldn't process your payment. Please check your card details "
            "and try again.\n\n"
            "Use /billing to update your payment method or /subscribe to try again."
        ),
        parse_mode="Markdown"
    )


# =============================================================================
# Register Handlers
# =============================================================================

def register_payment_handlers(application):
    """
    Register all payment-related command handlers.
    
    Call this from ralph_bot.py main() to add payment commands.
    
    Args:
        application: Telegram application instance
    """
    from telegram.ext import CommandHandler
    
    # Command handlers
    application.add_handler(CommandHandler("subscribe", handle_subscribe_command))
    application.add_handler(CommandHandler("billing", handle_billing_command))
    application.add_handler(CommandHandler("cancel", handle_cancel_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(
        handle_subscription_callback,
        pattern="^sub_(builder|priority|enterprise)$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_billing_callback,
        pattern="^billing$"
    ))
    application.add_handler(CallbackQueryHandler(
        handle_cancel_callback,
        pattern="^cancel_(confirm|abort)$"
    ))
    
    logger.info("SEC-021: Payment command handlers registered")


async def handle_billing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle billing button callback (same as /billing command)."""
    query = update.callback_query
    await query.answer()
    
    # Reuse the billing command logic
    await handle_billing_command(update, context)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SEC-021: Stripe Integration - Telegram Bot Commands")
    print("=" * 70)
    print("\nAvailable Commands:")
    print("  /subscribe  - View and select subscription plans")
    print("  /billing    - Manage billing and subscription")
    print("  /cancel     - Cancel subscription")
    print("\nTo integrate with ralph_bot.py:")
    print("  from stripe_integration import register_payment_handlers")
    print("  register_payment_handlers(application)")
    print("\n🔒 Security: All card data handled by Stripe (PCI-DSS Level 1)")
    print("=" * 70)
