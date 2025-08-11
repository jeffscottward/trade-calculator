#!/usr/bin/env python3
"""
Test Yahoo Finance connection and rate limiting
"""

import time
import yfinance as yf
from datetime import datetime

print("Testing Yahoo Finance API...")
print(f"Time: {datetime.now()}")
print("-" * 50)

# Test 1: Simple ticker fetch
print("\nTest 1: Fetching NVDA ticker info...")
try:
    ticker = yf.Ticker("NVDA")
    info = ticker.info
    print(f"✓ Successfully fetched {info.get('longName', 'NVDA')} info")
    print(f"  Current price: ${info.get('currentPrice', 'N/A')}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Options chain
print("\nTest 2: Fetching NVDA options chain...")
try:
    ticker = yf.Ticker("NVDA")
    options_dates = ticker.options
    print(f"✓ Found {len(options_dates)} option expiration dates")
    if options_dates:
        print(f"  Next expiration: {options_dates[0]}")
        # Try to get the options for the first date
        opt_chain = ticker.option_chain(options_dates[0])
        print(f"  Calls: {len(opt_chain.calls)} contracts")
        print(f"  Puts: {len(opt_chain.puts)} contracts")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Clear cache and retry
print("\nTest 3: Clearing cache and retrying...")
try:
    import os
    cache_dir = os.path.expanduser("~/.cache/py-yfinance")
    if os.path.exists(cache_dir):
        import shutil
        shutil.rmtree(cache_dir)
        print("  Cache cleared")
    
    # Small delay to avoid immediate rate limit
    time.sleep(2)
    
    ticker = yf.Ticker("NVDA")
    options_dates = ticker.options
    print(f"✓ Successfully fetched options after cache clear")
except Exception as e:
    print(f"✗ Error after cache clear: {e}")

print("\n" + "-" * 50)
print("Test complete. If you see 429 errors, wait a few minutes and try again.")
print("Yahoo Finance has rate limits that reset after some time.")