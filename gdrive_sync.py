import os
import time
import gdown
import streamlit as st

GDRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1woQ1E1KCa3ikUWp5YIlRaMdMwbMYkC8E?usp=sharing"
AUTO_DIR = "auto_logs"
SYNC_INTERVAL_SECONDS = 300  # Check Google Drive at most once every 5 minutes

def sync_from_gdrive(force: bool = False) -> bool:
    """
    Downloads new/updated files from Google Drive into auto_logs/.
    Uses timestamp throttling so it doesn't repeatedly download if no changes occur.
    Returns True if new files were downloaded or synced.
    """
    os.makedirs(AUTO_DIR, exist_ok=True)
    last_sync = st.session_state.get("last_gdrive_sync", 0)
    now = time.time()

    if not force and (now - last_sync < SYNC_INTERVAL_SECONDS):
        return False

    try:
        # Download files into auto_logs
        downloaded = gdown.download_folder(
            url=GDRIVE_FOLDER_URL,
            output=AUTO_DIR,
            quiet=True,
            use_cookies=False,
            remaining_ok=True
        )
        st.session_state["last_gdrive_sync"] = now
        return bool(downloaded and len(downloaded) > 0)
    except Exception as e:
        print(f"GDrive sync warning: {e}")
        return False
