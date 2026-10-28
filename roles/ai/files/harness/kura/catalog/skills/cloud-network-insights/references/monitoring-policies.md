# Monitoring Policy Configuration Reference (AppNeta API)

This guide covers configuring Network and Web Monitoring Policies
(`/api/v4/monitoringPolicy`) via the Broadcom AppNeta REST API v4.

## Contents

-   [1. Authentication and Organization Discovery](#1-authentication-and-organization-discovery)
-   [2. Network Monitoring Policies](#2-network-monitoring-policies)
-   [3. Web Monitoring Policies](#3-web-monitoring-policies)

## 1. Authentication and Organization Discovery

Because each shell command execution runs in an independent subshell, always
initialize `APPNETA_URL_HOST` and `APPNETA_TOKEN` (via Application Default
Credentials) in the same subshell block that executes `curl` against AppNeta
(where `PROVIDER_ID` is `external` when enabled via the Google Cloud console, or
a custom provider ID):

```bash
# 1. Initialize AppNeta host URL and bearer token in the active subshell
APPNETA_URL_HOST=$(gcloud network-management \
  network-monitoring-providers describe PROVIDER_ID \
  --location=global --project=PROJECT_ID --format="value(providerUri)" \
  | sed 's|^https\?://||')
APPNETA_TOKEN=$(gcloud network-management \
  network-monitoring-providers generate-provider-access-token PROVIDER_ID \
  --location=global --project=PROJECT_ID \
  --gcp-access-token=$(gcloud auth print-access-token 2>/dev/null \
    || gcloud auth application-default print-access-token) \
  --format="value(providerAccessToken)")

# 2. Discover Organization ID (`id` field in the response = ORG_ID)
curl -s -X GET "https://${APPNETA_URL_HOST}/api/v4/organization" \
  -H "Authorization: Bearer ${APPNETA_TOKEN}"

# 3. Execute any REST v4 API call in the same subshell using:
#    -H "Authorization: Bearer ${APPNETA_TOKEN}" \
#    -H "Content-Type: application/json"
```

-   **Reference Documentation**:
    -   [Broadcom AppNeta REST API v4 Documentation](https://techdocs.broadcom.com/us/en/ca-enterprise-software/it-operations-management/appneta-for-google-cloud-network-insights/GA/api/api-v4.html):
        Authentication headers, organization/policy/Monitoring Point ID lookup,
        and valid `APPNETA_MP_TYPE` values.
    -   **OpenAPI 3.0 Spec**:
        `https://${APPNETA_URL_HOST}/api/openapi.json?version=v4` (or Swagger UI
        at `https://${APPNETA_URL_HOST}/api/swagger/index.html#/`).

--------------------------------------------------------------------------------

## 2. Network Monitoring Policies

1.  **Check Existing Policies**: Query `GET
    https://${APPNETA_URL_HOST}/api/v4/monitoringPolicy` first to verify whether
    a policy with the target `name` already exists.
2.  **Create Network Monitoring Policy**: Send `POST
    https://${APPNETA_URL_HOST}/api/v4/monitoringPolicy` with the following JSON
    payload:

```json
{
  "orgId": ORG_ID,
  "name": "POLICY_NAME",
  "description": "DESCRIPTION",
  "monitoringEnabled": true,
  "target": "TARGET_IP",
  "networkMonitoring": {
    "dualEnded": false,
    "networkProtocol": "TCP",
    "networkPathGroupName": "Default"
  },
  "webHttpMonitoring": null,
  "monitoringPointRules": [
    {
      "filterRule": {
        "type": {
          "values": ["APPNETA_MP_TYPE"],
          "exclude": false
        }
      }
    }
  ]
}
```

-   `dualEnded`: `false` (single-ended against a target IP) or `true`
    (dual-ended between two AppNeta Monitoring Points).
-   `networkProtocol`: `"TCP"` (default) or `"UDP"`.
-   `APPNETA_MP_TYPE`: Must match the AppNeta Monitoring Point type string
    (such as `"c50 Container"` or `"v35 Virtual"` — see
    [Monitoring Point Types](https://techdocs.broadcom.com/us/en/ca-enterprise-software/it-operations-management/appneta-for-google-cloud-network-insights/GA/api/api-v4.html#title-appneta-api_monitoring-point-types)).
3.  **Delete Monitoring Policy (Cleanup)**: Send `DELETE
    https://${APPNETA_URL_HOST}/api/v4/monitoringPolicy/POLICY_ID` to remove a
    policy by ID.

--------------------------------------------------------------------------------

## 3. Web Monitoring Policies

After checking `GET https://${APPNETA_URL_HOST}/api/v4/monitoringPolicy`, create
an HTTP/HTTPS synthetic web policy via `POST
https://${APPNETA_URL_HOST}/api/v4/monitoringPolicy` with the following JSON
payload:

```json
{
  "orgId": ORG_ID,
  "name": "POLICY_NAME",
  "description": "DESCRIPTION",
  "monitoringEnabled": true,
  "target": "TARGET_URL",
  "networkMonitoring": {
    "dualEnded": false,
    "networkProtocol": "TCP",
    "networkPathGroupName": "Default"
  },
  "webHttpMonitoring": {
    "method": "GET",
    "intervalMinutes": 5,
    "timeoutSeconds": 60,
    "ignoreSslValidation": false,
    "followRedirects": true,
    "assertions": [
      {
        "type": "statuscode",
        "value": "200"
      }
    ]
  },
  "monitoringPointRules": [
    {
      "filterRule": {
        "type": {
          "values": ["APPNETA_MP_TYPE"],
          "exclude": false
        }
      }
    }
  ]
}
```
