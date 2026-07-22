import sys
import os
import io
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.platform.storage.object_storage import ObjectStorage

def test_object_storage_read_write_delete():
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = ObjectStorage(base_dir=temp_dir)
        
        bucket = "test_bucket"
        key = "folder/file.txt"
        file_content = b"hello platform storage"
        
        # 1. Put
        file_obj = io.BytesIO(file_content)
        dest_path = storage.put_object(bucket, key, file_obj)
        assert os.path.exists(dest_path)
        
        # 2. Get Path
        retrieved_path = storage.get_object_path(bucket, key)
        assert retrieved_path == dest_path
        
        # Read file
        with open(retrieved_path, "rb") as f:
            assert f.read() == file_content
            
        # 3. Delete
        success = storage.delete_object(bucket, key)
        assert success is True
        assert not os.path.exists(dest_path)
