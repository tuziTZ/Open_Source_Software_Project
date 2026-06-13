import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export type ProviderSummary = components["schemas"]["ProviderSummary"];

export interface CreateProviderRequest {
  name: string;
  kind?: string;
  model?: string;
  base_url?: string;
  api_key?: string;
  api_key_header?: string;
  is_default?: boolean;
}

export interface UpdateProviderRequest {
  name?: string;
  kind?: string;
  model?: string;
  base_url?: string;
  api_key?: string;
  api_key_header?: string;
  is_default?: boolean;
}

export function getProviders(client: IpcClient) {
  return client.request<ProviderSummary[]>("GET", "/providers/");
}

export function getProvider(client: IpcClient, name: string) {
  return client.request<ProviderSummary | null>("GET", `/providers/${name}`);
}

export function getDefaultProvider(client: IpcClient) {
  return client.request<ProviderSummary | null>("GET", "/providers/default");
}

export function createProvider(client: IpcClient, body: CreateProviderRequest) {
  return client.request<{ status: string; name: string }, CreateProviderRequest>(
    "POST",
    "/providers/",
    { body }
  );
}

export function updateProvider(client: IpcClient, name: string, body: UpdateProviderRequest) {
  return client.request<{ status: string; name: string }, UpdateProviderRequest>(
    "PUT",
    `/providers/${name}`,
    { body }
  );
}

export function setDefaultProvider(client: IpcClient, name: string) {
  return client.request<{ status: string; default: string }, { name: string }>(
    "POST",
    "/providers/default",
    { body: { name } }
  );
}

export function deleteProvider(client: IpcClient, name: string) {
  return client.request<{ status: string; name: string }>(
    "DELETE",
    `/providers/${name}`
  );
}

export function testProvider(client: IpcClient, name: string) {
  return client.request<{ status: string; provider: string; response?: string; error?: string }>(
    "POST",
    `/providers/test/${name}`
  );
}
