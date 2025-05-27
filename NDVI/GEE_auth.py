# Google Earth Engine Setup for NDVI Data Collection
# Step 1: Install required packages
# Run these commands in your terminal first:
# pip install earthengine-api
# pip install pandas numpy matplotlib

import ee
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Step 2: Authenticate and initialize Earth Engine
# First time setup - run this once to authenticate
def authenticate_gee():
    """
    One-time authentication setup for Google Earth Engine
    This will open a browser for you to sign in with your Google account
    """
    try:
        ee.Authenticate()
        print("Authentication successful!")
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Please visit https://earthengine.google.com/ to sign up for access")

# Initialize Earth Engine (run this every time you start your script)
def initialize_gee():
    """
    Initialize Google Earth Engine
    """
    try:
        ee.Initialize(project="agriaid-461007")
        print("Google Earth Engine initialized successfully!")
        return True
    except Exception as e:
        print(f"Initialization failed: {e}")
        print("Make sure you've authenticated first using authenticate_gee()")
        return False

# Example usage:
if __name__ == "__main__":
    # Uncomment the line below for first-time setup
    # authenticate_gee()
    
    # Run this every time
    initialize_gee()