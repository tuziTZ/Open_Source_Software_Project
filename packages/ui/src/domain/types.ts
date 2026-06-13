export type LocaleCode = "en" | "zh-Hans";

export type SidebarSection = "feeds" | "tags";
export type FeedScope = "all" | "starred" | `feed:${string}`;
export type TagMatchMode = "any" | "all";
export type ReaderMode = "reader" | "web" | "dual";
export type ReaderToolbarPanel = "tags" | "note" | "theme" | null;
export type ReportKind = "overview" | "provider" | "model" | "agent" | "comparison";
export type LongTaskStatus = "idle" | "queued" | "running" | "success" | "failure" | "cancelled";
export type ProviderKind = "openai_compatible" | "anthropic" | "ollama";

export interface Feed {
  id: string;
  title: string;
  siteUrl: string;
  feedUrl: string;
  unreadCount: number;
  status: LongTaskStatus;
}

export interface Tag {
  id: string;
  name: string;
  aliases: string[];
  usageCount: number;
  unreadCount: number;
}

export interface Entry {
  id: string;
  feedId: string;
  title: string;
  summary: string;
  author: string;
  url: string;
  publishedAt: string;
  isRead: boolean;
  isStarred: boolean;
  tagIds: string[];
  readerHtml: string;
  webPreview: string;
  relatedEntryIds: string[];
  note: string;
  summaryText: string;
  translationHtml?: string;
  translationStatus: LongTaskStatus;
}

export interface DigestTemplate {
  id: string;
  title: string;
  includeSummary: boolean;
  includeNotes: boolean;
  includeTags: boolean;
}

export interface UsageBucket {
  day: string;
  promptTokens: number;
  completionTokens: number;
  requests: number;
  failures: number;
}

export interface UsageReport {
  id: string;
  title: string;
  subtitle: string;
  buckets: UsageBucket[];
  provider: string;
  model: string;
  agent: string;
}

export interface ProviderSummary {
  name: string;
  kind: ProviderKind;
  model: string;
  baseUrl: string | null;
  apiKeyHeader: string | null;
  isDefault: boolean;
  hasApiKey: boolean;
}

export interface ProviderDraft {
  name: string;
  kind: ProviderKind;
  model: string;
  baseUrl: string;
  apiKey: string;
  apiKeyHeader: string;
  isDefault: boolean;
  clearApiKey: boolean;
}

export interface AppState {
  locale: LocaleCode;
  sidebarSection: SidebarSection;
  feedScope: FeedScope;
  selectedTagIds: string[];
  tagMatchMode: TagMatchMode;
  searchText: string;
  searchScope: "currentFeed" | "allFeeds";
  unreadOnly: boolean;
  selectedEntryId: string | null;
  readerMode: ReaderMode;
  activePanel: ReaderToolbarPanel;
  summaryExpanded: boolean;
  summaryHeight: number;
  relatedExpanded: boolean;
  entryPageSize: number;
  multipleDigestMode: boolean;
  multipleDigestEntryIds: string[];
  modal: ModalState;
  feedLoadState: SurfaceState;
  tagLoadState: SurfaceState;
  entryLoadState: SurfaceState;
  shellLoadState: SurfaceState;
  translationNotice: string | null;
  batchNotice: string | null;
  settingsTab: "general" | "reader" | "agents" | "digest";
  reportKind: ReportKind;
  theme: ReaderThemeSettings;
}

export type SurfaceState = "ready" | "loading" | "empty" | "error";

export type ModalState =
  | { type: "none" }
  | { type: "feedEditor"; feedId?: string }
  | { type: "importOpml" }
  | { type: "settings" }
  | { type: "shareDigest"; entryId: string; exportMode: "share" | "single" | "multiple" }
  | { type: "batchTagging" }
  | { type: "tagLibrary" }
  | { type: "usageReport" };

export interface ReaderThemeSettings {
  preset: "classic" | "sepia" | "contrast";
  mode: "auto" | "light" | "dark";
  fontFamily: "system" | "serif" | "mono";
  fontSize: number;
  lineHeight: number;
  contentWidth: number;
}
