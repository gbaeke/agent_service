import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import CodeInterpreterTool
from azure.ai.projects.models import FunctionTool, ToolSet
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import base64
import jwt
from jwt.exceptions import InvalidTokenError
from dotenv import load_dotenv
from typing import Dict, Any, Callable, Set

# Load environment variables
load_dotenv(dotenv_path="../.env")

app = FastAPI()
security = HTTPBearer()

# Get JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable not set")



# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        print(f"Token payload: {payload}")
        return payload
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

# functions for agent to call
def turn_on_light(room: str) -> str:
    """
    Turns on the light in the specified room.

    :param room (str): The room where the light should be turned on.
    :return: Confirmation message.
    :rtype: str
    """
    return f"Light in room {room} turned on"

# function to turn off light
def turn_off_light(room: str) -> str:
    """
    Turns off the light in the specified room.

    :param room (str): The room where the light should be turned off.
    :return: Confirmation message.
    :rtype: str
    """
    
    return f"Light in room {room} turned off"

# function to get temperature in a location
def get_temperature(location: str) -> str:
    """
    Gets the current temperature for the specified location.

    :param location (str): The location to get the temperature for.
    :return: Current temperature message.
    :rtype: str
    """
    
    # Get lat/long from location using Nominatim API
    geocode_url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json"
    headers = {'User-Agent': 'Mozilla/5.0'}  # Required by Nominatim
    geo_response = requests.get(geocode_url, headers=headers)
    
    if not geo_response.json():
        return f"Could not find location: {location}"
    
    lat = geo_response.json()[0]['lat']
    lon = geo_response.json()[0]['lon']
    
    # Get weather data from Open-Meteo API
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    weather_response = requests.get(weather_url)
    
    if weather_response.status_code != 200:
        return f"Error getting temperature for {location}"
    
    temperature = weather_response.json()['current_weather']['temperature']
    return f"Current temperature in {location} is {temperature}°C"

# Set up credentials and project client
credential = DefaultAzureCredential()
conn_str = os.environ["PROJECT_CONNECTION_STRING"]
project_client = AIProjectClient.from_connection_string(
    credential=credential, conn_str=conn_str
)


user_functions: Set[Callable[..., Any]] = {
    turn_on_light,
    turn_off_light,
    get_temperature
}
functions = FunctionTool(user_functions)
toolset = ToolSet()
toolset.add(functions)

# Code interpreter tool
code_interpreter = CodeInterpreterTool()
toolset.add(code_interpreter)

# Create agent
agent = project_client.agents.create_agent(
    model="gpt-4o-mini",
    name="my-agent",
    instructions="You are helpful agent with functions to turn on/off light and get temperature in a location. If location is not specified, ask the user.",
    toolset=toolset
)

# Protected route to create a thread
# Switch the comments on the function signature to use the token verification or not

@app.post("/threads")
# async def create_thread() -> Dict[str, str]:
async def create_thread(payload: dict = Depends(verify_token)) -> Dict[str, str]:
    thread = project_client.agents.create_thread()
    return {"thread_id": thread.id}

class MessageRequest(BaseModel):
    message: str
    
# Protected route to add a message to a thread
# Switch the comments on the function signature to use the token verification or not

@app.post("/threads/{thread_id}/messages")
async def send_message(thread_id: str, request: MessageRequest, payload: dict = Depends(verify_token)):
# async def send_message(thread_id: str, request: MessageRequest):
    created_msg = project_client.agents.create_message(
        thread_id=thread_id,
        role="user",
        content=request.message  # Now accessing message from the request model
    )
    run = project_client.agents.create_and_process_run(
        thread_id=thread_id,
        assistant_id=agent.id
    )
    if run.status == "failed":
        return {"error": run.last_error or "Unknown error"}

    messages = project_client.agents.list_messages(thread_id=thread_id)
    last_msg = messages.get_last_message_by_sender("assistant")
    
    last_msg_text = last_msg.text_messages[0].text.value if last_msg.text_messages else None
    last_msg_image = last_msg.image_contents[0].image_file if last_msg.image_contents else None
    
    last_msg_image_b64 = None
    if last_msg_image:
        file_stream = project_client.agents.get_file_content(file_id=last_msg_image.file_id)
        base64_encoder = base64.b64encode
        byte_chunks = b"".join(file_stream)  # Concatenate all bytes from the iterator.
        last_msg_image_b64 = base64_encoder(byte_chunks).decode("utf-8")
        
    return {"assistant_text": last_msg_text, 
            "assistant_image": last_msg_image_b64}

if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        if agent:
            print(f"Deleting agent {agent.id}")
            project_client.agents.delete_agent(agent.id)