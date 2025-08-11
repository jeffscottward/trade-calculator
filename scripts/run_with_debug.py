#!/usr/bin/env python3
"""
Debug runner for calculator.py
Captures and displays all errors with full context
"""

import sys
import traceback
import logging
from datetime import datetime

# Set up detailed logging
import os
os.makedirs('logs', exist_ok=True)
log_filename = f'logs/debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("="*50)
        logger.info("Starting Trade Calculator Debug Session")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Log file: {log_filename}")
        logger.info("="*50)
        
        # Try importing each module separately to identify issues
        logger.info("Step 1: Setting up paths and importing tkinter_fix...")
        sys.path.insert(0, os.path.dirname(__file__))
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        import tkinter_fix
        logger.info("✓ tkinter_fix imported successfully")
        
        logger.info("Step 2: Importing FreeSimpleGUI...")
        import FreeSimpleGUI as sg
        logger.info(f"✓ FreeSimpleGUI version: {sg.version}")
        
        logger.info("Step 3: Importing yfinance...")
        import yfinance as yf
        logger.info("✓ yfinance imported successfully")
        
        logger.info("Step 4: Importing scipy...")
        from scipy.interpolate import interp1d
        logger.info("✓ scipy imported successfully")
        
        logger.info("Step 5: Importing numpy...")
        import numpy as np
        logger.info(f"✓ numpy version: {np.__version__}")
        
        logger.info("Step 6: Importing calculator module...")
        import calculator
        logger.info("✓ calculator module imported successfully")
        
        logger.info("Step 7: Starting GUI...")
        calculator.gui()
        
    except ImportError as e:
        logger.error(f"Import Error: {e}")
        logger.error(f"Module path: {sys.path}")
        logger.error(traceback.format_exc())
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected Error: {type(e).__name__}")
        logger.error(f"Error Message: {str(e)}")
        logger.error("Full Traceback:")
        logger.error(traceback.format_exc())
        
        # Try to provide more context
        if hasattr(e, '__traceback__'):
            tb = traceback.extract_tb(e.__traceback__)
            logger.error("\nError Location Details:")
            for frame in tb:
                logger.error(f"  File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
                logger.error(f"    Code: {frame.line}")
        
        return 1
    
    return 0

if __name__ == "__main__":
    logger.info("Starting debug runner...")
    exit_code = main()
    if exit_code == 0:
        logger.info("Calculator closed normally")
    else:
        logger.error(f"Calculator exited with error code: {exit_code}")
        print(f"\n⚠️  Error detected! Check {log_filename} for details")
    sys.exit(exit_code)