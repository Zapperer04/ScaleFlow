import os
import shutil
from typing import BinaryIO

class ObjectStorage:
    """
    Abstract object storage provider. Maps objects to local disk space.
    """
    def __init__(self, base_dir: str = None):
        from backend.platform.config.settings import settings
        self.base_dir = base_dir or settings.BASE_STORAGE_PATH

    def put_object(self, bucket: str, key: str, file_obj: BinaryIO) -> str:
        dest_dir = os.path.join(self.base_dir, bucket)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, key)
        
        # Avoid creating nested missing dirs inside key if key contains slashes
        key_dir = os.path.dirname(dest_path)
        os.makedirs(key_dir, exist_ok=True)
        
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)
        return dest_path

    def get_object_path(self, bucket: str, key: str) -> str:
        return os.path.join(self.base_dir, bucket, key)

    def delete_object(self, bucket: str, key: str) -> bool:
        dest_path = self.get_object_path(bucket, key)
        if os.path.exists(dest_path):
            os.remove(dest_path)
            return True
        return False
