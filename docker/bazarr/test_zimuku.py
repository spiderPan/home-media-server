import sys
import logging
import os

# Set up logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('subliminal_patch.providers.zimuku')

# Mock paths for imports to work inside bazarr container
sys.path.insert(0, '/app/bazarr/bin')
sys.path.insert(0, '/app/bazarr/bin/custom_libs')
sys.path.insert(0, '/app/bazarr/bin/libs')

from subliminal_patch.providers.zimuku import ZimukuProvider
from subliminal.video import Movie
from subzero.language import Language

def test_zimuku():
    print("--- Starting Zimuku IP Block Test ---")
    provider = ZimukuProvider()
    provider.initialize()
    
    test_url = "https://srtku.com/search?q=Inception"
    print(f"Attempting to fetch: {test_url}")
    
    try:
        # Use the bypass logic to see if we can get past the WAF
        r = provider.yunsuo_bypass(test_url, timeout=30)
        print(f"Response Status: {r.status_code}")
        
        if r.status_code == 200:
            print("SUCCESS: Connection established. Your IP is likely NOT blocked.")
            if "Inception" in r.text:
                print("SUCCESS: Page content retrieved correctly.")
            else:
                print("WARNING: Status 200 but content doesn't look like a search result.")
        elif r.status_code == 403:
            print("FAILURE: Status 403 (Forbidden). Your IP might be blocked or the WAF challenge changed.")
        else:
            print(f"FAILURE: Status {r.status_code}")
            
    except Exception as e:
        print(f"ERROR during connection: {e}")
    finally:
        provider.terminate()

if __name__ == "__main__":
    test_zimuku()
