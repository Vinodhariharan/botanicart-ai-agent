# backend/main.py

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel # Not directly used in the snippet for debugging .env, but keep if used elsewhere
import os
from dotenv import load_dotenv
import sys # For printing to stderr for visibility if stdout is captured

# --- BEGIN DEBUGGING .env LOADING ---
print("--- Debugging .env loading ---", file=sys.stderr)

# 1. Construct the path to the .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
print(f"Attempting to load .env file from: {dotenv_path}", file=sys.stderr)

# 2. Check if the .env file physically exists at that path
if os.path.exists(dotenv_path):
    print(f".env file FOUND at: {dotenv_path}", file=sys.stderr)
    
    # 3. Try to load it and check the result
    #    verbose=True might give more output from python-dotenv
    #    override=True ensures variables from .env take precedence
    load_success = load_dotenv(dotenv_path=dotenv_path, verbose=True, override=True)
    if load_success:
        print(".env file was loaded successfully by load_dotenv.", file=sys.stderr)
    else:
        print(".env file was NOT loaded by load_dotenv (load_dotenv returned False).", file=sys.stderr)
        print("This might happen if the file is empty or unreadable, even if it exists.", file=sys.stderr)
else:
    print(f".env file NOT FOUND at: {dotenv_path}", file=sys.stderr)

# 4. Check for GEMINI_API_KEY immediately after attempting to load
gemini_key_after_load = os.getenv("GEMINI_API_KEY")
if gemini_key_after_load:
    print(f"GEMINI_API_KEY found after load_dotenv: '{gemini_key_after_load[:5]}...'", file=sys.stderr) # Print first 5 chars for confirmation
else:
    print("GEMINI_API_KEY is STILL NOT FOUND in environment after load_dotenv.", file=sys.stderr)

print("--- End Debugging .env loading ---", file=sys.stderr)
# --- END DEBUGGING .env LOADING ---


# Your existing imports (ensure they are below the .env loading and debugging)
from agent.plant_agent import PlantRecommendationAgent
from models.schemas import ChatRequest, ChatResponse
from config.firebase_config import FirebaseConfig # Ensure Firebase is initialized

# Initialize FastAPI app
app = FastAPI(
    title="Plant Recommendation Chatbot API",
    description="API for plant recommendations and care guidance using LangChain and Gemini.",
    version="1.0.0"
)

# ... (rest of your main.py file remains the same) ...

# CORS (Cross-Origin Resource Sharing) Middleware
origins = [
    "http://localhost",         # Common for local development
    "http://localhost:3000",    # Default for React's create-react-app
    "http://localhost:5173",    # Default for Vite (React)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

plant_agent_instance: PlantRecommendationAgent = None

@app.on_event("startup")
async def startup_event():
    global plant_agent_instance
    
    print("Initializing Firebase...")
    try:
        FirebaseConfig.initialize_firebase() # This will also use os.getenv for Firebase keys
        print("Firebase initialized successfully.")
    except Exception as e:
        print(f"Critical Error: Failed to initialize Firebase: {e}", file=sys.stderr)

    # This is where your error originates
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("Critical Error: GEMINI_API_KEY not found in environment variables AT STARTUP.", file=sys.stderr)
        raise RuntimeError("GEMINI_API_KEY is not set. The application cannot start.")
    else:
        print(f"GEMINI_API_KEY successfully retrieved at startup: '{gemini_api_key[:5]}...'", file=sys.stderr)
    
    print("Initializing Plant Recommendation Agent...")
    plant_agent_instance = PlantRecommendationAgent(gemini_api_key=gemini_api_key)
    print("Plant Recommendation Agent initialized.")
    
@app.post("/chat", response_model=ChatResponse)
async def chat_with_plant_agent(request: ChatRequest = Body(...)):
    """
    Endpoint to interact with the plant recommendation chatbot.
    Receives a user message and returns the agent's response,
    including recommendations, care guides, and other relevant information.
    """
    if not plant_agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized. Please try again later.")
        
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        print(f"Received chat request: UserID='{request.user_id}', SessionID='{request.session_id}', Message='{request.message}'")
        
        # Get recommendation from the agent
        agent_output = plant_agent_instance.get_recommendation(
            user_message=request.message,
            user_id=request.user_id 
            # session_id could be used by the agent for conversation history if implemented
        )
        
        # Ensure the output conforms to the ChatResponse Pydantic model
        # The agent's get_recommendation method is designed to return a dict matching this structure.
        return ChatResponse(**agent_output)

    except Exception as e:
        print(f"Error during chat processing: {e}")
        # Return a generic error response conforming to ChatResponse schema
        return ChatResponse(
            response=f"An unexpected error occurred: {str(e)}. Please try again.",
            product_recommendations=[],
            care_guides=[],
            suggested_actions=["try_again", "contact_support"],
            confidence_score=0.0,
            query_understood={"error": str(e)}
        )

@app.get("/")
async def root():
    return {"message": "Welcome to the Plant Recommendation Chatbot API!"}

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    # Could add checks for DB connection, LLM accessibility etc.
    return {"status": "healthy", "firebase_initialized": bool(FirebaseConfig._db)}


# To run this FastAPI application (from the plant-chatbot/backend directory):
# uvicorn main:app --reload