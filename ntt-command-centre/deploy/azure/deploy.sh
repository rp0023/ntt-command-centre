#!/usr/bin/env bash
#
# Deploy both halves to Azure App Service (Linux, Web App for Containers).
#
#   AZ_PREFIX=nttcc-syren ./deploy/azure/deploy.sh
#
# Safe to re-run: existing resources are reused, images are rebuilt with a new
# tag and both apps are pointed at it. Images are built in Azure Container
# Registry (`az acr build`), so Docker is not needed on this machine.
#
# Creates (names derive from AZ_PREFIX, which must be globally unique):
#   resource group  $AZ_RG                         (default <prefix>-rg)
#   registry        <prefix, alphanumeric>acr       images ntt-api, ntt-web
#   plan            <prefix>-plan                   Linux, $AZ_SKU (default B2)
#   web app         <prefix>-api                    uvicorn on 8080
#   web app         <prefix>-web                    nginx on 80, proxies /api to <prefix>-api
#   storage         <prefix, alphanumeric>st        Azure Files share holding .demo-accounts.json
#
# Secrets: every KEY=VALUE in ./.env becomes an App Setting on the API app, and
# ./.demo-accounts.json is uploaded to the file share and mounted
# at /mnt/accounts. Neither ever enters an image.
#
set -euo pipefail
# Git Bash on Windows would otherwise rewrite /mnt/... and /subscriptions/... args.
export MSYS_NO_PATHCONV=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PREFIX="${AZ_PREFIX:?set AZ_PREFIX to a globally unique, lowercase name, e.g. nttcc-syren}"
LOCATION="${AZ_LOCATION:-eastus}"
RG="${AZ_RG:-$PREFIX-rg}"
SKU="${AZ_SKU:-B2}"
FLAT="$(echo "$PREFIX" | tr -cd 'a-z0-9')"
ACR="${AZ_ACR:-${FLAT:0:47}acr}"
STORAGE="${AZ_STORAGE:-${FLAT:0:22}st}"
PLAN="$PREFIX-plan"
API_APP="$PREFIX-api"
WEB_APP="$PREFIX-web"
SHARE="ntt-accounts"
MOUNT="/mnt/accounts"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo manual)-$(date +%Y%m%d%H%M%S)}"

API_URL="https://$API_APP.azurewebsites.net"
WEB_URL="https://$WEB_APP.azurewebsites.net"

step() { printf '\n▸ %s\n' "$*"; }

az account show --query "{subscription:name, id:id}" -o table >/dev/null \
  || { echo "not signed in — run: az login" >&2; exit 1; }
az account show --query "{subscription:name, id:id}" -o table

step "resource group $RG ($LOCATION)"
az group create -n "$RG" -l "$LOCATION" -o none

step "container registry $ACR"
az acr show -n "$ACR" -g "$RG" -o none 2>/dev/null \
  || az acr create -n "$ACR" -g "$RG" --sku Basic -o none
ACR_ID="$(az acr show -n "$ACR" -g "$RG" --query id -o tsv)"
LOGIN_SERVER="$(az acr show -n "$ACR" -g "$RG" --query loginServer -o tsv)"
API_IMAGE="$LOGIN_SERVER/ntt-api:$TAG"
WEB_IMAGE="$LOGIN_SERVER/ntt-web:$TAG"

step "build $API_IMAGE"
az acr build -r "$ACR" -t "ntt-api:$TAG" -t "ntt-api:latest" -f Dockerfile . -o none
step "build $WEB_IMAGE"
az acr build -r "$ACR" -t "ntt-web:$TAG" -t "ntt-web:latest" -f web/Dockerfile web -o none

step "app service plan $PLAN ($SKU, Linux)"
az appservice plan show -n "$PLAN" -g "$RG" -o none 2>/dev/null \
  || az appservice plan create -n "$PLAN" -g "$RG" --is-linux --sku "$SKU" -o none

# Create (or retarget) a container web app that pulls from ACR with its own
# managed identity — no registry passwords stored anywhere.
ensure_app() {
  local app="$1" image="$2"
  if ! az webapp show -n "$app" -g "$RG" -o none 2>/dev/null; then
    az webapp create -n "$app" -g "$RG" -p "$PLAN" --container-image-name "$image" \
      --assign-identity "[system]" --role AcrPull --scope "$ACR_ID" -o none
  fi
  az webapp config set -n "$app" -g "$RG" -o none \
    --generic-configurations '{"acrUseManagedIdentityCreds": true}'
  az webapp config container set -n "$app" -g "$RG" -o none \
    --container-image-name "$image" --container-registry-url "https://$LOGIN_SERVER"
  az webapp update -n "$app" -g "$RG" --https-only true -o none
  az webapp config set -n "$app" -g "$RG" -o none \
    --always-on true --ftps-state Disabled --min-tls-version 1.2 --http20-enabled true
}

step "api app $API_APP"
ensure_app "$API_APP" "$API_IMAGE"
az webapp config set -n "$API_APP" -g "$RG" -o none \
  --generic-configurations '{"healthCheckPath": "/healthz"}'

API_SETTINGS=(
  "WEBSITES_PORT=8080"
  # The first request trains the closure model; allow a slow first start.
  "WEBSITES_CONTAINER_START_TIME_LIMIT=600"
  "NTT_ALLOWED_ORIGINS=$WEB_URL"
)

# LLM keys and any other settings from the local .env (never baked into images).
if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=(.*)$ ]] || continue
    key="${BASH_REMATCH[1]}"
    val="$(echo "${BASH_REMATCH[2]}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e "s/^[\"']//" -e "s/[\"']\$//")"
    [[ -n "$val" ]] && API_SETTINGS+=("$key=$val")
  done < .env
  echo "  + $(( ${#API_SETTINGS[@]} - 3 )) setting(s) from .env"
fi

if [[ -f .demo-accounts.json ]]; then
  step "demo accounts → Azure Files ($STORAGE/$SHARE → $MOUNT)"
  az storage account show -n "$STORAGE" -g "$RG" -o none 2>/dev/null \
    || az storage account create -n "$STORAGE" -g "$RG" -l "$LOCATION" \
         --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 \
         --allow-blob-public-access false -o none
  KEY="$(az storage account keys list -n "$STORAGE" -g "$RG" --query '[0].value' -o tsv)"
  az storage share-rm show --storage-account "$STORAGE" -n "$SHARE" -g "$RG" -o none 2>/dev/null \
    || az storage share-rm create --storage-account "$STORAGE" -n "$SHARE" -g "$RG" --quota 1 -o none
  az storage file upload --account-name "$STORAGE" --account-key "$KEY" \
    --share-name "$SHARE" --source .demo-accounts.json --path demo-accounts.json -o none
  if az webapp config storage-account list -n "$API_APP" -g "$RG" --query "[?name=='accounts']" -o tsv | grep -q .; then
    az webapp config storage-account update -n "$API_APP" -g "$RG" --custom-id accounts \
      --storage-type AzureFiles --account-name "$STORAGE" --share-name "$SHARE" \
      --access-key "$KEY" --mount-path "$MOUNT" -o none
  else
    az webapp config storage-account add -n "$API_APP" -g "$RG" --custom-id accounts \
      --storage-type AzureFiles --account-name "$STORAGE" --share-name "$SHARE" \
      --access-key "$KEY" --mount-path "$MOUNT" -o none
  fi
  API_SETTINGS+=("NTT_DEMO_ACCOUNTS_FILE=$MOUNT/demo-accounts.json")
else
  echo "  ! no .demo-accounts.json — set NTT_EXECUTIVE_EMAIL, NTT_EXECUTIVE_PASSWORD and"
  echo "    NTT_ACCESS_SECRET in .env (or App Settings), or nobody can sign in"
fi

az webapp config appsettings set -n "$API_APP" -g "$RG" --settings "${API_SETTINGS[@]}" -o none

step "web app $WEB_APP"
ensure_app "$WEB_APP" "$WEB_IMAGE"
az webapp config set -n "$WEB_APP" -g "$RG" -o none \
  --generic-configurations '{"healthCheckPath": "/"}'
az webapp config appsettings set -n "$WEB_APP" -g "$RG" -o none --settings \
  "WEBSITES_PORT=80" "API_UPSTREAM=$API_URL"

step "restart"
az webapp restart -n "$API_APP" -g "$RG" -o none
az webapp restart -n "$WEB_APP" -g "$RG" -o none

step "waiting for $API_URL/healthz (first start trains the model; can take a few minutes)"
for _ in $(seq 1 60); do
  if curl -fsS "$API_URL/healthz" >/dev/null 2>&1; then ok=1; break; fi
  sleep 10
done
if [[ "${ok:-}" == 1 ]] && curl -fsS "$WEB_URL/healthz" >/dev/null 2>&1; then
  printf '\n✓ deployed %s\n  web  %s\n  api  %s\n' "$TAG" "$WEB_URL" "$API_URL"
else
  echo "not healthy yet — check: az webapp log tail -n $API_APP -g $RG" >&2
  exit 1
fi
