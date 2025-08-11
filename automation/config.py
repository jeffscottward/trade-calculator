"""
Configuration management for automated trading system.
Loads sensitive data from environment variables.
"""

import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Validate required environment variables
REQUIRED_ENV_VARS = ['DATABASE_URL']

for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} is not set. Check .env file.")

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
db_url = urlparse(DATABASE_URL)

DATABASE_CONFIG = {
    'host': db_url.hostname,
    'port': db_url.port or 5432,
    'database': db_url.path[1:],
    'user': db_url.username,
    'password': db_url.password,
    'sslmode': 'require',
    'connect_timeout': 10
}

# Interactive Brokers Configuration
BROKER_CONFIG = {
    'provider': 'interactive_brokers',
    'host': os.getenv('IB_HOST', '127.0.0.1'),
    'port': int(os.getenv('IB_PORT', '7497')),  # 7497 for paper, 7496 for live
    'client_id': int(os.getenv('IB_CLIENT_ID', '1')),
    'account': os.getenv('IB_ACCOUNT', '')
}

# Data Provider Configuration
DATA_CONFIG = {
    'alpha_vantage_key': os.getenv('ALPHA_VANTAGE_KEY', ''),
    'earnings_horizon': '3month',
    'yfinance_cache': True,
    'yfinance_cache_dir': '.cache/yfinance'
}

# Strategy Configuration
STRATEGY_CONFIG = {
    'position_size_pct': 0.06,  # 6% per trade (10% Kelly)
    'max_concurrent_positions': 3,
    'term_structure_threshold': -0.1,  # Negative slope required
    'volume_threshold': 1_000_000,  # 1M shares minimum
    'iv_rv_threshold': 1.2,  # IV 20% higher than RV
    'min_days_to_expiry': 45,  # For back month selection
    'calendar_spread_gap_days': 30,  # Days between front and back month
    'entry_minutes_before_close': 15,
    'exit_minutes_after_open': 15
}

# Risk Management Configuration
RISK_CONFIG = {
    'max_daily_loss_pct': 0.10,  # 10% daily loss limit
    'max_consecutive_losses': 3,
    'max_portfolio_exposure': 0.20,  # 20% max exposure
    'min_stock_price': 20.0,
    'max_stock_price': 1000.0,
    'min_option_volume': 100,  # Minimum option contracts volume
    'emergency_stop_loss_pct': 0.15  # 15% loss triggers manual review
}

# Notification Configuration
NOTIFICATION_CONFIG = {
    'email_enabled': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
    'email_smtp_server': os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
    'email_smtp_port': int(os.getenv('EMAIL_SMTP_PORT', '587')),
    'email_from': os.getenv('EMAIL_FROM', ''),
    'email_to': os.getenv('EMAIL_TO', ''),
    'email_password': os.getenv('EMAIL_PASSWORD', ''),
    'discord_webhook': os.getenv('DISCORD_WEBHOOK', '')
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'file': 'logs/automation.log',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# Trading Hours (Eastern Time)
TRADING_HOURS = {
    'market_open': '09:30',
    'market_close': '16:00',
    'entry_time': '15:45',  # 15 minutes before close
    'exit_time': '09:45',   # 15 minutes after open
    'timezone': 'America/New_York'
}