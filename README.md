# Azure AI Agent Service Demo

This code is discussed in the following post: https://blog.baeke.info/2024/12/24/creating-an-agent-with-the-azure-ai-agent-sdk/

Ensure you have an Azure AI Foundry hub and project. The hub should have gpt-4o-mini deployed. You can use another model if you wish but then you have to change the Python code in `agent_api.py`.

Ensure you have the Azure CLI and use it to login to your Azure account. Use the command `az login` to login. Your account needs AI Developer role on the project.

In the main folder, create a `.env` file with the following content:

```bash
PROJECT_CONNECTION_STRING="connection string to Azure AI Foundry project"
JWT_SECRET="JWT secret if you want to protect routes"
```

If you do not want to protect routes, set JWT_SECRET to anything and check the routes to comment/uncomment the function signature.

In folder `agentui`, do the following:

- Install Python requirements: `pip install -r requirements.txt`
- Run the app: `python agent_api.py`
- Use VS Code Live Server to run `index.html` in folder `agentui`