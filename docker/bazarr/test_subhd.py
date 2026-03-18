import sys
import logging
import os

# Set up logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger('subliminal_patch.providers.yifysubtitles')

# Mock paths for imports to work inside bazarr container
sys.path.insert(0, '/app/bazarr/bin')
sys.path.insert(0, '/app/bazarr/bin/custom_libs')
sys.path.insert(0, '/app/bazarr/bin/libs')

from subliminal_patch.providers.yifysubtitles import YifySubtitlesProvider
from subliminal.video import Movie
# Bazarr uses a patched Language class
from subzero.language import Language

def test_search():
    print("--- Starting SubHD Test ---")
    provider = YifySubtitlesProvider()
    provider.initialize()
    
    # Mock a video object (e.g., Inception)
    video = Movie('Inception.2010.1080p.mkv', 'Inception', year=2010)
    languages = {Language('zho')}
    
    print(f"Searching for subtitles for: {video.title} ({video.year})")
    try:
        subtitles = provider.list_subtitles(video, languages)
        print(f"\nFound {len(subtitles)} Chinese subtitles:")
        for i, sub in enumerate(subtitles):
            print(f"[{i}] {sub.version} - {sub.page_link}")
            
        if subtitles:
            print(f"\nAttempting to download the first one: {subtitles[0].page_link}")
            provider.download_subtitle(subtitles[0])
            if hasattr(subtitles[0], 'content') and subtitles[0].content:
                print(f"SUCCESS: Downloaded {len(subtitles[0].content)} bytes of content.")
            else:
                print("FAILURE: Subtitle content is empty.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        provider.terminate()

if __name__ == "__main__":
    test_search()
