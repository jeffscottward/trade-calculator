"""
Debug version of calculator.py with enhanced error tracking
"""

import sys
import traceback
import logging

# Set up logging
import os
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/calculator_debug.log'),
        logging.StreamHandler()
    ]
)

try:
    logging.info("Starting calculator application...")
    logging.info(f"Python version: {sys.version}")
    
    logging.info("Setting up paths and importing tkinter_fix...")
    sys.path.insert(0, os.path.dirname(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    import tkinter_fix
    
    logging.info("Importing FreeSimpleGUI...")
    import FreeSimpleGUI as sg
    
    logging.info("Importing other modules...")
    import yfinance as yf
    from datetime import datetime, timedelta
    from scipy.interpolate import interp1d
    import numpy as np
    import threading
    
    logging.info("All imports successful")
    
    # Import the rest of the calculator code
    from calculator import *
    
    logging.info("Starting GUI...")
    gui()
    
except Exception as e:
    logging.error(f"Error occurred: {type(e).__name__}: {str(e)}")
    logging.error(f"Full traceback:\n{traceback.format_exc()}")
    print(f"\nError: {e}")
    print("\nFull error details have been saved to logs/calculator_debug.log")
    sys.exit(1)