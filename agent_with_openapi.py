import os
import jsonref
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from typing import Any
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects.models import OpenApiTool, OpenApiAnonymousAuthDetails


load_dotenv()

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(), conn_str=os.environ["PROJECT_CONNECTION_STRING"]
)

with open('./jsonplaceholder.json', 'r') as f:
    openapi_spec = jsonref.loads(f.read())

# Create Auth object for the OpenApiTool (note that connection or managed identity auth setup requires additional setup in Azure)
auth = OpenApiAnonymousAuthDetails()

# Initialize agent OpenApi tool using the read in OpenAPI spec
openapi = OpenApiTool(name="posts", spec=openapi_spec, description="Retrieve post information", auth=auth)

print(f"Created OpenAPI tool, definitions: {openapi.definitions}")



with project_client:

    agent = project_client.agents.create_agent(
        model="gpt-4o-mini",
        name="my-agent",
        instructions="You are helpful agent",
        tools=openapi.definitions  # adding this seems to result in an error
    )
    print(f"Created agent, agent ID: {agent.id}")

    # Create a thread
    thread = project_client.agents.create_thread()
    print(f"Created thread, thread ID: {thread.id}")

    while True:
        # Get user input
        user_question = input("Enter your question (or 'exit' to quit): ")
        
        # Check for exit condition
        if user_question.lower() == 'exit':
            break

        # Create a message
        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=user_question
        )
        print(f"Created message, message ID: {message.id}")

        # Run the agent
        run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            continue

        # Get messages from the thread
        messages = project_client.agents.list_messages(thread_id=thread.id)

        # Get the last message from the sender
        last_msg = messages.get_last_text_message_by_sender("assistant")
        if last_msg:
            print(f"Last Message: {last_msg.text.value}")
        
    # Delete the agent once done
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")