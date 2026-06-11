import {
  createProvider,
  cleanStoredContent,
  deleteProvider,
  createFeed,
  deleteEntry,
  generateSummary,
  getEntries,
  getEntry,
  getFeeds,
  getProviders,
  getTags,
  importOpml,
  IpcError,
  setEntryReadState,
  setEntryStarState,
  syncAllFeeds,
  updateProvider
} from "@mercury/ipc-client";
import type { components } from "@mercury/shared-types";

import type { Entry, Feed, ProviderDraft, ProviderSummary, Tag } from "../../domain/types";
import { mercuryClient } from "./client";
import { toUiEntry, toUiFeed, toUiTag } from "./mappers";

export interface AppDataPayload {
  feeds: Feed[];
  tags: Tag[];
  entries: Entry[];
}

export async function loadAppData(): Promise<AppDataPayload> {
  const [feeds, tags, entries] = await Promise.all([
    getFeeds(mercuryClient),
    getTags(mercuryClient),
    getEntries(mercuryClient)
  ]);

  return {
    feeds: feeds.map(toUiFeed),
    tags: tags.map(toUiTag),
    entries: entries.map(toUiEntry)
  };
}

export async function loadEntry(entryId: string): Promise<Entry> {
  return toUiEntry(await getEntry(mercuryClient, entryId));
}

export async function updateEntryReadState(entryId: string, isRead: boolean): Promise<Entry> {
  return toUiEntry(await setEntryReadState(mercuryClient, entryId, { is_read: isRead }));
}

export async function updateEntryStarState(entryId: string, isStarred: boolean): Promise<Entry> {
  return toUiEntry(await setEntryStarState(mercuryClient, entryId, { is_starred: isStarred }));
}

export async function removeEntry(entryId: string): Promise<void> {
  await deleteEntry(mercuryClient, entryId);
}

export async function requestSummary(entryId: string): Promise<components["schemas"]["SummaryResult"]> {
  return generateSummary(mercuryClient, { entry_id: entryId });
}

export async function subscribeToFeed(url: string, sync = true): Promise<Feed> {
  return toUiFeed(await createFeed(mercuryClient, { url, sync }));
}

export async function importOpmlFile(file: File): Promise<components["schemas"]["OPMLImportResult"]> {
  return importOpml(mercuryClient, await file.text());
}

export async function syncFeeds(): Promise<components["schemas"]["SyncResult"][]> {
  return syncAllFeeds(mercuryClient);
}

export async function ensureEntryContent(entryId: string): Promise<components["schemas"]["CleanContentResponse"]> {
  return cleanStoredContent(mercuryClient, entryId);
}

export async function loadProviders(): Promise<ProviderSummary[]> {
  const providers = await getProviders(mercuryClient);
  return providers.map((provider) => ({
    name: provider.name,
    kind: provider.kind,
    model: provider.model,
    baseUrl: provider.base_url ?? null,
    apiKeyHeader: provider.api_key_header ?? null,
    isDefault: provider.is_default,
    hasApiKey: provider.has_api_key
  }));
}

export async function createProviderConfig(draft: ProviderDraft): Promise<ProviderSummary> {
  const provider = await createProvider(mercuryClient, toProviderRequest(draft));
  return {
    name: provider.name,
    kind: provider.kind,
    model: provider.model,
    baseUrl: provider.base_url ?? null,
    apiKeyHeader: provider.api_key_header ?? null,
    isDefault: provider.is_default,
    hasApiKey: provider.has_api_key
  };
}

export async function updateProviderConfig(providerName: string, draft: ProviderDraft): Promise<ProviderSummary> {
  const provider = await updateProvider(mercuryClient, providerName, toProviderRequest(draft));
  return {
    name: provider.name,
    kind: provider.kind,
    model: provider.model,
    baseUrl: provider.base_url ?? null,
    apiKeyHeader: provider.api_key_header ?? null,
    isDefault: provider.is_default,
    hasApiKey: provider.has_api_key
  };
}

export async function removeProviderConfig(providerName: string): Promise<void> {
  await deleteProvider(mercuryClient, providerName);
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof IpcError) {
    if (hasDetail(error.body)) {
      const detail = error.body.detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
    return `Request failed (${error.status})`;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Request failed";
}

function hasDetail(value: unknown): value is { detail?: unknown } {
  return typeof value === "object" && value !== null && "detail" in value;
}

function toProviderRequest(draft: ProviderDraft): components["schemas"]["ProviderUpsertRequest"] {
  return {
    name: draft.name.trim(),
    kind: draft.kind,
    model: draft.model.trim(),
    base_url: draft.baseUrl.trim() || null,
    api_key: draft.apiKey.trim() || null,
    api_key_header: draft.apiKeyHeader.trim() || null,
    is_default: draft.isDefault,
    clear_api_key: draft.clearApiKey
  };
}
