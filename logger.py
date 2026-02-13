import logging
import sys
import os

def setup_logger(name=__name__, log_file="app.log", level=logging.INFO):
    """
    Sets up a logger with the Bloomberg Terminal standard.
    - Console output: Clean, structured.
    - File output: Detailed trace.
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Check if handlers already exist to avoid duplicate logs
    if logger.hasHandlers():
        return logger

    # Create formatters
    # Console: simpler, for "Observability"
    console_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
    
    # File: detailed, for debugging
    file_formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s')

    # Create handlers
    # 1. Stream (Console)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    
    # 2. File
    try:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG) # Always log debug to file
    except Exception as e:
        print(f"Failed to create log file handler: {e}")
        file_handler = None

    # Add handlers
    logger.addHandler(console_handler)
    if file_handler:
        logger.addHandler(file_handler)
        
    return logger

# Create a default instance for easy import
logger = setup_logger("BloombergTerminal")
