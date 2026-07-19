import os
from typing import Any
from sqlalchemy.orm import Session
from backend.infrastructure.storage.base_storage import BaseBinaryStorage
from backend.infrastructure.storage.filesystem_storage import FilesystemStorage
from backend.infrastructure.storage.memory_storage import MemoryStorage
from backend.infrastructure.storage.artifact_store import ArtifactStore
from backend.infrastructure.storage.checkpoint_store import BaseCheckpointStore, BinaryCheckpointStore
from backend.infrastructure.storage.vector_store import BaseVectorStore
from backend.infrastructure.storage.qdrant_store import QdrantStore
from backend.infrastructure.storage.cache_store import BaseCacheStore
from backend.infrastructure.storage.redis_cache import RedisCache
from backend.infrastructure.storage.memory_cache import MemoryCache
from backend.repositories.unit_of_work import UnitOfWork
from backend.infrastructure.persistence.sqlalchemy.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

class StorageFactory:
    @staticmethod
    def create_storage(storage_type: str, **kwargs) -> BaseBinaryStorage:
        if storage_type.lower() == "filesystem":
            base_dir = kwargs.get("base_dir", "backend/storage")
            return FilesystemStorage(base_dir=base_dir)
        elif storage_type.lower() == "memory":
            return MemoryStorage()
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")

    @staticmethod
    def create_artifact_store(binary_storage: BaseBinaryStorage) -> ArtifactStore:
        return ArtifactStore(binary_storage=binary_storage)

    @staticmethod
    def create_checkpoint_store(binary_storage: BaseBinaryStorage) -> BaseCheckpointStore:
        return BinaryCheckpointStore(binary_storage=binary_storage)

class RepositoryFactory:
    @staticmethod
    def create_unit_of_work(session: Session) -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session=session)

class CacheFactory:
    @staticmethod
    def create_cache(cache_type: str, **kwargs) -> BaseCacheStore:
        if cache_type.lower() == "redis":
            host = kwargs.get("host", os.environ.get("REDIS_HOST", "localhost"))
            port = int(kwargs.get("port", os.environ.get("REDIS_PORT", 6379)))
            db = int(kwargs.get("db", os.environ.get("REDIS_DB", 0)))
            return RedisCache(host=host, port=port, db=db)
        elif cache_type.lower() == "memory":
            return MemoryCache()
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")

class VectorStoreFactory:
    @staticmethod
    def create_vector_store(store_type: str, **kwargs) -> BaseVectorStore:
        if store_type.lower() == "qdrant":
            return QdrantStore()
        else:
            raise ValueError(f"Unknown vector store type: {store_type}")
