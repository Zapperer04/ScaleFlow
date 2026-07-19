import os
import config
from backend.infrastructure.providers.provider_registry import ProviderRegistry
from backend.infrastructure.providers.provider_router import ProviderRouter
from backend.infrastructure.providers.provider_factory import ProviderFactory
from backend.application.parsing_service import ParsingServiceImpl

class ApplicationContainer:
    """Dependency Injection Container representing the wired up application."""
    def __init__(
        self,
        registry: ProviderRegistry,
        router: ProviderRouter,
        parsing_service: ParsingServiceImpl,
    ):
        self.registry = registry
        self.router = router
        self.parsing_service = parsing_service

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

    return ApplicationContainer(
        registry=registry,
        router=router,
        parsing_service=parsing_service,
    )
