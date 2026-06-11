import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export function getProviders(client: IpcClient) {
  return client.request<components["schemas"]["ProviderSummaryResponse"][]>("GET", "/providers");
}

export function createProvider(
  client: IpcClient,
  body: components["schemas"]["ProviderUpsertRequest"]
) {
  return client.request<components["schemas"]["ProviderSummaryResponse"], components["schemas"]["ProviderUpsertRequest"]>(
    "POST",
    "/providers",
    { body }
  );
}

export function updateProvider(
  client: IpcClient,
  providerName: string,
  body: components["schemas"]["ProviderUpsertRequest"]
) {
  return client.request<components["schemas"]["ProviderSummaryResponse"], components["schemas"]["ProviderUpsertRequest"]>(
    "PUT",
    `/providers/${encodeURIComponent(providerName)}`,
    { body }
  );
}

export function deleteProvider(client: IpcClient, providerName: string) {
  return client.request<{ deleted: boolean }>("DELETE", `/providers/${encodeURIComponent(providerName)}`);
}
