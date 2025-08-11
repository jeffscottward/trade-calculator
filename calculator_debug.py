"""
Debug version of calculator.py with enhanced error tracking
"""

import sys
import traceback
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('calculator_debug.log'),
        logging.StreamHandler()
    ]
)

try:
    logging.info("Starting calculator application...")
    logging.info(f"Python version: {sys.version}")
    
    logging.info("Importing tkinter_fix...")
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
    print("\nFull error details have been saved to calculator_debug.log")
    sys.exit(1)