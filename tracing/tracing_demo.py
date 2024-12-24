import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from typing import Any
from pathlib import Path
from dotenv import load_dotenv
from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects.models import FunctionTool, ToolSet
from typing import Any, Callable, Set, Dict, List, Optional


load_dotenv()


# functions for agent to call
def turn_on_light(room: str) -> str:
    return f"Light in room {room} turned on"

# function to turn off light
def turn_off_light(room: str) -> str:
    return f"Light in room {room} turned off"

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(), conn_str=os.environ["PROJECT_CONNECTION_STRING"]
)

application_insights_connection_string = project_client.telemetry.get_connection_string()
if not application_insights_connection_string:
    print("Application Insights was not enabled for this project.")
    print("Enable it via the 'Tracing' tab in your AI Foundry project page.")
    exit()
configure_azure_monitor(connection_string=application_insights_connection_string)

scenario = os.path.basename(__file__)
tracer = trace.get_tracer(__name__)

user_functions: Set[Callable[..., Any]] = {
    turn_on_light,
    turn_off_light
}

functions = FunctionTool(user_functions)
toolset = ToolSet()
toolset.add(functions)

# set user question
user_question = "Can you turn on the light in the living room?"

with tracer.start_as_current_span(scenario):

    with project_client:
        agent = project_client.agents.create_agent(
            model="gpt-4o-mini",
            name="my-agent",
            instructions="You are helpful agent",
            toolset=toolset
        )
        print(f"Created agent, agent ID: {agent.id}")

        # Create a thread
        thread = project_client.agents.create_thread()
        print(f"Created thread, thread ID: {thread.id}")

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
            # Check if you got "Rate limit is exceeded.", then you want to get more quota
            print(f"Run failed: {run.last_error}")

        # Get messages from the thread
        messages = project_client.agents.list_messages(thread_id=thread.id)
        print(f"Messages: {messages}")

        # Get the last message from the sender
        last_msg = messages.get_last_text_message_by_sender("assistant")
        if last_msg:
            print(f"Last Message: {last_msg.text.value}")
            
        # Delete the agent once done
        project_client.agents.delete_agent(agent.id)
        print("Deleted agent")