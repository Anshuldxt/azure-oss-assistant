# Deploying to Azure via GitHub Actions

The workflow at `.github/workflows/deploy-azure.yml` builds the Docker
image and deploys it to **Azure Container Apps** on every push to
`main`. It needs a few Azure resources and GitHub secrets/variables
set up **once** before the first run — everything below only has to be
done a single time.

You'll need the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
installed and logged in (`az login`) to run these.

## 1. Pick some names and create the resource group

```bash
# Change these to whatever you like -- ACR_NAME must be globally
# unique across all of Azure, lowercase letters/numbers only.
RG=oss-assistant-rg
LOCATION=eastus
ACR_NAME=ossassistantacr123      # <-- must be globally unique, change this
CONTAINERAPP_ENV=oss-assistant-env
CONTAINERAPP_NAME=oss-assistant

az group create --name $RG --location $LOCATION
```

## 2. Create the Azure Container Registry

```bash
az acr create --resource-group $RG --name $ACR_NAME --sku Basic --admin-enabled true
```

`--admin-enabled true` lets the workflow fetch a username/password to
pull the image (simplest option to get running). For a tighter setup
later, switch to a managed identity with an `AcrPull` role assignment
instead and drop the `--registry-username`/`--registry-password` lines
from the workflow.

## 3. Create a service principal for GitHub Actions to log in as

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az ad sp create-for-rbac \
  --name "oss-assistant-github-actions" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG \
  --sdk-auth
```

This prints a JSON blob like:
```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "..."
}
```
Copy the **entire JSON output** — you'll paste it into a GitHub secret next.

## 4. Add GitHub repo secrets and variables

In your GitHub repo: **Settings → Secrets and variables → Actions**

**Secrets** tab → *New repository secret*:
| Name | Value |
|---|---|
| `AZURE_CREDENTIALS` | the entire JSON blob from step 3 |

**Variables** tab → *New repository variable* (these aren't secret, just config):
| Name | Value |
|---|---|
| `ACR_NAME` | the value you picked for `$ACR_NAME` above |
| `ACR_LOGIN_SERVER` | `<ACR_NAME>.azurecr.io` |
| `RESOURCE_GROUP` | the value you picked for `$RG` above |
| `LOCATION` | the value you picked for `$LOCATION` above |
| `CONTAINERAPP_ENV` | the value you picked for `$CONTAINERAPP_ENV` above |
| `CONTAINERAPP_NAME` | the value you picked for `$CONTAINERAPP_NAME` above |

## 5. Push to main

```bash
git add .
git commit -m "Add Azure Container Apps CI/CD"
git push
```

Watch it run under the **Actions** tab of your GitHub repo. The last
step of the workflow prints the app's public URL
(`<something>.azurecontainerapps.io`) — open that in a browser and
you should see the OSS Assistant dashboard.

## Why min/max replicas are pinned to 1

The NE index lives in the process's memory (`backend/app/store.py`),
not a database. More than one replica would mean search results depend
on which instance happens to handle the request, and Container Apps'
default scale-to-zero behavior would silently wipe your uploaded data
the moment traffic goes quiet. The workflow pins the app to exactly one
replica so behavior stays predictable. If you outgrow a single
instance, move the store to Redis or SQLite first (see the "Scaling
notes" section in the main README), then relax this constraint.

## Redeploying manually

Push to `main`, or trigger it by hand from the **Actions** tab →
"Deploy to Azure Container Apps" → **Run workflow** (this is the
`workflow_dispatch` trigger in the yaml).

## Tearing it down

```bash
az group delete --name $RG --yes --no-wait
```

This deletes everything created above (registry, container app,
environment) in one shot.
