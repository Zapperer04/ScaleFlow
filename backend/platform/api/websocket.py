import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from backend.platform.runtime.app_state import app_state
from backend.platform.runtime.dependency_container import DependencyContainer
from backend.platform.security.auth import AuthManager
from backend.platform.security.permissions import PermissionManager
from backend.platform.streaming.events import PlatformEvent, EVENT_TOKEN_STREAM, EVENT_ANSWER_COMPLETE

router = APIRouter(tags=["WebSocket"])

@router.websocket("/chat/ws")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...)
):
    # Verify token
    payload = AuthManager.decode_token(token)
    if not payload or not PermissionManager.has_permission(payload.get("role", "user"), "write:chat"):
        await websocket.close(code=1008) # Policy Violation
        return

    await websocket.accept()
    app_state.active_websockets.append(websocket)
    
    conv_service = DependencyContainer.get_conversation_service()
    ret_service = DependencyContainer.get_retrieval_service()
    gen_service = DependencyContainer.get_generation_service()
    
    try:
        while True:
            # Receive client message
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            
            question = data.get("question")
            document_ids = data.get("document_ids", [])
            conv_id = data.get("conversation_id")
            model = data.get("model")
            
            if not question or not document_ids:
                await websocket.send_text(json.dumps({"error": "Missing question or document_ids"}))
                continue
                
            # Create session if not present
            if not conv_id:
                conv_id = conv_service.start_conversation(question[:30])
                
            # Retrieve memory
            from engine.document_retrieval.retrieval_memory import RetrievalSessionMemory
            session_memory = RetrievalSessionMemory()
            conv_service.recover_session_state(conv_id, session_memory)
            
            doc_id = document_ids[0]
            
            # Send start retrieval event
            await websocket.send_text(json.dumps({"event": "RETRIEVAL_STARTED", "data": {}}))
            
            # Retrieve
            ret_result = ret_service.retrieve(
                query=question,
                document_id=doc_id,
                session_id=conv_id
            )
            
            await websocket.send_text(json.dumps({
                "event": "EXPERT_COMPLETE",
                "data": {"latencies": ret_result.get("latencies", {})}
            }))
            
            # Start generation
            await websocket.send_text(json.dumps({"event": "GENERATION_STARTED", "data": {}}))
            
            gateway = DependencyContainer.get_inference_gateway()
            for token in gateway.stream_generate(question, model):
                await websocket.send_text(json.dumps({
                    "event": "TOKEN_STREAM",
                    "data": {"token": token}
                }))
                
            ans_result = gen_service.generate_answer(
                query=question,
                query_understanding=ret_result["query_understanding"],
                candidates=ret_result["final_context"]
            )
            
            # Persist state
            conv_service.record_turn(
                conversation_id=conv_id,
                user_message=question,
                assistant_message=ans_result.text,
                citations=[{"source": c.source, "text": c.text, "score": c.score} for c in ans_result.citations],
                metrics=ans_result.metrics
            )
            conv_service.persist_session_state(conv_id, session_memory)
            
            await websocket.send_text(json.dumps({
                "event": "ANSWER_COMPLETE",
                "data": {
                    "conversation_id": conv_id,
                    "answer": ans_result.text,
                    "citations": [{"source": c.source, "score": c.score} for c in ans_result.citations],
                    "confidence": ans_result.confidence
                }
            }))
            
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in app_state.active_websockets:
            app_state.active_websockets.remove(websocket)
