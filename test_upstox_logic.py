import sys
import os
import logging

# Ensure we can import from local directory
sys.path.append(os.getcwd())

from bbt10.upstox_fo_complete import UpstoxFOData, UpstoxAuth

# Mock Auth
class MockAuth:
    def get_access_token(self):
        return "mock_token"

def test_logic():
    print("Testing UpstoxFOData logic...")
    
    try:
        # Initialize
        auth = MockAuth()
        fo_data = UpstoxFOData(auth)
        
        # Test _get_next_expiry signature
        symbol = "Nifty 50"
        category = "options"
        expiry_type = "weekly"
        
        print(f"Calling _get_next_expiry('{symbol}', '{category}', '{expiry_type}')...")
        expiry = fo_data._get_next_expiry(symbol, category, expiry_type)
        print(f"SUCCESS: Expiry returned: {expiry}")
        
    except TypeError as e:
        print(f"FAILED: TypeError caught: {e}")
    except Exception as e:
        print(f"FAILED: Other exception: {e}")

if __name__ == "__main__":
    test_logic()
