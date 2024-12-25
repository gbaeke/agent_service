# Azure AI Agent Service Demo

In the main folder, create a .env file with the following content:

```bash
PROJECT_CONNECTION_STRING=connection string to Azure AI Foundry project
JWT_SECRET=JWT secret if you want to protect routes
```

If you do not want to protect routes, set JWT_SECRET to anything and check the routes to comment/uncomment the function signature.

In folder `agentui`, do the following:

- Install Python requirements: `pip install -r requirements.txt`
- Run the app: `python agent_api.py`
- Use VS Code Live Server to run `index.html` in folder `agentui`