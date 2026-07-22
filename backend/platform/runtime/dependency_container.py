from backend.platform.runtime.app_state import app_state

class DependencyContainer:
    @staticmethod
    def get_document_store():
        from backend.platform.storage.document_store import DocumentStore
        return DocumentStore()

    @staticmethod
    def get_artifact_store():
        from backend.platform.storage.artifact_store import ArtifactStore
        return ArtifactStore()

    @staticmethod
    def get_conversation_store():
        from backend.platform.storage.conversation_store import ConversationStore
        return ConversationStore(app_state.db_conn)

    @staticmethod
    def get_index_manager():
        from backend.platform.services.index_manager import IndexManager
        return IndexManager(
            document_store=DependencyContainer.get_document_store(),
            artifact_store=DependencyContainer.get_artifact_store()
        )

    @staticmethod
    def get_indexing_service():
        from backend.platform.services.indexing_service import IndexingService
        return IndexingService(
            queue=app_state.queue,
            index_manager=DependencyContainer.get_index_manager()
        )

    @staticmethod
    def get_inference_gateway():
        from backend.platform.services.inference_gateway import InferenceGateway
        return InferenceGateway()

    @staticmethod
    def get_retrieval_service():
        from backend.platform.services.retrieval_service import RetrievalService
        return RetrievalService()

    @staticmethod
    def get_generation_service():
        from backend.platform.services.generation_service import GenerationService
        return GenerationService(gateway=DependencyContainer.get_inference_gateway())

    @staticmethod
    def get_conversation_service():
        from backend.platform.services.conversation_service import ConversationService
        return ConversationService(
            store=DependencyContainer.get_conversation_store()
        )

    @staticmethod
    def get_document_service():
        from backend.platform.services.document_service import DocumentService
        return DocumentService(
            db_conn=app_state.db_conn,
            store=DependencyContainer.get_document_store()
        )
