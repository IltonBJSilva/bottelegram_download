from pathlib import Path
from datetime import datetime
import hashlib
from app.core.config import settings

def get_destination_path(folder_name: str, file_name: str, unique_id: str) -> Path:
    """
    Creates a dynamic path based on the current date and user folder.
    Ex: media/2026-08-14/palco/12345_video.mp4
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_dir = Path(settings.DOWNLOAD_DIR)
    
    # Clean folder name to avoid path traversal
    safe_folder = "".join([c for c in folder_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
    if not safe_folder:
        safe_folder = settings.DEFAULT_FOLDER
        
    final_dir = base_dir / today_str / safe_folder
    final_dir.mkdir(parents=True, exist_ok=True)
    
    return final_dir / f"{unique_id}_{file_name}"

async def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA256 hash asynchronously by reading chunks."""
    import asyncio
    
    # We run this in an executor to avoid blocking the asyncio event loop
    def _hash():
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _hash)
