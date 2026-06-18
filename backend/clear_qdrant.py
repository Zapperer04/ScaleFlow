import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.vector_store import get_client, COLLECTIONS
import config

client = get_client()

for collection_name in list(COLLECTIONS.values()) + [config.QDRANT_COLLECTION_NAME]:
    try:
        print(f"Deleting collection: {collection_name}")
        client.delete_collection(collection_name=collection_name)
    except Exception as e:
        print(f"Error deleting {collection_name}: {e}")

from services.vector_store import ensure_collections_exist, ensure_collection
ensure_collections_exist()
ensure_collection(config.QDRANT_COLLECTION_NAME)
print("Collections recreated successfully.")
