import json
import os
from typing import Dict, List

import redis
from database import DbSession
from google import genai
from google.genai import types
from tools import book_slot, check_availability


class ChatClient:
    """
    Manages individual session chat sessions with the AI booking agent.

    Responsibilities:
    - Session management with unique session ID
    - Conversation history persistence in Redis
    - Message processing through Gemini AI
    - Tool execution (check_availability, book_slot)
    - Response generation and delivery
    """

    # Class-level configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    CHAT_HISTORY_TTL = 3600 * 24  # 24 hours
    MAX_TOOL_ITERATIONS = 5  # Prevent infinite loops
    MODEL = "gemini-3-flash-preview"

    # System instruction for the AI agent
    SYSTEM_INSTRUCTION = """You are a polite and efficient Booking Assistant. Your role is to help users book 1-hour time slots between 9 AM and 5 PM.

Each booking is exactly 1 hour long. If a user needs multiple hours, you should book consecutive slots separately.

Follow this protocol:
1. Greet the user warmly and ask for their name if not provided.
2. Ask for the date they want to book (format: YYYY-MM-DD).
3. Use check_availability to show available 1-hour slots for that date.
4. Ask which time slot they prefer (e.g., 9-10 AM, 2-3 PM, etc.).
5. Confirm the booking details with the user before finalizing.
6. Use book_slot to complete the booking.
7. Provide a clear confirmation with the booking ID.
8. If they need multiple hours, offer to book additional consecutive slots.

Important rules:
- Always be polite and professional
- Each slot is exactly 1 hour (9-10, 10-11, 11-12, etc.)
- Available slots: 9-10, 10-11, 11-12, 12-1, 1-2, 2-3, 3-4, 4-5 (8 slots total)
- If a slot is unavailable, suggest alternatives
- Always confirm details before booking
- Provide clear error messages if something goes wrong
- For multiple hours, book each slot individually"""

    # Tool Declarations
    TOOLS = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=check_availability.__name__,
                description="Check available 1-hour time slots for a specific date between 9 AM and 5 PM. Each slot is exactly 1 hour.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "date_str": types.Schema(
                            type=types.Type.STRING,
                            description="The date to check in YYYY-MM-DD format (e.g., 2026-01-20)",
                        )
                    },
                    required=["date_str"],
                ),
            ),
            types.FunctionDeclaration(
                name=book_slot.__name__,
                description="Book a 1-hour time slot for a user. Each booking is exactly 1 hour long.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "user_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the user making the booking",
                        ),
                        "date_str": types.Schema(
                            type=types.Type.STRING,
                            description="The date for the booking in YYYY-MM-DD format (e.g., 2026-01-20)",
                        ),
                        "hour": types.Schema(
                            type=types.Type.INTEGER,
                            description="Starting hour in 24-hour format (9-16, where 9=9AM, 10=10AM, 16=4PM)",
                        ),
                    },
                    required=["user_name", "date_str", "hour"],
                ),
            ),
        ]
    )

    # Object-level configuration
    def __init__(self, session_id: str, db: DbSession) -> None:
        """
        Initialize a new chat client.

        Args:
            session_id: Unique identifier for this client session
            db_session: SQLAlchemy database session for tool operations
        """

        self.session_id = session_id
        self.db = db
        self.redis_key = f"chat:{session_id}"
        # Initialize redis client
        self.redis_client = redis.from_url(self.REDIS_URL, decode_responses=True)
        # Initialize gemini client
        # It will automatically look for GEMINI_API_KEY environment variable
        self.client = genai.Client()

        print(f"[Client {self.session_id}] Initialized with new google-genai SDK")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Retrieve conversation history from Redis.

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        try:
            history_json = str(self.redis_client.get(self.redis_key))
            if history_json:
                history = json.loads(history_json)
                print(
                    f"[Client {self.session_id}] Loaded {len(history)} messages from history"
                )
                return history
            return []
        except Exception as e:
            print(f"[Client {self.session_id}] Error loading history: {e}")
            return []

    def save_conversation_history(self, history: List[Dict[str, str]]) -> None:
        """
        Save conversation history to Redis with expiration.

        Args:
            history: List of message dictionaries to save
        """
        try:
            self.redis_client.setex(
                self.redis_key, self.CHAT_HISTORY_TTL, json.dumps(history)
            )
            print(
                f"[Client {self.session_id}] Saved {len(history)} messages to history"
            )
        except Exception as e:
            print(f"[Client {self.session_id}] Error saving history: {e}")

    def append_to_history(self, role: str, content: str) -> None:
        """
        Append a single message to conversation history.

        Args:
            role: Message role ('user' or 'model')
            content: Message content
        """
        history = self.get_conversation_history()
        history.append({"role": role, "content": content})
        self.save_conversation_history(history)

    def clear_history(self) -> None:
        """Clear conversation history from Redis."""
        try:
            self.redis_client.delete(self.redis_key)
            print(f"[Client {self.session_id}] Cleared conversation history")
        except Exception as e:
            print(f"[Client {self.session_id}] Error clearing history: {e}")

    def build_chat_history_for_gemini(
        self, history: List[Dict[str, str]]
    ) -> List[types.Content]:
        """
        Convert our history format to Gemini's expected format (new SDK).

        Args:
            history: Our conversation history

        Returns:
            List of Content objects formatted for Gemini chat
        """
        contents = []
        for msg in history:
            if msg["role"] == "user":
                contents.append(
                    types.Content(role="user", parts=[types.Part(text=msg["content"])])
                )
            elif msg["role"] == "model":
                contents.append(
                    types.Content(role="model", parts=[types.Part(text=msg["content"])])
                )
        return contents

    def execute_tool(self, function_name: str, function_args: Dict) -> str:
        """
        Execute a tool function and return the result.

        Args:
            function_name: Name of the function to execute
            function_args: Dictionary of function arguments

        Returns:
            String result from the tool execution
        """
        print(
            f"[Client {self.session_id}] Executing tool: {function_name} with args: {function_args}"
        )

        try:
            if function_name == check_availability.__name__:
                result = check_availability(self.db, function_args["date_str"])

            elif function_name == book_slot.__name__:
                result = book_slot(
                    self.db,
                    function_args["user_name"],
                    function_args["date_str"],
                    function_args["hour"],
                )

            else:
                result = f"Error: Unknown function '{function_name}'"

            print(f"[Client {self.session_id}] Tool result: {result}")
            return result

        except Exception as e:
            error_msg = f"Error executing {function_name}: {str(e)}"
            print(f"[Client {self.session_id}] {error_msg}")
            return error_msg

    def process_message(self, user_message: str) -> str:
        """
        Process a user message through the AI agent with tool calling.

        This is the main method that:
        1. Loads conversation history
        2. Sends message to Gemini
        3. Handles tool calls (function calling)
        4. Returns final response
        5. Saves updated history

        Args:
            user_message: The message from the user

        Returns:
            Agent's response string
        """
        try:
            print(f"[Client {self.session_id}] Processing message: '{user_message}'")

            # Get conversation history
            history = self.get_conversation_history()

            # Build Gemini-format history
            contents = self.build_chat_history_for_gemini(history)

            # Add user message to contents
            contents.append(
                types.Content(role="user", parts=[types.Part(text=user_message)])
            )

            # Generate response with the new SDK
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=[self.TOOLS],
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=0.7,
                    max_output_tokens=400,
                ),
            )

            # Handle tool calling loop
            iteration = 0
            current_contents = contents.copy()

            while iteration < self.MAX_TOOL_ITERATIONS:
                # Check if there are function calls in the response
                if (
                    response.candidates
                    and response.candidates[0].content
                    and response.candidates[0].content.parts
                ):
                    has_function_call = False
                    function_responses = []

                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            has_function_call = True
                            function_name = part.function_call.name
                            function_args = part.function_call.args

                            # execute the tool
                            tool_result = self.execute_tool(
                                function_name, function_args
                            )

                            # Create function response
                            function_responses.append(
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=function_name,
                                        response={"result": tool_result},
                                    )
                                )
                            )
                    if has_function_call:
                        # Add model's response to history
                        current_contents.append(response.candidates[0].content)

                        # Add function responses
                        current_contents.append(
                            types.Content(role="user", parts=function_responses)
                        )

                        # Send function results back to model
                        response = self.client.models.generate_content(
                            model=self.MODEL,
                            contents=current_contents,
                            config=types.GenerateContentConfig(
                                tools=[self.TOOLS],
                                system_instruction=self.SYSTEM_INSTRUCTION,
                                temperature=0.7,
                                max_output_tokens=400,
                            ),
                        )

                        iteration += 1
                    else:
                        # No function calls, we have the final response
                        break
                else:
                    break
            # Extract final text response
            final_response = response.text if response.text else "No Response"
            print(f"[Client {self.session_id}] Generated response: '{final_response}'")

            # Update conversation history
            self.append_to_history("user", user_message)
            self.append_to_history("model", final_response)

            return final_response
        except Exception as e:
            error_msg = (
                f"I apologize, but I encountered an error: {str(e)}. Please try again."
            )
            print(f"[Client {self.session_id}] Error processing message: {e}")
            return error_msg
