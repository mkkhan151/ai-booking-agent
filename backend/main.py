from contextlib import asynccontextmanager
import asyncio

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

        # Track the current processing task to allow cancellation
        processing_task = None
        current_message_buffer = []

        async def process_and_respond(messages_to_process: str):
            """Helper to process message and send response"""
            try:
                # Process combined message through AI agent
                agent_response = await chat_client.process_message(messages_to_process)
                
                # Send response back as plain text
                await websocket.send_text(agent_response)
                print(f"[WebSocket] Sent to {session_id}: '{agent_response}'")
            except asyncio.CancelledError:
                print(f"[WebSocket] Processing cancelled for {session_id} (New message arrived)")
                raise # Re-raise to let asyncio handle it
            except Exception as e:
                print(f"[WebSocket] Error during processing: {e}")
                await websocket.send_text(f"Error: {str(e)}")

        def on_task_done(future):
            """Callback when a processing task finishes"""
            # If the task finished successfully (not cancelled, no exception),
            # it means it handled all messages currently in the buffer at the time of start.
            # In this strict cancellation model, if a new message had arrived, 
            # this task would have been cancelled.
            # So if it finishes, we can safely clear the buffer.
            if not future.cancelled() and not future.exception():
                current_message_buffer.clear()

        # Main message loop
        while True:
            # Receive message (blocking)
            try:
                new_message = await websocket.receive_text()
            except RuntimeError:
                break
            
            if not new_message.strip():
                continue

            print(f"[WebSocket] Received from {session_id}: '{new_message}'")
            
            # If there is an active task running, cancel it
            if processing_task and not processing_task.done():
                print(f"[WebSocket] Cancelling previous task for {session_id}")
                processing_task.cancel()
                try:
                    await processing_task 
                except asyncio.CancelledError:
                    pass # Expected
            
            # Add to buffer
            current_message_buffer.append(new_message)
            
            # Combine all pending messages
            full_context = "\n".join(current_message_buffer)
            
            # Start new processing task
            processing_task = asyncio.create_task(process_and_respond(full_context))
            processing_task.add_done_callback(on_task_done)

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
