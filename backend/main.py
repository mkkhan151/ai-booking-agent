from contextlib import asynccontextmanager

from agent import ChatClient
from database import DbSession, init_db
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, WebSocketException, status
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Booking Agent",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": f"Welcome to {app.title}"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: DbSession):
    """
    WebSocket endpoint for real-time chat.

    Args:
        websocket: WebSocket connection
        session_id: Unique client identifier for session management
        db: DbSession to query database for context
    """
    await websocket.accept()
    print(f"[WebSocket] Client {session_id} connected")

    # Create chat client instance for this connection
    chat_client = ChatClient(session_id, db)

    try:
        # Send welcome message
        await websocket.send_text(
            "Welcome to AI Booking Agent! How can I help you book a time slot today?"
        )

        # Main message loop
        while True:
            # Receive plain text message from client
            user_message = await websocket.receive_text()

            # Skip empty messages
            if not user_message.strip():
                continue

            print(f"[WebSocket] Received from {session_id}: '{user_message}'")

            # Process message through AI agent
            agent_response = chat_client.process_message(user_message)

            # Send response back as plain text
            await websocket.send_text(agent_response)
            print(f"[WebSocket] Sent to {session_id}: '{agent_response}'")

    except WebSocketDisconnect:
        print(f"[WebSocket] Client {session_id} disconnected normally")

    except Exception as e:
        print(f"[WebSocket] Error with client {session_id}: {e}")
        try:
            await websocket.send_text(f"An error occurred: {str(e)}")
        except:
            raise WebSocketException(
                status.WS_1011_INTERNAL_ERROR,
                reason="Something went wrong with connection.",
            )

    finally:
        # Cleanup
        db.close()
        print(f"[WebSocket] Session ended for {session_id}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
