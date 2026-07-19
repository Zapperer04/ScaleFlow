import os
import config
from backend.infrastructure.providers.provider_registry import ProviderRegistry
from backend.infrastructure.providers.provider_router import ProviderRouter
from backend.infrastructure.providers.provider_factory import ProviderFactory
from backend.application.parsing_service import ParsingServiceImpl

# Phase 4A Imports
from backend.infrastructure.factories import StorageFactory, RepositoryFactory, CacheFactory, VectorStoreFactory
from backend.models import SessionLocal

class ApplicationContainer:
    """Dependency Injection Container representing the wired up application."""
    def __init__(
        self,
        registry: ProviderRegistry,
        router: ProviderRouter,
        parsing_service: ParsingServiceImpl,
        storage=None,
        artifact_store=None,
        checkpoint_store=None,
        cache=None,
        vector_store=None,
        unit_of_work=None
    ):
        self.registry = registry
        self.router = router
        self.parsing_service = parsing_service
        self.storage = storage
        self.artifact_store = artifact_store
        self.checkpoint_store = checkpoint_store
        self.cache = cache
        self.vector_store = vector_store
        self.unit_of_work = unit_of_work

def bootstrap_app() -> ApplicationContainer:
    """Composition Root function to load config, wire dependencies, and return container."""
    # 1. Load config (config module does this on import)
    config.load_env()

    # 2. Instantiate providers using ProviderFactory
    gemini = ProviderFactory.create_provider("gemini")
    openrouter = ProviderFactory.create_provider("openrouter")
    ocr = ProviderFactory.create_provider("ocr")
    digital_pdf = ProviderFactory.create_provider("digital_pdf")
    llamaparse = ProviderFactory.create_provider("llamaparse")

    # 3. Register providers
    registry = ProviderRegistry()
    registry.register("gemini", gemini)
    registry.register("openrouter", openrouter)
    registry.register("ocr", ocr)
    registry.register("digital_pdf", digital_pdf)
    registry.register("llamaparse", llamaparse, enabled=False) # disabled stub

    # 4. Build router
    router = ProviderRouter(registry)

    # 5. Construct ParsingService
    parsing_service = ParsingServiceImpl(parser_provider=router)

    # 6. Instantiate Phase 4A Storage, Cache, Vector Store, and Unit of Work
    # Check environment/config database mode
    db_mode = os.environ.get("DB_MODE", "sqlite")
    storage_type = "filesystem"
    cache_type = "redis" if db_mode == "postgres" else "memory"
    
    # We default storage base directory
    base_storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
    storage = StorageFactory.create_storage(storage_type, base_dir=base_storage_dir)
    artifact_store = StorageFactory.create_artifact_store(storage)
    checkpoint_store = StorageFactory.create_checkpoint_store(storage)
    
    cache = CacheFactory.create_cache(cache_type)
    vector_store = VectorStoreFactory.create_vector_store("qdrant")
    
    session = SessionLocal()
    unit_of_work = RepositoryFactory.create_unit_of_work(session)

    return ApplicationContainer(
        registry=registry,
        router=router,
        parsing_service=parsing_service,
        storage=storage,
        artifact_store=artifact_store,
        checkpoint_store=checkpoint_store,
        cache=cache,
        vector_store=vector_store,
        unit_of_work=unit_of_work
    )
