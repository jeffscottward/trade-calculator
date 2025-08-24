"""
Notification utilities for alerts and trade updates.
Supports email and Discord webhooks.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import Optional

from ..config import NOTIFICATION_CONFIG

logger = logging.getLogger(__name__)


def send_notification(subject: str, message: str, priority: str = "normal"):
    """Send notification through configured channels."""
    
    # Send email if enabled
    if NOTIFICATION_CONFIG['email_enabled']:
        send_email(subject, message, priority)
    
    # Send Discord webhook if configured
    if NOTIFICATION_CONFIG['discord_webhook']:
        send_discord(subject, message, priority)
    
    # Always log
    if priority == "high":
        logger.critical(f"{subject}: {message}")
    else:
        logger.info(f"{subject}: {message}")


def send_alert(subject: str, message: str, priority: str = "high"):
    """Send high-priority alert."""
    send_notification(f"🚨 ALERT: {subject}", message, priority)


def send_email(subject: str, body: str, priority: str = "normal"):
    """Send email notification."""
    if not all([
        NOTIFICATION_CONFIG['email_from'],
        NOTIFICATION_CONFIG['email_to'],
        NOTIFICATION_CONFIG['email_password']
    ]):
        logger.warning("Email not configured properly")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = NOTIFICATION_CONFIG['email_from']
        msg['To'] = NOTIFICATION_CONFIG['email_to']
        msg['Subject'] = f"[Trading Bot] {subject}"
        
        if priority == "high":
            msg['X-Priority'] = '1'
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(
            NOTIFICATION_CONFIG['email_smtp_server'],
            NOTIFICATION_CONFIG['email_smtp_port']
        ) as server:
            server.starttls()
            server.login(
                NOTIFICATION_CONFIG['email_from'],
                NOTIFICATION_CONFIG['email_password']
            )
            server.send_message(msg)
        
        logger.info(f"Email sent: {subject}")
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def send_discord(subject: str, message: str, priority: str = "normal"):
    """Send Discord webhook notification."""
    webhook_url = NOTIFICATION_CONFIG['discord_webhook']
    
    if not webhook_url:
        return
    
    try:
        # Format message for Discord
        color = 0xFF0000 if priority == "high" else 0x00FF00 if "✅" in message else 0x0099FF
        
        embed = {
            "title": subject,
            "description": message,
            "color": color,
            "footer": {
                "text": "Automated Trading System"
            }
        }
        
        payload = {
            "embeds": [embed]
        }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        
        logger.info(f"Discord notification sent: {subject}")
        
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")


def format_trade_summary(trades: list) -> str:
    """Format trade summary for notifications."""
    if not trades:
        return "No trades"
    
    summary = f"Total Trades: {len(trades)}\n"
    
    winners = [t for t in trades if t.get('pnl', 0) > 0]
    losers = [t for t in trades if t.get('pnl', 0) < 0]
    
    summary += f"Winners: {len(winners)}\n"
    summary += f"Losers: {len(losers)}\n"
    
    if trades:
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        summary += f"Total P&L: ${total_pnl:,.2f}\n"
        
        if len(winners) > 0:
            avg_win = sum(t['pnl'] for t in winners) / len(winners)
            summary += f"Avg Win: ${avg_win:,.2f}\n"
        
        if len(losers) > 0:
            avg_loss = sum(t['pnl'] for t in losers) / len(losers)
            summary += f"Avg Loss: ${avg_loss:,.2f}\n"
    
    return summary


def send_daily_report(metrics: dict):
    """Send daily performance report."""
    subject = "Daily Trading Report"
    
    message = "📊 DAILY PERFORMANCE SUMMARY\n"
    message += "="*40 + "\n\n"
    
    message += f"Date: {metrics.get('date', 'Today')}\n"
    message += f"Total Trades: {metrics.get('total_trades', 0)}\n"
    message += f"Winning Trades: {metrics.get('winning_trades', 0)}\n"
    message += f"Win Rate: {metrics.get('win_rate', 0):.1f}%\n"
    message += f"Total P&L: ${metrics.get('total_pnl', 0):,.2f}\n"
    
    if metrics.get('sharpe_ratio'):
        message += f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
    
    if metrics.get('max_drawdown'):
        message += f"Max Drawdown: {metrics['max_drawdown']:.2%}\n"
    
    message += "\n" + "="*40
    
    send_notification(subject, message)


def send_error_alert(error_type: str, error_details: str):
    """Send error alert notification."""
    subject = f"Error: {error_type}"
    
    message = f"⚠️ An error has occurred:\n\n"
    message += f"Type: {error_type}\n"
    message += f"Details: {error_details}\n"
    message += f"\nPlease check the system logs for more information."
    
    send_alert(subject, message, priority="high")