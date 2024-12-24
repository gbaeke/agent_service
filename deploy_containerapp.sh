az containerapp up \
  --name ca-azureagent \
  --resource-group rg-azureagents \
  --location westeurope \
  --source . \
  --ingress external \
  --target-port 8000