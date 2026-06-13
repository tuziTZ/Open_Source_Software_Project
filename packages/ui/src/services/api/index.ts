import {
  createProvider,
  cleanStoredContent,
  deleteProvider,
  createFeed,
  createProvider as createProviderClient,
  deleteEntry,
  deleteProvider as deleteProviderClient,
  generateSummary,
  getEntries,
  getEntry,
  getFeeds,
  getProviders as getProvidersClient,
  getTags,
  importOpml,
  IpcError,
  setDefaultProvider as setDefaultProviderClient,
  setEntryReadState,
  setEntryStarState,
  syncAllFeeds,
  testProvider as testProviderClient,
  translateArticle as translateArticleClient,
  updateProvider as updateProviderClient
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

export async function requestTranslation(
  entryId: string,
  targetLang: string
): Promise<components["schemas"]["TranslationResult"]> {
  return mercuryClient.request<
    components["schemas"]["TranslationResult"],
    components["schemas"]["TranslationRequest"]
  >("POST", "/agents/translation", { body: { entry_id: entryId, target_lang: targetLang } });
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

export async function getProviders() {
  return getProvidersClient(mercuryClient);
}

export async function createProvider(body: { name: string; kind?: string; model?: string; base_url?: string; api_key?: string; api_key_header?: string; is_default?: boolean }) {
  return createProviderClient(mercuryClient, body);
}

export async function updateProvider(name: string, body: { kind?: string; model?: string; base_url?: string; api_key?: string; api_key_header?: string; is_default?: boolean }) {
  return updateProviderClient(mercuryClient, name, body);
}

export async function deleteProvider(name: string) {
  return deleteProviderClient(mercuryClient, name);
}

export async function setDefaultProvider(name: string) {
  return setDefaultProviderClient(mercuryClient, name);
}

export async function testProvider(name: string) {
  return testProviderClient(mercuryClient, name);
}

export async function translateArticle(entryId: string, targetLang: string) {
  return translateArticleClient(mercuryClient, { entry_id: entryId, target_lang: targetLang });
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
