import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Columns2,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Gauge,
  Languages,
  Library,
  ListChecks,
  MoreHorizontal,
  Paintbrush,
  Plus,
  Search,
  Settings,
  Share2,
  Star,
  Tags,
  X
} from "lucide-react";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { composeDigest } from "./domain/digest";
import { digestTemplates, usageReports } from "./domain/fixtures";
import {
  filterEntries,
  nextSelectedEntryId,
  scopeTitle,
  visiblePage
} from "./domain/selectors";
import { useAppData } from "./hooks/useAppData";
import { useEntryActions } from "./hooks/useEntryActions";
import { useEntryCleaner } from "./hooks/useEntryCleaner";
import { useFeedActions } from "./hooks/useFeedActions";
import { useSummaryAction } from "./hooks/useSummaryAction";
import type {
  AppState,
  Entry,
  Feed,
  FeedScope,
  LocaleCode,
  ModalState,
  ProviderDraft,
  ProviderKind,
  ProviderSummary,
  ReaderMode,
  ReaderThemeSettings,
  SidebarSection,
  SurfaceState,
  Tag
} from "./domain/types";
import { translate } from "./i18n/messages";
import {
  getApiErrorMessage,
  requestTranslation
} from "./services/api";
import { readStoredBoolean, readStoredNumber, writeStoredBoolean, writeStoredNumber } from "./services/storage";

const maxSidebarTags = 5;
const sidebarWidthKey = "ui.sidebarWidth";
const listWidthKey = "ui.listWidth";
const summaryExpandedKey = "ui.summaryExpanded";
const summaryHeightKey = "ui.summaryHeight";

type DataState = {
  feeds: Feed[];
  entries: Entry[];
  tags: Tag[];
};

type Action =
  | { type: "setLocale"; locale: LocaleCode }
  | { type: "setSidebarSection"; section: SidebarSection }
  | { type: "setFeedScope"; scope: FeedScope }
  | { type: "toggleTag"; tagId: string }
  | { type: "clearTags" }
  | { type: "setTagMatchMode"; mode: AppState["tagMatchMode"] }
  | { type: "setSearchText"; text: string }
  | { type: "setSearchScope"; scope: AppState["searchScope"] }
  | { type: "setUnreadOnly"; unreadOnly: boolean }
  | { type: "selectEntry"; entryId: string | null }
  | { type: "setReaderMode"; mode: ReaderMode }
  | { type: "setActivePanel"; panel: AppState["activePanel"] }
  | { type: "setSummaryExpanded"; expanded: boolean }
  | { type: "setSummaryHeight"; height: number }
  | { type: "setRelatedExpanded"; expanded: boolean }
  | { type: "loadMore" }
  | { type: "setModal"; modal: ModalState }
  | { type: "setMultipleDigestMode"; enabled: boolean }
  | { type: "toggleMultipleDigestEntry"; entryId: string }
  | { type: "setTranslationNotice"; notice: string | null }
  | { type: "setBatchNotice"; notice: string | null }
  | { type: "setSettingsTab"; tab: AppState["settingsTab"] }
  | { type: "setReportKind"; kind: AppState["reportKind"] }
  | { type: "setTheme"; theme: Partial<ReaderThemeSettings> }
  | { type: "setSurfaceState"; surface: "feed" | "tag" | "entry" | "shell"; state: SurfaceState };

const initialState: AppState = {
  locale: "en",
  sidebarSection: "feeds",
  feedScope: "all",
  selectedTagIds: [],
  tagMatchMode: "any",
  searchText: "",
  searchScope: "allFeeds",
  unreadOnly: false,
  selectedEntryId: null,
  readerMode: "reader",
  activePanel: null,
  summaryExpanded: readStoredBoolean(summaryExpandedKey, true),
  summaryHeight: readStoredNumber(summaryHeightKey, 280),
  relatedExpanded: true,
  entryPageSize: 5,
  multipleDigestMode: false,
  multipleDigestEntryIds: [],
  modal: { type: "none" },
  feedLoadState: "ready",
  tagLoadState: "ready",
  entryLoadState: "ready",
  shellLoadState: "ready",
  translationNotice: null,
  batchNotice: null,
  settingsTab: "general",
  reportKind: "overview",
  theme: {
    preset: "classic",
    mode: "auto",
    fontFamily: "serif",
    fontSize: 17,
    lineHeight: 1.65,
    contentWidth: 720
  }
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "setLocale":
      return { ...state, locale: action.locale };
    case "setSidebarSection":
      return {
        ...state,
        sidebarSection: action.section,
        feedScope: action.section === "tags" ? "all" : state.feedScope,
        searchScope: action.section === "tags" ? "allFeeds" : state.searchScope,
        selectedEntryId: null,
        multipleDigestMode: false,
        multipleDigestEntryIds: []
      };
    case "setFeedScope":
      return {
        ...state,
        feedScope: action.scope,
        searchScope: action.scope === "all" ? "allFeeds" : "currentFeed",
        selectedEntryId: null,
        multipleDigestMode: false,
        multipleDigestEntryIds: []
      };
    case "toggleTag": {
      const hasTag = state.selectedTagIds.includes(action.tagId);
      if (!hasTag && state.selectedTagIds.length >= maxSidebarTags) {
        return state;
      }
      return {
        ...state,
        selectedTagIds: hasTag
          ? state.selectedTagIds.filter((tagId) => tagId !== action.tagId)
          : [...state.selectedTagIds, action.tagId],
        selectedEntryId: null,
        multipleDigestMode: false,
        multipleDigestEntryIds: []
      };
    }
    case "clearTags":
      return { ...state, selectedTagIds: [], selectedEntryId: null };
    case "setTagMatchMode":
      return { ...state, tagMatchMode: action.mode, selectedEntryId: null };
    case "setSearchText":
      return {
        ...state,
        searchText: action.text,
        selectedEntryId: null,
        multipleDigestMode: false,
        multipleDigestEntryIds: [],
        entryPageSize: initialState.entryPageSize
      };
    case "setSearchScope":
      return { ...state, searchScope: action.scope, selectedEntryId: null };
    case "setUnreadOnly":
      return {
        ...state,
        unreadOnly: action.unreadOnly,
        selectedEntryId: null,
        multipleDigestMode: false,
        multipleDigestEntryIds: []
      };
    case "selectEntry":
      return { ...state, selectedEntryId: action.entryId, activePanel: null };
    case "setReaderMode":
      return { ...state, readerMode: action.mode };
    case "setActivePanel":
      return { ...state, activePanel: state.activePanel === action.panel ? null : action.panel };
    case "setSummaryExpanded":
      writeStoredBoolean(summaryExpandedKey, action.expanded);
      return { ...state, summaryExpanded: action.expanded };
    case "setSummaryHeight":
      writeStoredNumber(summaryHeightKey, action.height);
      return { ...state, summaryHeight: action.height };
    case "setRelatedExpanded":
      return { ...state, relatedExpanded: action.expanded };
    case "loadMore":
      return { ...state, entryPageSize: state.entryPageSize + 5 };
    case "setModal":
      return { ...state, modal: action.modal };
    case "setMultipleDigestMode":
      return {
        ...state,
        multipleDigestMode: action.enabled,
        multipleDigestEntryIds: action.enabled ? state.multipleDigestEntryIds : []
      };
    case "toggleMultipleDigestEntry": {
      const isSelected = state.multipleDigestEntryIds.includes(action.entryId);
      return {
        ...state,
        multipleDigestEntryIds: isSelected
          ? state.multipleDigestEntryIds.filter((entryId) => entryId !== action.entryId)
          : [...state.multipleDigestEntryIds, action.entryId]
      };
    }
    case "setTranslationNotice":
      return { ...state, translationNotice: action.notice };
    case "setBatchNotice":
      return { ...state, batchNotice: action.notice };
    case "setSettingsTab":
      return { ...state, settingsTab: action.tab };
    case "setReportKind":
      return { ...state, reportKind: action.kind };
    case "setTheme":
      return { ...state, theme: { ...state.theme, ...action.theme } };
    case "setSurfaceState":
      return {
        ...state,
        feedLoadState: action.surface === "feed" ? action.state : state.feedLoadState,
        tagLoadState: action.surface === "tag" ? action.state : state.tagLoadState,
        entryLoadState: action.surface === "entry" ? action.state : state.entryLoadState,
        shellLoadState: action.surface === "shell" ? action.state : state.shellLoadState
      };
    default:
      return state;
  }
}

export function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { data, error, isLoading, reload, setData, updateEntry, refreshEntry } = useAppData();
  const [entryActionError, setEntryActionError] = useState<string | null>(null);
  const {
    status: feedActionStatus,
    errorMessage: feedActionError,
    notice: feedActionNotice,
    addFeed,
    importFeedsFromOpml,
    syncAll,
    clearMessages: clearFeedActionMessages
  } = useFeedActions(reload);
  const { ensureCleaned } = useEntryCleaner(refreshEntry);
  const { status: summaryStatus, errorMessage: summaryError, runSummary, clearError: clearSummaryError } = useSummaryAction(refreshEntry);
  const { setReadState, setReadStateForEntries, toggleStar, deleteOne } = useEntryActions(setData, reload);
  const [sidebarWidth, setSidebarWidth] = useState(() => readStoredNumber(sidebarWidthKey, 252));
  const [listWidth, setListWidth] = useState(() => readStoredNumber(listWidthKey, 360));
  const searchRef = useRef<HTMLInputElement>(null);
  const autoMarkReadTimerRef = useRef<number | null>(null);
  const suppressAutoMarkReadEntryIdRef = useRef<string | null>(null);

  const t = (key: string, values?: Record<string, string | number>) => translate(state.locale, key, values);
  const query = useMemo(
    () => ({
      feedScope: state.feedScope,
      selectedTagIds: state.sidebarSection === "tags" ? state.selectedTagIds : [],
      tagMatchMode: state.tagMatchMode,
      unreadOnly: state.unreadOnly,
      searchText: state.searchText,
      searchScope: state.searchScope
    }),
    [
      state.feedScope,
      state.selectedTagIds,
      state.sidebarSection,
      state.tagMatchMode,
      state.unreadOnly,
      state.searchText,
      state.searchScope
    ]
  );
  const filteredEntries = useMemo(() => filterEntries(data.entries, query), [data.entries, query]);
  const page = useMemo(() => visiblePage(filteredEntries, state.entryPageSize), [filteredEntries, state.entryPageSize]);
  const selectedEntry = data.entries.find((entry) => entry.id === state.selectedEntryId) ?? null;

  useEffect(() => {
    const nextId = nextSelectedEntryId(state.selectedEntryId, filteredEntries, true);
    if (nextId !== state.selectedEntryId) {
      dispatch({ type: "selectEntry", entryId: nextId });
    }
  }, [filteredEntries, state.selectedEntryId]);

  useEffect(() => {
    clearSummaryError();
  }, [clearSummaryError, state.selectedEntryId]);

  useEffect(() => {
    if (autoMarkReadTimerRef.current !== null) {
      window.clearTimeout(autoMarkReadTimerRef.current);
      autoMarkReadTimerRef.current = null;
    }

    if (!selectedEntry) {
      return;
    }
    if (suppressAutoMarkReadEntryIdRef.current && suppressAutoMarkReadEntryIdRef.current !== selectedEntry.id) {
      suppressAutoMarkReadEntryIdRef.current = null;
    }
    if (selectedEntry.isRead || suppressAutoMarkReadEntryIdRef.current === selectedEntry.id) {
      return;
    }

    autoMarkReadTimerRef.current = window.setTimeout(() => {
      void setReadState(selectedEntry, true).catch((loadError: Error) => {
        setEntryActionError(loadError.message);
      });
    }, 3000);

    return () => {
      if (autoMarkReadTimerRef.current !== null) {
        window.clearTimeout(autoMarkReadTimerRef.current);
        autoMarkReadTimerRef.current = null;
      }
    };
  }, [selectedEntry, setReadState]);

  useEffect(() => {
    const shellState: SurfaceState = isLoading ? "loading" : error ? "error" : "ready";
    const feedState: SurfaceState = isLoading ? "loading" : error ? "error" : data.feeds.length === 0 ? "empty" : "ready";
    const tagState: SurfaceState = isLoading ? "loading" : error ? "error" : data.tags.length === 0 ? "empty" : "ready";
    const entryState: SurfaceState = isLoading ? "loading" : error ? "error" : data.entries.length === 0 ? "empty" : "ready";

    dispatch({ type: "setSurfaceState", surface: "shell", state: shellState });
    dispatch({ type: "setSurfaceState", surface: "feed", state: feedState });
    dispatch({ type: "setSurfaceState", surface: "tag", state: tagState });
    dispatch({ type: "setSurfaceState", surface: "entry", state: entryState });
  }, [data.entries.length, data.feeds.length, data.tags.length, error, isLoading]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "f") {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") {
        if (state.modal.type !== "none") {
          dispatch({ type: "setModal", modal: { type: "none" } });
          return;
        }
        if (state.activePanel) {
          dispatch({ type: "setActivePanel", panel: null });
        }
      }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        const index = page.items.findIndex((entry) => entry.id === state.selectedEntryId);
        if (index < 0) {
          return;
        }
        const nextIndex = event.key === "ArrowDown" ? index + 1 : index - 1;
        const nextEntry = page.items[nextIndex];
        if (nextEntry) {
          event.preventDefault();
          dispatch({ type: "selectEntry", entryId: nextEntry.id });
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [page.items, state.activePanel, state.modal.type, state.selectedEntryId]);

  async function markSelectedEntry(isRead: boolean) {
    if (!selectedEntry) {
      return;
    }
    suppressAutoMarkReadEntryIdRef.current = isRead ? null : selectedEntry.id;
    try {
      await setReadState(selectedEntry, isRead);
      setEntryActionError(null);
    } catch (loadError) {
      setEntryActionError(loadError instanceof Error ? loadError.message : t("requestFailed"));
    }
  }

  async function markAllFilteredEntries(isRead: boolean) {
    try {
      await setReadStateForEntries(filteredEntries, isRead);
      setEntryActionError(null);
    } catch (loadError) {
      setEntryActionError(loadError instanceof Error ? loadError.message : t("requestFailed"));
    }
  }

  async function toggleEntryStar(entryId: string) {
    const entry = data.entries.find((candidate) => candidate.id === entryId);
    if (!entry) {
      return;
    }

    try {
      await toggleStar(entry);
      setEntryActionError(null);
    } catch (loadError) {
      setEntryActionError(loadError instanceof Error ? loadError.message : t("requestFailed"));
    }
  }

  async function deleteSelectedEntry() {
    if (!selectedEntry) {
      return;
    }

    const selectedIndex = filteredEntries.findIndex((entry) => entry.id === selectedEntry.id);
    const fallbackEntryId =
      filteredEntries[selectedIndex + 1]?.id ?? filteredEntries[selectedIndex - 1]?.id ?? null;

    try {
      await deleteOne(selectedEntry.id);
      dispatch({ type: "selectEntry", entryId: fallbackEntryId });
      setEntryActionError(null);
    } catch (loadError) {
      setEntryActionError(loadError instanceof Error ? loadError.message : t("requestFailed"));
    }
  }

  function clearStatusMessages() {
    clearFeedActionMessages();
    setEntryActionError(null);
  }

  function openMultipleDigestExport() {
    dispatch({ type: "setModal", modal: { type: "shareDigest", entryId: state.selectedEntryId ?? "", exportMode: "multiple" } });
  }

  function setResize(
    event: React.MouseEvent,
    startValue: number,
    min: number,
    max: number,
    setter: (value: number) => void,
    storageKey: string
  ) {
    event.preventDefault();
    const startX = event.clientX;
    const onMove = (moveEvent: MouseEvent) => {
      const next = Math.min(Math.max(startValue + moveEvent.clientX - startX, min), max);
      setter(next);
      writeStoredNumber(storageKey, next);
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  const selectedForDigest =
    state.modal.type === "shareDigest" && state.modal.exportMode === "multiple"
      ? data.entries.filter((entry) => state.multipleDigestEntryIds.includes(entry.id))
      : selectedEntry
        ? [selectedEntry]
        : [];

  return (
    <div className="app-shell" data-locale={state.locale}>
      <TopToolbar
        t={t}
        locale={state.locale}
        onLocaleChange={(locale) => dispatch({ type: "setLocale", locale })}
        searchText={state.searchText}
        searchRef={searchRef}
        searchScope={state.searchScope}
        feedScope={state.feedScope}
        onSearchText={(text) => dispatch({ type: "setSearchText", text })}
        onSearchScope={(scope) => dispatch({ type: "setSearchScope", scope })}
        onSettings={() => dispatch({ type: "setModal", modal: { type: "settings" } })}
        onReports={() => dispatch({ type: "setModal", modal: { type: "usageReport" } })}
      />

      {(feedActionNotice || feedActionError || entryActionError) && (
        <div className="status-note">
          <span>{entryActionError ?? feedActionError ?? feedActionNotice}</span>
          <button type="button" onClick={clearStatusMessages}>
            <X size={14} aria-hidden />
          </button>
        </div>
      )}

      <main className="reader-workspace" aria-busy={state.shellLoadState === "loading"}>
        <aside className="pane sidebar-pane" style={{ width: sidebarWidth }}>
          <Sidebar
            t={t}
            feeds={data.feeds}
            entries={data.entries}
            tags={data.tags}
            state={state}
            onSection={(section) => dispatch({ type: "setSidebarSection", section })}
            onFeedScope={(scope) => dispatch({ type: "setFeedScope", scope })}
            onToggleTag={(tagId) => dispatch({ type: "toggleTag", tagId })}
            onClearTags={() => dispatch({ type: "clearTags" })}
            onTagMatchMode={(mode) => dispatch({ type: "setTagMatchMode", mode })}
            onModal={(modal) => dispatch({ type: "setModal", modal })}
            onSync={syncAll}
          />
        </aside>
        <div
          className="resize-grip"
          role="separator"
          aria-orientation="vertical"
          onMouseDown={(event) => setResize(event, sidebarWidth, 220, 360, setSidebarWidth, sidebarWidthKey)}
        />
        <section className="pane entry-pane" style={{ width: listWidth }}>
          <EntryList
            t={t}
            feeds={data.feeds}
            state={state}
            entries={page.items}
            selectedEntry={selectedEntry}
            hasMore={page.hasMore}
            totalFiltered={filteredEntries.length}
            onUnreadOnly={(unreadOnly) => dispatch({ type: "setUnreadOnly", unreadOnly })}
            onSelect={(entryId) => dispatch({ type: "selectEntry", entryId })}
            onLoadMore={() => dispatch({ type: "loadMore" })}
            onMarkSelectedRead={() => void markSelectedEntry(true)}
            onMarkSelectedUnread={() => void markSelectedEntry(false)}
            onMarkAllRead={() => void markAllFilteredEntries(true)}
            onMarkAllUnread={() => void markAllFilteredEntries(false)}
            onToggleStar={(entryId) => void toggleEntryStar(entryId)}
            onDeleteSelected={() => void deleteSelectedEntry()}
            onMultipleMode={(enabled) => dispatch({ type: "setMultipleDigestMode", enabled })}
            onToggleMultiple={(entryId) => dispatch({ type: "toggleMultipleDigestEntry", entryId })}
            onConfirmMultiple={openMultipleDigestExport}
          />
        </section>
        <div
          className="resize-grip"
          role="separator"
          aria-orientation="vertical"
          onMouseDown={(event) => setResize(event, listWidth, 300, 520, setListWidth, listWidthKey)}
        />
        <section className="pane reader-pane">
          <ReaderDetail
            t={t}
            state={state}
            entry={selectedEntry}
            entries={data.entries}
            tags={data.tags}
            onMode={(mode) => dispatch({ type: "setReaderMode", mode })}
            onPanel={(panel) => dispatch({ type: "setActivePanel", panel })}
            onSelectEntry={(entryId) => dispatch({ type: "selectEntry", entryId })}
            onUpdateEntry={updateEntry}
            onTheme={(theme) => dispatch({ type: "setTheme", theme })}
            onSummaryExpanded={(expanded) => dispatch({ type: "setSummaryExpanded", expanded })}
            onSummaryHeight={(height) => dispatch({ type: "setSummaryHeight", height })}
            onRelatedExpanded={(expanded) => dispatch({ type: "setRelatedExpanded", expanded })}
            onNotice={(notice) => dispatch({ type: "setTranslationNotice", notice })}
            onModal={(modal) => dispatch({ type: "setModal", modal })}
            onRunSummary={runSummary}
            onEnsureEntryContent={ensureCleaned}
            summaryStatus={summaryStatus}
            summaryError={summaryError}
            onClearSummaryError={clearSummaryError}
          />
        </section>
      </main>

      <ModalHost
        t={t}
        state={state}
        entries={data.entries}
        tags={data.tags}
        digestEntries={selectedForDigest}
        onClose={() => dispatch({ type: "setModal", modal: { type: "none" } })}
        onLocale={(locale) => dispatch({ type: "setLocale", locale })}
        onSettingsTab={(tab) => dispatch({ type: "setSettingsTab", tab })}
        onReportKind={(kind) => dispatch({ type: "setReportKind", kind })}
        onModal={(modal) => dispatch({ type: "setModal", modal })}
        onBatchNotice={(notice) => dispatch({ type: "setBatchNotice", notice })}
        onSetTags={(tags) => setData((current) => ({ ...current, tags }))}
        feedActionStatus={feedActionStatus}
        feedActionError={feedActionError}
        onAddFeed={addFeed}
        onImportOpml={importFeedsFromOpml}
      />
    </div>
  );
}

function TopToolbar(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  locale: LocaleCode;
  searchText: string;
  searchRef: React.RefObject<HTMLInputElement | null>;
  searchScope: AppState["searchScope"];
  feedScope: FeedScope;
  onLocaleChange: (locale: LocaleCode) => void;
  onSearchText: (text: string) => void;
  onSearchScope: (scope: AppState["searchScope"]) => void;
  onSettings: () => void;
  onReports: () => void;
}) {
  const { t } = props;
  return (
    <header className="top-toolbar">
      <div className="brand">
        <BookOpen size={18} aria-hidden />
        <span>{t("appTitle")}</span>
      </div>
      <label className="search-box">
        <Search size={15} aria-hidden />
        <input
          ref={props.searchRef}
          value={props.searchText}
          onChange={(event) => props.onSearchText(event.target.value)}
          placeholder={t("searchEntries")}
          aria-label={t("searchEntries")}
        />
      </label>
      <select
        className="compact-select"
        value={props.searchScope}
        onChange={(event) => props.onSearchScope(event.target.value as AppState["searchScope"])}
        disabled={props.feedScope === "all"}
        aria-label={t("searchEntries")}
      >
        <option value="currentFeed">{t("searchScopeCurrent")}</option>
        <option value="allFeeds">{t("searchScopeAll")}</option>
      </select>
      <div className="toolbar-spacer" />
      <select
        className="compact-select"
        value={props.locale}
        onChange={(event) => props.onLocaleChange(event.target.value as LocaleCode)}
        aria-label={t("language")}
      >
        <option value="en">English</option>
        <option value="zh-Hans">简体中文</option>
      </select>
      <button className="icon-button" type="button" onClick={props.onReports} title={t("usageReports")}>
        <Gauge size={17} aria-hidden />
      </button>
      <button className="icon-button" type="button" onClick={props.onSettings} title={t("settings")}>
        <Settings size={17} aria-hidden />
      </button>
    </header>
  );
}

function Sidebar(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  feeds: Feed[];
  entries: Entry[];
  tags: Tag[];
  state: AppState;
  onSection: (section: SidebarSection) => void;
  onFeedScope: (scope: FeedScope) => void;
  onToggleTag: (tagId: string) => void;
  onClearTags: () => void;
  onTagMatchMode: (mode: AppState["tagMatchMode"]) => void;
  onModal: (modal: ModalState) => void;
  onSync: () => Promise<unknown>;
}) {
  const [tagSearch, setTagSearch] = useState("");
  const { t, state } = props;
  const visibleTags = props.tags.filter((tag) => {
    const search = tagSearch.trim().toLocaleLowerCase();
    return search.length === 0 || tag.name.toLocaleLowerCase().includes(search) || tag.aliases.join(" ").includes(search);
  });

  return (
    <div className="sidebar">
      <div className="segmented">
        <button
          type="button"
          className={state.sidebarSection === "feeds" ? "active" : ""}
          onClick={() => props.onSection("feeds")}
        >
          {t("feeds")}
        </button>
        <button
          type="button"
          className={state.sidebarSection === "tags" ? "active" : ""}
          onClick={() => props.onSection("tags")}
        >
          {t("tags")}
        </button>
      </div>

      {state.sidebarSection === "feeds" ? (
        <>
          <div className="pane-header">
            <h2>{t("feeds")}</h2>
            <MenuButton
              label={t("addFeed")}
              icon={<Plus size={16} aria-hidden />}
              items={[
                { label: t("addFeed"), action: () => props.onModal({ type: "feedEditor" }) },
                { label: t("importOpml"), action: () => props.onModal({ type: "importOpml" }) }
              ]}
            />
            <MenuButton
              label={t("feeds")}
              items={[
                { label: t("syncNow"), action: () => void props.onSync().catch(() => undefined) },
                { label: t("exportOpml"), action: () => undefined, disabled: true }
              ]}
            />
          </div>
          <nav className="sidebar-list" aria-label={t("feeds")}>
            <SidebarRow
              active={state.feedScope === "all"}
              title={t("allFeeds")}
              icon={<Library size={15} aria-hidden />}
              badge={props.feeds.reduce((sum, feed) => sum + feed.unreadCount, 0)}
              onClick={() => props.onFeedScope("all")}
            />
            <SidebarRow
              active={state.feedScope === "starred"}
              title={t("starred")}
              icon={<Star size={15} aria-hidden />}
              badge={props.entries.filter((entry) => entry.isStarred && !entry.isRead).length}
              onClick={() => props.onFeedScope("starred")}
            />
            {props.feeds.map((feed) => (
              <SidebarRow
                key={feed.id}
                active={state.feedScope === `feed:${feed.id}`}
                title={feed.title}
                badge={feed.unreadCount}
                status={feed.status}
                onClick={() => props.onFeedScope(`feed:${feed.id}`)}
              />
            ))}
          </nav>
        </>
      ) : (
        <>
          <div className="pane-header">
            <h2>{t("tags")}</h2>
            {state.selectedTagIds.length > 0 && (
              <button className="icon-button" type="button" onClick={props.onClearTags} title={t("clear")}>
                <X size={15} aria-hidden />
              </button>
            )}
          </div>
          <label className="field">
            <Search size={14} aria-hidden />
            <input value={tagSearch} onChange={(event) => setTagSearch(event.target.value)} placeholder={t("searchTags")} />
          </label>
          <div className="segmented compact">
            <button
              type="button"
              className={state.tagMatchMode === "any" ? "active" : ""}
              onClick={() => props.onTagMatchMode("any")}
            >
              {t("any")}
            </button>
            <button
              type="button"
              className={state.tagMatchMode === "all" ? "active" : ""}
              onClick={() => props.onTagMatchMode("all")}
            >
              {t("all")}
            </button>
          </div>
          <div className="sidebar-list">
            {visibleTags.length === 0 ? (
              <div className="empty-state small">{t("noTags")}</div>
            ) : (
              visibleTags.map((tag) => (
                <button
                  key={tag.id}
                  type="button"
                  className={`tag-row ${state.selectedTagIds.includes(tag.id) ? "active" : ""}`}
                  disabled={!state.selectedTagIds.includes(tag.id) && state.selectedTagIds.length >= maxSidebarTags}
                  onClick={() => props.onToggleTag(tag.id)}
                >
                  <span>{state.selectedTagIds.includes(tag.id) ? <CheckCircle2 size={15} /> : <span className="checkbox-dot" />}</span>
                  <span className="truncate">{tag.name}</span>
                  <span className="muted">({tag.usageCount})</span>
                  {tag.unreadCount > 0 && <span className="badge">{tag.unreadCount}</span>}
                </button>
              ))
            )}
          </div>
          <div className="sidebar-actions">
            <span className="muted">{t("selectedCount", { count: state.selectedTagIds.length, max: maxSidebarTags })}</span>
            <button type="button" onClick={() => props.onModal({ type: "tagLibrary" })}>
              <Tags size={15} aria-hidden />
              {t("tagLibrary")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function SidebarRow(props: {
  active: boolean;
  title: string;
  badge?: number;
  icon?: React.ReactNode;
  status?: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className={`sidebar-row ${props.active ? "active" : ""}`} onClick={props.onClick}>
      {props.icon ?? <span className="feed-dot" />}
      <span className="truncate">{props.title}</span>
      {props.status === "running" && <span className="status-dot running" />}
      {props.badge ? <span className="badge">{props.badge}</span> : null}
    </button>
  );
}

function EntryList(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  feeds: Feed[];
  state: AppState;
  entries: Entry[];
  selectedEntry: Entry | null;
  hasMore: boolean;
  totalFiltered: number;
  onUnreadOnly: (unreadOnly: boolean) => void;
  onSelect: (entryId: string) => void;
  onLoadMore: () => void;
  onMarkSelectedRead: () => void;
  onMarkSelectedUnread: () => void;
  onMarkAllRead: () => void;
  onMarkAllUnread: () => void;
  onToggleStar: (entryId: string) => void;
  onDeleteSelected: () => void;
  onMultipleMode: (enabled: boolean) => void;
  onToggleMultiple: (entryId: string) => void;
  onConfirmMultiple: () => void;
}) {
  const { t, state } = props;
  const title = scopeTitle(state.feedScope, props.feeds);
  const headerTitle = title === "all" ? t("entries") : title === "starred" ? t("starred") : title;
  const feedById = new Map(props.feeds.map((feed) => [feed.id, feed.title]));

  return (
    <div className="entry-list">
      <div className="entry-header">
        {state.multipleDigestMode ? (
          <>
            <button type="button" onClick={() => props.onMultipleMode(false)}>
              {t("cancel")}
            </button>
            <span className="muted">{t("selectedEntries", { count: state.multipleDigestEntryIds.length })}</span>
            <div className="toolbar-spacer" />
            <button type="button" disabled={state.multipleDigestEntryIds.length === 0} onClick={props.onConfirmMultiple}>
              {t("continue")}
            </button>
          </>
        ) : (
          <>
            <h2>{headerTitle}</h2>
            <span className="muted">{props.totalFiltered}</span>
            <div className="toolbar-spacer" />
            <button type="button" className={state.unreadOnly ? "toggle active" : "toggle"} onClick={() => props.onUnreadOnly(!state.unreadOnly)}>
              <ListChecks size={15} aria-hidden />
              {t("unread")}
            </button>
            <MenuButton
              label={t("entries")}
              items={[
                { label: t("delete"), action: props.onDeleteSelected, disabled: !props.selectedEntry, destructive: true },
                { label: t("markRead"), action: props.onMarkSelectedRead, disabled: !props.selectedEntry || props.selectedEntry.isRead },
                { label: t("markUnread"), action: props.onMarkSelectedUnread, disabled: !props.selectedEntry || !props.selectedEntry.isRead },
                { label: t("markAllRead"), action: props.onMarkAllRead },
                { label: t("markAllUnread"), action: props.onMarkAllUnread },
                { label: t("exportMultipleDigest"), action: () => props.onMultipleMode(true) }
              ]}
            />
          </>
        )}
      </div>
      <div className="entry-scroll">
        {state.entryLoadState === "loading" && <div className="empty-state">{t("loading")}</div>}
        {state.entryLoadState === "error" && <div className="empty-state">{t("errorEntries")}</div>}
        {props.entries.length === 0 && (state.entryLoadState === "ready" || state.entryLoadState === "empty") && (
          <div className="empty-state">{t("emptyEntries")}</div>
        )}
        {props.entries.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className={`entry-row ${props.selectedEntry?.id === entry.id ? "active" : ""}`}
            onClick={() => (state.multipleDigestMode ? props.onToggleMultiple(entry.id) : props.onSelect(entry.id))}
          >
            {state.multipleDigestMode && (
              <span className="multi-check">
                {state.multipleDigestEntryIds.includes(entry.id) ? <CheckCircle2 size={16} /> : <span className="checkbox-dot" />}
              </span>
            )}
            <span className={`unread-dot ${entry.isRead ? "read" : ""}`} />
            <span className="entry-row-main">
              <span className={`entry-title ${entry.isRead ? "read" : ""}`}>{entry.title}</span>
              {state.feedScope === "all" && <span className="entry-source">{feedById.get(entry.feedId)}</span>}
              <span className="entry-meta">
                {formatDate(entry.publishedAt)}
                <button
                  type="button"
                  className="star-button"
                  onClick={(event) => {
                    event.stopPropagation();
                    props.onToggleStar(entry.id);
                  }}
                  aria-label={t("starred")}
                >
                  <Star size={14} fill={entry.isStarred ? "currentColor" : "none"} />
                </button>
              </span>
            </span>
          </button>
        ))}
        <div className="list-footer">
          {props.hasMore ? (
            <button type="button" onClick={props.onLoadMore}>
              {t("loadMore")}
            </button>
          ) : (
            <span className="muted">{t("endOfList")}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function ReaderDetail(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  state: AppState;
  entry: Entry | null;
  entries: Entry[];
  tags: Tag[];
  onMode: (mode: ReaderMode) => void;
  onPanel: (panel: AppState["activePanel"]) => void;
  onSelectEntry: (entryId: string) => void;
  onUpdateEntry: (entryId: string, transform: (entry: Entry) => Entry) => void;
  onTheme: (theme: Partial<ReaderThemeSettings>) => void;
  onSummaryExpanded: (expanded: boolean) => void;
  onSummaryHeight: (height: number) => void;
  onRelatedExpanded: (expanded: boolean) => void;
  onNotice: (notice: string | null) => void;
  onModal: (modal: ModalState) => void;
  onRunSummary: (entryId: string) => Promise<void>;
  onEnsureEntryContent: (entryId: string) => Promise<void>;
  summaryStatus: "idle" | "running" | "error";
  summaryError: string | null;
  onClearSummaryError: () => void;
}) {
  const { t, state, entry } = props;
  const tags = entry ? props.tags.filter((tag) => entry.tagIds.includes(tag.id)) : [];
  const related = entry ? entry.relatedEntryIds.map((id) => props.entries.find((candidate) => candidate.id === id)).filter(Boolean) as Entry[] : [];
  const showReader = state.readerMode !== "web";
  const showWeb = state.readerMode !== "reader";
  const [translationMode, setTranslationMode] = useState<"original" | "translation">("original");
  const [noteDirty, setNoteDirty] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);

  useEffect(() => {
    setTranslationMode("original");
    setNoteDirty(false);
  }, [entry?.id]);

  useEffect(() => {
    if (!entry?.readerHtml.trim()) {
      return;
    }
    void props.onEnsureEntryContent(entry.id);
  }, [entry?.id, entry?.readerHtml, props.onEnsureEntryContent]);

  if (!entry) {
    return (
      <div className="reader-empty">
        <FileText size={28} aria-hidden />
        <p>{t("selectEntry")}</p>
      </div>
    );
  }

  const articleHtml = translationMode === "translation" && entry.translationHtml
    ? renderBilingualMarkdown(entry.translationHtml)
    : entry.readerHtml;
  const webHtml = entry.webPreview.trim().startsWith("<") ? entry.webPreview : articleHtml;

  async function toggleTranslation() {
    if (!entry) {
      return;
    }
    if (state.readerMode === "web") {
      props.onNotice(t("translationReaderOnly"));
      return;
    }

    // Reader mode: real backend translation with side-by-side original/translation.
    if (state.readerMode === "reader") {
      if (translationMode === "translation") {
        setTranslationMode("original");
        return;
      }
      setTranslationMode("translation");
      if (entry.translationHtml) {
        return;
      }
      if (isTranslating) {
        return;
      }
      const entryId = entry.id;
      const targetLang = detectTargetLang(entry.readerHtml);
      setIsTranslating(true);
      props.onUpdateEntry(entryId, (current) => ({ ...current, translationStatus: "running" }));
      try {
        const result = await requestTranslation(entryId, targetLang);
        if (result.status === "success" && result.translation_html.trim()) {
          props.onUpdateEntry(entryId, (current) => ({
            ...current,
            translationStatus: "success",
            translationHtml: result.translation_html
          }));
        } else {
          props.onUpdateEntry(entryId, (current) => ({ ...current, translationStatus: "failure" }));
          props.onNotice(t("translationFailed"));
          setTranslationMode("original");
        }
      } catch (error) {
        props.onUpdateEntry(entryId, (current) => ({ ...current, translationStatus: "failure" }));
        props.onNotice(getApiErrorMessage(error));
        setTranslationMode("original");
      } finally {
        setIsTranslating(false);
      }
      return;
    }

    // Dual mode: preserve existing mock preview behavior unchanged.
    if (translationMode === "original") {
      setTranslationMode("translation");
      // 如果已有翻译，直接显示
      if (entry.translationHtml) {
        props.onUpdateEntry(entry.id, (current) => ({ ...current, translationStatus: "success" }));
        return;
      }
      // 否则调用翻译 API
      props.onUpdateEntry(entry.id, (current) => ({ ...current, translationStatus: "running" }));
      import("./services/api").then(({ translateArticle }) => {
        translateArticle(entry.id, detectTargetLang(entry.readerHtml))
          .then((result) => {
            props.onUpdateEntry(entry.id, (current) => ({
              ...current,
              translationHtml: result.translation_html,
              translationStatus: result.status === "success" ? "success" : "failure"
            }));
          })
          .catch(() => {
            props.onUpdateEntry(entry.id, (current) => ({ ...current, translationStatus: "failure" }));
          });
      });
      return;
    }
    setTranslationMode("original");
  }

  return (
    <div className="reader-detail">
      <div className="reader-toolbar">
        <div className="segmented mode-switch">
          {(["reader", "web", "dual"] as ReaderMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={state.readerMode === mode ? "active" : ""}
              onClick={() => props.onMode(mode)}
              title={t(mode)}
              aria-label={t(mode)}
            >
              {mode === "reader" && <BookOpen size={16} aria-hidden />}
              {mode === "web" && <ExternalLink size={16} aria-hidden />}
              {mode === "dual" && <Columns2 size={16} aria-hidden />}
            </button>
          ))}
        </div>
        <button
          className="icon-button"
          type="button"
          disabled={isTranslating}
          onClick={() => void toggleTranslation()}
          title={isTranslating ? t("translatingButton") : translationMode === "original" ? t("switchToTranslation") : t("returnToOriginal")}
          aria-label={isTranslating ? t("translatingButton") : translationMode === "original" ? t("switchToTranslation") : t("returnToOriginal")}
        >
          <Languages size={17} aria-hidden className={isTranslating ? "spin" : undefined} />
        </button>
        <button
          className="icon-button"
          type="button"
          disabled={!entry.translationHtml}
          onClick={() => {
            setTranslationMode("original");
            props.onUpdateEntry(entry.id, (current) => ({ ...current, translationHtml: undefined, translationStatus: "idle" }));
          }}
          title={t("clearTranslation")}
        >
          <X size={17} aria-hidden />
        </button>
        <button className="icon-button" type="button" onClick={() => props.onPanel("tags")} title={t("tagsPanel")}>
          <Tags size={17} aria-hidden />
        </button>
        <button className="icon-button with-badge" type="button" onClick={() => props.onPanel("note")} title={t("notePanel")}>
          <FileText size={17} aria-hidden />
          {entry.note && <span />}
        </button>
        <button className="icon-button" type="button" onClick={() => props.onPanel("theme")} title={t("themePanel")}>
          <Paintbrush size={17} aria-hidden />
        </button>
        <MenuButton
          label={t("share")}
          icon={<Share2 size={17} aria-hidden />}
          items={[
            { label: t("copyLink"), action: () => void navigator.clipboard?.writeText(entry.url) },
            { label: t("openBrowser"), action: () => window.open(entry.url, "_blank", "noopener") },
            { label: t("shareDigest"), action: () => props.onModal({ type: "shareDigest", entryId: entry.id, exportMode: "share" }) },
            { label: t("exportDigest"), action: () => props.onModal({ type: "shareDigest", entryId: entry.id, exportMode: "single" }) }
          ]}
        />
      </div>
      {state.translationNotice && (
        <div className="status-note status-note-reader">
          <span>{state.translationNotice}</span>
          <button type="button" onClick={() => props.onNotice(null)}>
            <X size={14} aria-hidden />
          </button>
        </div>
      )}
      <div className="article-header">
        <div className="article-header-main">
          <h1>{entry.title}</h1>
          <p>
            {entry.author} · {formatDate(entry.publishedAt)}
          </p>
        </div>
        {tags.length > 0 && (
          <div className="tag-chip-list">
            {tags.map((tag) => (
              <span key={tag.id} className="tag-chip">
                {tag.name}
              </span>
            ))}
          </div>
        )}
        {related.length > 0 && (
          <button className="icon-button" type="button" onClick={() => props.onRelatedExpanded(!state.relatedExpanded)} title={state.relatedExpanded ? t("hideRelated") : t("showRelated")}>
            {state.relatedExpanded ? <ChevronUp size={17} /> : <ChevronDown size={17} />}
          </button>
        )}
      </div>
      {related.length > 0 && state.relatedExpanded && (
        <div className="related-strip" aria-label={t("relatedContent")}>
          {related.map((relatedEntry) => (
            <button key={relatedEntry.id} type="button" onClick={() => props.onSelectEntry(relatedEntry.id)}>
              <span>{relatedEntry.title}</span>
              <small>{formatDate(relatedEntry.publishedAt)}</small>
            </button>
          ))}
        </div>
      )}
      <div className={`reader-surface mode-${state.readerMode}`}>
        {showReader && (
          <article
            className={`reader-article theme-${state.theme.preset} font-${state.theme.fontFamily}`}
            style={{
              fontSize: state.theme.fontSize,
              lineHeight: state.theme.lineHeight,
              maxWidth: state.readerMode === "dual" ? "none" : state.theme.contentWidth
            }}
            dangerouslySetInnerHTML={{ __html: articleHtml }}
          />
        )}
        {showWeb && (
          <div className="web-pane">
            <div className="web-url-bar">
              <button type="button" className="icon-button" onClick={() => void navigator.clipboard?.writeText(entry.url)} title={t("copyUrl")}>
                <Copy size={15} aria-hidden />
              </button>
              <span>{entry.url}</span>
            </div>
            <article
              className={`web-preview-article theme-${state.theme.preset} font-${state.theme.fontFamily}`}
              style={{
                fontSize: state.theme.fontSize,
                lineHeight: state.theme.lineHeight
              }}
              dangerouslySetInnerHTML={{ __html: webHtml }}
            />
          </div>
        )}
      </div>
      {state.activePanel && (
        <FloatingPanel title={t(`${state.activePanel}Panel`)} onClose={() => props.onPanel(null)}>
          {state.activePanel === "tags" && (
            <TagsPanel t={t} entry={entry} tags={props.tags} onUpdateEntry={props.onUpdateEntry} />
          )}
          {state.activePanel === "note" && (
            <NotePanel
              t={t}
              entry={entry}
              dirty={noteDirty}
              onDirty={setNoteDirty}
              onUpdate={(note) => {
                setNoteDirty(false);
                props.onUpdateEntry(entry.id, (current) => ({ ...current, note }));
              }}
            />
          )}
          {state.activePanel === "theme" && <ThemePanel t={t} theme={state.theme} onTheme={props.onTheme} />}
        </FloatingPanel>
      )}
      <SummaryPanel
        t={t}
        entry={entry}
        expanded={state.summaryExpanded}
        height={state.summaryHeight}
        onExpanded={props.onSummaryExpanded}
        onHeight={props.onSummaryHeight}
        onUpdateEntry={props.onUpdateEntry}
        onRunSummary={props.onRunSummary}
        summaryStatus={props.summaryStatus}
        summaryError={props.summaryError}
        onClearSummaryError={props.onClearSummaryError}
      />
    </div>
  );
}

function FloatingPanel(props: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <aside className="floating-panel" role="dialog" aria-label={props.title}>
      <div className="floating-panel-header">
        <h3>{props.title}</h3>
        <button className="icon-button" type="button" onClick={props.onClose}>
          <X size={15} aria-hidden />
        </button>
      </div>
      {props.children}
    </aside>
  );
}

function TagsPanel(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  entry: Entry;
  tags: Tag[];
  onUpdateEntry: (entryId: string, transform: (entry: Entry) => Entry) => void;
}) {
  const suggestions = props.tags.filter((tag) => !props.entry.tagIds.includes(tag.id)).slice(0, 4);
  return (
    <div className="panel-body">
      <h4>{props.t("currentTags")}</h4>
      <div className="tag-chip-list wrap">
        {props.entry.tagIds.map((tagId) => {
          const tag = props.tags.find((candidate) => candidate.id === tagId);
          return (
            <button
              key={tagId}
              type="button"
              className="tag-chip removable"
              onClick={() => props.onUpdateEntry(props.entry.id, (entry) => ({ ...entry, tagIds: entry.tagIds.filter((id) => id !== tagId) }))}
            >
              {tag?.name ?? tagId}
              <X size={12} aria-hidden />
            </button>
          );
        })}
      </div>
      <h4>{props.t("suggestions")}</h4>
      <div className="suggestion-list">
        {suggestions.map((tag) => (
          <button
            key={tag.id}
            type="button"
            onClick={() => props.onUpdateEntry(props.entry.id, (entry) => ({ ...entry, tagIds: [...entry.tagIds, tag.id] }))}
          >
            <Plus size={14} aria-hidden />
            {tag.name}
          </button>
        ))}
      </div>
    </div>
  );
}

function NotePanel(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  entry: Entry;
  dirty: boolean;
  onDirty: (dirty: boolean) => void;
  onUpdate: (note: string) => void;
}) {
  const [draft, setDraft] = useState(props.entry.note);
  useEffect(() => setDraft(props.entry.note), [props.entry.id, props.entry.note]);
  useEffect(() => {
    if (!props.dirty) {
      return;
    }
    const id = window.setTimeout(() => props.onUpdate(draft), 700);
    return () => window.clearTimeout(id);
  }, [draft, props.dirty]);

  return (
    <div className="panel-body">
      <textarea
        value={draft}
        onChange={(event) => {
          setDraft(event.target.value);
          props.onDirty(true);
        }}
        placeholder={props.t("notePlaceholder")}
      />
      <div className="panel-status">{props.dirty ? props.t("noteStatusDirty") : props.t("noteStatusSaved")}</div>
    </div>
  );
}

function ThemePanel(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  theme: ReaderThemeSettings;
  onTheme: (theme: Partial<ReaderThemeSettings>) => void;
}) {
  return (
    <div className="panel-body">
      <h4>{props.t("quickThemes")}</h4>
      <div className="segmented">
        {(["classic", "sepia", "contrast"] as const).map((preset) => (
          <button key={preset} type="button" className={props.theme.preset === preset ? "active" : ""} onClick={() => props.onTheme({ preset })}>
            {props.t(preset)}
          </button>
        ))}
      </div>
      <label>
        {props.t("fontFamily")}
        <select value={props.theme.fontFamily} onChange={(event) => props.onTheme({ fontFamily: event.target.value as ReaderThemeSettings["fontFamily"] })}>
          <option value="system">{props.t("systemFont")}</option>
          <option value="serif">{props.t("serifFont")}</option>
          <option value="mono">{props.t("monoFont")}</option>
        </select>
      </label>
      <Slider label={props.t("fontSize")} value={props.theme.fontSize} min={14} max={24} step={1} onChange={(fontSize) => props.onTheme({ fontSize })} />
      <Slider label={props.t("lineHeight")} value={props.theme.lineHeight} min={1.3} max={2} step={0.05} onChange={(lineHeight) => props.onTheme({ lineHeight })} />
      <Slider label={props.t("contentWidth")} value={props.theme.contentWidth} min={560} max={920} step={20} onChange={(contentWidth) => props.onTheme({ contentWidth })} />
      <p className="theme-preview">{props.t("previewSentence")}</p>
    </div>
  );
}

function renderSimpleMarkdown(text: string): string {
  // 保存双语标记，避免被转义
  const bilingualMarkers: string[] = [];
  let html = text.replace(/<div class="bilingual-(original|translation)">([\s\S]*?)<\/div>/g, (match) => {
    const index = bilingualMarkers.length;
    bilingualMarkers.push(match);
    return `__BILINGUAL_${index}__`;
  });

  // 清理文本
  html = html
    // 移除图片链接 ![alt](url) -> [图片]
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "[图片]")
    // 简化链接 [text](url) -> text
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    // 移除其他 HTML 标签
    .replace(/<[^>]+>/g, "")
    // 移除 URL 链接（单独一行的）
    .replace(/^https?:\/\/\S+$/gm, "")
    // Escape HTML 特殊字符
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 代码块: ```code```
  html = html.replace(/```[\s\S]*?```/g, (match) => {
    const code = match.replace(/```\w*\n?/g, "").replace(/```$/g, "");
    return `<pre><code>${code}</code></pre>`;
  });

  // Headers: ### h3, ## h2, # h1
  html = html.replace(/^#### (.+)$/gm, "<h5>$1</h5>");
  html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");

  // Bold: **text**
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic: *text*
  html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");

  // Inline code: `code`
  html = html.replace(/`(.+?)`/g, "<code>$1</code>");

  // Blockquote: > text
  html = html.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");

  // Horizontal rule: --- or ***
  html = html.replace(/^[-*]{3,}$/gm, "<hr>");

  // Unordered list: - item or * item
  html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");

  // Ordered list: 1. item
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

  // 合并连续的 li 为 ul
  html = html.replace(/((?:<li>.*<\/li>\s*)+)/g, "<ul>$1</ul>");

  // 段落处理：双换行 = 新段落
  html = html.replace(/\n\n+/g, "</p><p>");
  // 单换行 = <br>
  html = html.replace(/\n/g, "<br>");
  html = "<p>" + html + "</p>";

  // 清理空段落和嵌套问题
  html = html.replace(/<p>\s*<\/p>/g, "");
  html = html.replace(/<p>(<h[2-5]>)/g, "$1");
  html = html.replace(/(<\/h[2-5]>)<\/p>/g, "$1");
  html = html.replace(/<p>(<ul>)/g, "$1");
  html = html.replace(/(<\/ul>)<\/p>/g, "$1");
  html = html.replace(/<p>(<blockquote>)/g, "$1");
  html = html.replace(/(<\/blockquote>)<\/p>/g, "$1");
  html = html.replace(/<p>(<pre>)/g, "$1");
  html = html.replace(/(<\/pre>)<\/p>/g, "$1");
  html = html.replace(/<p>(<hr>)/g, "$1");
  html = html.replace(/(<hr>)<\/p>/g, "$1");
  // 清理连续的 br
  html = html.replace(/(<br>\s*){3,}/g, "<br><br>");
  // 清理 [图片] 周围的多余标记
  html = html.replace(/\[图片\]/g, '<span style="color: var(--color-muted); font-style: italic;">[图片]</span>');

  // 恢复双语标记
  html = html.replace(/__BILINGUAL_(\d+)__/g, (_, index) => {
    return bilingualMarkers[parseInt(index)];
  });

  return html;
}

function SummaryPanel(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  entry: Entry;
  expanded: boolean;
  height: number;
  onExpanded: (expanded: boolean) => void;
  onHeight: (height: number) => void;
  onUpdateEntry: (entryId: string, transform: (entry: Entry) => Entry) => void;
  onRunSummary: (entryId: string) => Promise<void>;
  summaryStatus: "idle" | "running" | "error";
  summaryError: string | null;
  onClearSummaryError: () => void;
}) {
  async function runSummary() {
    await props.onRunSummary(props.entry.id);
  }

  return (
    <section className="summary-panel" style={{ height: props.expanded ? props.height : 44 }}>
      {props.expanded && (
        <div
          className="horizontal-resize"
          role="separator"
          aria-orientation="horizontal"
          onMouseDown={(event) => {
            event.preventDefault();
            const startY = event.clientY;
            const start = props.height;
            const onMove = (moveEvent: MouseEvent) => props.onHeight(Math.min(Math.max(start - (moveEvent.clientY - startY), 220), 520));
            const onUp = () => {
              window.removeEventListener("mousemove", onMove);
              window.removeEventListener("mouseup", onUp);
            };
            window.addEventListener("mousemove", onMove);
            window.addEventListener("mouseup", onUp);
          }}
        />
      )}
      <div className="summary-header">
        <button
          type="button"
          className="plain-button"
          onClick={() => {
            props.onClearSummaryError();
            props.onExpanded(!props.expanded);
          }}
        >
          {props.expanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          {props.t("summary")}
        </button>
        <div className="toolbar-spacer" />
        {props.summaryStatus === "running" && <span className="muted">{props.t("loading")}</span>}
        {props.expanded && (
          <>
            <button type="button" onClick={() => void runSummary()} disabled={props.summaryStatus === "running"}>
              {props.t("summary")}
            </button>
            <button type="button" disabled>
              {props.t("abort")}
            </button>
            <button type="button" disabled={!props.entry.summaryText} onClick={() => void navigator.clipboard?.writeText(props.entry.summaryText)}>
              {props.t("copy")}
            </button>
            <button
              type="button"
              disabled={!props.entry.summaryText}
              onClick={() => {
                props.onClearSummaryError();
                props.onUpdateEntry(props.entry.id, (entry) => ({ ...entry, summaryText: "" }));
              }}
            >
              {props.t("clear")}
            </button>
          </>
        )}
      </div>
      {props.expanded && (
        <>
          <div className="summary-meta">
            <span>{props.t("target")}=en</span>
            <span>{props.t("detail")}={props.t("medium")}</span>
          </div>
          <div className="summary-content" dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(props.summaryError ?? (props.entry.summaryText || props.t("emptySummary"))) }} />
        </>
      )}
    </section>
  );
}

function ModalHost(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  state: AppState;
  entries: Entry[];
  tags: Tag[];
  digestEntries: Entry[];
  onClose: () => void;
  onLocale: (locale: LocaleCode) => void;
  onSettingsTab: (tab: AppState["settingsTab"]) => void;
  onReportKind: (kind: AppState["reportKind"]) => void;
  onModal: (modal: ModalState) => void;
  onBatchNotice: (notice: string) => void;
  onSetTags: (tags: Tag[]) => void;
  feedActionStatus: "idle" | "running" | "error";
  feedActionError: string | null;
  onAddFeed: (url: string, sync?: boolean) => Promise<Feed>;
  onImportOpml: (file: File, syncAfterImport: boolean) => Promise<unknown>;
}) {
  const { t, state } = props;
  if (state.modal.type === "none") {
    return null;
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    // 只在点击 backdrop 本身时关闭，不包括 modal 内容
    if (e.target === e.currentTarget) {
      props.onClose();
    }
  };

  const modalClassName = [
    "modal",
    state.modal.type === "settings" || state.modal.type === "usageReport" ? "wide" : "",
    state.modal.type === "feedEditor" || state.modal.type === "importOpml" ? "compact" : ""
  ].filter(Boolean).join(" ");

  return (
    <div className="modal-backdrop" role="presentation" onClick={handleBackdropClick}>
      <div className={modalClassName} role="dialog" aria-modal="true">
        <div className="modal-header">
          <h2>{modalTitle(t, state.modal)}</h2>
          <button className="icon-button" type="button" onClick={props.onClose}>
            <X size={16} aria-hidden />
          </button>
        </div>
        {state.modal.type === "settings" && (
          <SettingsModal t={t} state={state} onLocale={props.onLocale} onTab={props.onSettingsTab} onModal={props.onModal} />
        )}
        {state.modal.type === "importOpml" && (
          <SimpleFlow
            t={t}
            status={props.feedActionStatus}
            error={props.feedActionError}
            onImportOpml={props.onImportOpml}
            onClose={props.onClose}
          />
        )}
        {state.modal.type === "feedEditor" && (
          <FeedEditor
            t={t}
            status={props.feedActionStatus}
            error={props.feedActionError}
            onAddFeed={props.onAddFeed}
            onClose={props.onClose}
          />
        )}
        {state.modal.type === "shareDigest" && <DigestModal t={t} entries={props.digestEntries} tags={props.tags} mode={state.modal.exportMode} />}
        {state.modal.type === "batchTagging" && <BatchTaggingModal t={t} notice={state.batchNotice} onNotice={props.onBatchNotice} />}
        {state.modal.type === "tagLibrary" && <TagLibraryModal t={t} tags={props.tags} onSetTags={props.onSetTags} />}
        {state.modal.type === "usageReport" && <UsageReportModal t={t} state={state} onKind={props.onReportKind} />}
      </div>
    </div>
  );
}

function SettingsModal(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  state: AppState;
  onLocale: (locale: LocaleCode) => void;
  onTab: (tab: AppState["settingsTab"]) => void;
  onModal: (modal: ModalState) => void;
}) {
  const tabs: AppState["settingsTab"][] = ["general", "reader", "agents", "digest"];
  const [providers, setProviders] = useState<Array<{ name: string; kind: string; model: string; base_url?: string | null; is_default: boolean; has_api_key: boolean }>>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ status: string; error?: string } | null>(null);

  // 编辑表单状态
  const [isEditing, setIsEditing] = useState(false);
  const [isNewProvider, setIsNewProvider] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    kind: "openai_compatible",
    model: "",
    base_url: "",
    api_key: "",
    api_key_header: "",
    is_default: false,
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadProviders = async () => {
    try {
      const { getProviders } = await import("./services/api");
      const data = await getProviders();
      setProviders(data);
      return data;
    } catch (error) {
      console.error("Failed to load providers:", error);
      return [];
    }
  };

  useEffect(() => {
    loadProviders().then((data) => {
      const defaultProvider = data.find((p) => p.is_default);
      if (defaultProvider) {
        setSelectedProvider(defaultProvider.name);
      } else if (data.length > 0) {
        setSelectedProvider(data[0].name);
      }
    });
  }, []);

  const handleSelectProvider = (name: string) => {
    setSelectedProvider(name);
    const provider = providers.find((p) => p.name === name);
    if (provider) {
      setFormData({
        name: provider.name,
        kind: provider.kind,
        model: provider.model,
        base_url: provider.base_url || "",
        api_key: "",
        api_key_header: "",
        is_default: provider.is_default,
      });
      setIsEditing(true);
      setIsNewProvider(false);
    }
  };

  const handleAddNew = () => {
    setSelectedProvider("");
    setFormData({
      name: "",
      kind: "openai_compatible",
      model: "",
      base_url: "",
      api_key: "",
      api_key_header: "",
      is_default: providers.length === 0,
    });
    setIsEditing(true);
    setIsNewProvider(true);
    setTestResult(null);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;
    setSaving(true);
    try {
      const { createProvider, updateProvider } = await import("./services/api");
      if (isNewProvider) {
        await createProvider(formData);
      } else {
        await updateProvider(selectedProvider, formData);
      }
      setIsEditing(false);
      setIsNewProvider(false);
      const data = await loadProviders();
      setSelectedProvider(formData.name);
      // 如果设为默认，刷新列表
      if (formData.is_default) {
        await loadProviders();
      }
    } catch (error) {
      console.error("Failed to save provider:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedProvider) return;
    setDeleting(true);
    try {
      const { deleteProvider } = await import("./services/api");
      await deleteProvider(selectedProvider);
      setIsEditing(false);
      setSelectedProvider("");
      await loadProviders();
    } catch (error) {
      console.error("Failed to delete provider:", error);
    } finally {
      setDeleting(false);
    }
  };

  const handleTestProvider = async () => {
    if (!selectedProvider) return;
    setTestingProvider(selectedProvider);
    setTestResult(null);
    try {
      const { testProvider } = await import("./services/api");
      const result = await testProvider(selectedProvider);
      setTestResult(result);
    } catch (error) {
      setTestResult({ status: "error", error: String(error) });
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSetDefault = async () => {
    if (!selectedProvider) return;
    try {
      const { setDefaultProvider } = await import("./services/api");
      await setDefaultProvider(selectedProvider);
      // 更新 formData
      setFormData((prev) => ({ ...prev, is_default: true }));
      await loadProviders();
    } catch (error) {
      console.error("Failed to set default provider:", error);
    }
  };

  const handleFormChange = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="settings-layout">
      <div className="tab-list">
        {tabs.map((tab) => (
          <button key={tab} type="button" className={props.state.settingsTab === tab ? "active" : ""} onClick={() => props.onTab(tab)}>
            {props.t(tab)}
          </button>
        ))}
      </div>
      <div className="settings-panel">
        {props.state.settingsTab === "general" && (
          <>
            <SettingRow label={props.t("language")}>
              <select value={props.state.locale} onChange={(event) => props.onLocale(event.target.value as LocaleCode)}>
                <option value="en">English</option>
                <option value="zh-Hans">简体中文</option>
              </select>
            </SettingRow>
            <Slider label={props.t("concurrency")} value={6} min={2} max={10} step={1} onChange={() => undefined} />
            <SettingRow label={props.t("retention")}>
              <select defaultValue="six">
                <option value="one">1 Month</option>
                <option value="three">3 Months</option>
                <option value="six">6 Months</option>
                <option value="forever">{props.t("forever")}</option>
              </select>
            </SettingRow>
            <SettingRow label={props.t("tagSystem")}>
              <button type="button" onClick={() => props.onModal({ type: "batchTagging" })}>{props.t("batchTagging")}</button>
              <button type="button" onClick={() => props.onModal({ type: "tagLibrary" })}>{props.t("tagLibrary")}</button>
            </SettingRow>
          </>
        )}
        {props.state.settingsTab === "reader" && (
          <>
            <SettingRow label={props.t("quickThemes")}>
              <span>{props.t(props.state.theme.preset)}</span>
            </SettingRow>
            <SettingRow label={props.t("fontSize")}>
              <span>{props.state.theme.fontSize}</span>
            </SettingRow>
            <div className="reader-settings-preview">{props.t("previewSentence")}</div>
          </>
        )}
        {props.state.settingsTab === "agents" && (
          <div className="provider-settings">
            {/* Provider 选择器 */}
            <SettingRow label={props.t("provider")}>
              <div className="provider-selector">
                <select
                  value={selectedProvider}
                  onChange={(event) => handleSelectProvider(event.target.value)}
                >
                  {providers.length === 0 && (
                    <option value="">{props.t("noProviders")}</option>
                  )}
                  {providers.map((provider) => (
                    <option key={provider.name} value={provider.name}>
                      {provider.name}
                    </option>
                  ))}
                </select>
                <button type="button" className="add-provider-btn" onClick={handleAddNew}>
                  {props.t("addProvider")}
                </button>
              </div>
            </SettingRow>

            {/* 编辑表单 */}
            {isEditing && (
              <div className="provider-form">
                <SettingRow label={props.t("providerName")}>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(event) => handleFormChange("name", event.target.value)}
                    disabled={!isNewProvider}
                    placeholder="e.g., openai, deepseek, ollama"
                  />
                </SettingRow>
                <SettingRow label={props.t("providerType")}>
                  <select
                    value={formData.kind}
                    onChange={(event) => handleFormChange("kind", event.target.value)}
                  >
                    <option value="openai_compatible">OpenAI Compatible</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="ollama">Ollama (Local)</option>
                  </select>
                </SettingRow>
                <SettingRow label={props.t("model")}>
                  <input
                    type="text"
                    value={formData.model}
                    onChange={(event) => handleFormChange("model", event.target.value)}
                    placeholder="e.g., gpt-4o, claude-3-opus, llama3"
                  />
                </SettingRow>
                <SettingRow label={props.t("baseUrl")}>
                  <input
                    type="text"
                    value={formData.base_url}
                    onChange={(event) => handleFormChange("base_url", event.target.value)}
                    placeholder="e.g., https://api.openai.com/v1"
                  />
                </SettingRow>
                <SettingRow label={props.t("apiKey")}>
                  <input
                    type="password"
                    value={formData.api_key}
                    onChange={(event) => handleFormChange("api_key", event.target.value)}
                    placeholder={providers.find((p) => p.name === selectedProvider)?.has_api_key ? "(已配置)" : "sk-..."}
                  />
                </SettingRow>
                <SettingRow label={props.t("apiKeyHeader")}>
                  <input
                    type="text"
                    value={formData.api_key_header}
                    onChange={(event) => {
                      // 只允许 ASCII 字符
                      const value = event.target.value.replace(/[^\x00-\x7F]/g, "");
                      handleFormChange("api_key_header", value);
                    }}
                    placeholder="留空使用默认 Authorization: Bearer"
                  />
                </SettingRow>
                <SettingRow label={props.t("defaultProvider")}>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.is_default}
                      onChange={(event) => handleFormChange("is_default", event.target.checked)}
                    />
                    <span>{props.t("setAsDefault")}</span>
                  </label>
                </SettingRow>
                <SettingRow label={props.t("availability")}>
                  <button
                    type="button"
                    disabled={testingProvider !== null || !selectedProvider}
                    onClick={handleTestProvider}
                  >
                    {testingProvider === selectedProvider ? props.t("testing") : props.t("testConnection")}
                  </button>
                  {testResult && (
                    <span className={`status-pill ${testResult.status === "ok" ? "success" : "error"}`}>
                      {testResult.status === "ok" ? props.t("ready") : testResult.error ?? props.t("failed")}
                    </span>
                  )}
                </SettingRow>
                <SettingRow label={props.t("fallback")}>
                  <span>{props.t("fallbackChain")}</span>
                </SettingRow>
                <div className="provider-actions">
                  <button type="button" className="btn-secondary" onClick={handleAddNew}>
                    {props.t("addNew")}
                  </button>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={handleDelete}
                    disabled={deleting || !selectedProvider}
                  >
                    {deleting ? props.t("deleting") : props.t("deleteProvider")}
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={handleSave}
                    disabled={saving || !formData.name.trim()}
                  >
                    {saving ? props.t("saving") : props.t("saveProvider")}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        {props.state.settingsTab === "digest" && (
          <>
            <SettingRow label={props.t("exportFolder")}>
              <code>~/Documents/Lumen Digests</code>
            </SettingRow>
            <SettingRow label={props.t("templates")}>
              <span>{digestTemplates.map((template) => template.title).join(", ")}</span>
            </SettingRow>
          </>
        )}
      </div>
    </div>
  );
}

function DigestModal(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  entries: Entry[];
  tags: Tag[];
  mode: "share" | "single" | "multiple";
}) {
  const template = digestTemplates.find((candidate) => candidate.id === (props.mode === "multiple" ? "multiple" : "share")) ?? digestTemplates[0];
  const digest = composeDigest(props.entries, props.tags, template);
  return (
    <div className="modal-body">
      <SettingRow label={props.t("templates")}>
        <select defaultValue={template.id}>
          {digestTemplates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.title}
            </option>
          ))}
        </select>
      </SettingRow>
      <textarea className="digest-preview" value={digest} readOnly aria-label={props.t("preview")} />
      <div className="modal-actions">
        <button type="button" onClick={() => void navigator.clipboard?.writeText(digest)}>
          {props.t("copy")}
        </button>
        <button type="button">{props.t(props.mode === "share" ? "share" : "export")}</button>
      </div>
    </div>
  );
}

function BatchTaggingModal(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  notice: string | null;
  onNotice: (notice: string) => void;
}) {
  const [step, setStep] = useState<"setup" | "run" | "review" | "apply">("setup");
  return (
    <div className="modal-body">
      <div className="stepper">
        {(["setup", "run", "review", "apply"] as const).map((item) => (
          <button key={item} type="button" className={step === item ? "active" : ""} onClick={() => setStep(item)}>
            {props.t(`batch${capitalize(item)}`)}
          </button>
        ))}
      </div>
      <div className="message-area">{props.notice ?? props.t("batchNotice")}</div>
      <div className="review-list">
        <span>{"AI -> e1, e5, e7"}</span>
        <span>{"UX -> e3, e6"}</span>
      </div>
      <div className="modal-actions">
        <button type="button" onClick={() => props.onNotice(props.t("success"))}>
          {props.t("batchApply")}
        </button>
        <button type="button" onClick={() => props.onNotice(props.t("failure"))}>
          {props.t("failure")}
        </button>
      </div>
    </div>
  );
}

function TagLibraryModal(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  tags: Tag[];
  onSetTags: (tags: Tag[]) => void;
}) {
  const [selectedId, setSelectedId] = useState(props.tags[0]?.id ?? "");
  const selected = props.tags.find((tag) => tag.id === selectedId) ?? props.tags[0];
  return (
    <div className="tag-library">
      <div className="tag-library-list">
        {props.tags.map((tag) => (
          <button key={tag.id} type="button" className={selected?.id === tag.id ? "active" : ""} onClick={() => setSelectedId(tag.id)}>
            {tag.name}
          </button>
        ))}
      </div>
      {selected && (
        <div className="tag-inspector">
          <SettingRow label={props.t("rename")}>
            <input
              value={selected.name}
              onChange={(event) => props.onSetTags(props.tags.map((tag) => (tag.id === selected.id ? { ...tag, name: event.target.value } : tag)))}
            />
          </SettingRow>
          <SettingRow label={props.t("aliases")}>
            <input value={selected.aliases.join(", ")} readOnly />
          </SettingRow>
          <SettingRow label={props.t("merge")}>
            <select defaultValue="">
              <option value="" disabled>
                {props.t("tags")}
              </option>
              {props.tags.filter((tag) => tag.id !== selected.id).map((tag) => (
                <option key={tag.id}>{tag.name}</option>
              ))}
            </select>
          </SettingRow>
          <p className="panel-status">{selected.name.trim().length === 0 ? props.t("conflict") : props.t("ready")}</p>
        </div>
      )}
    </div>
  );
}

function UsageReportModal(props: {
  t: (key: string, values?: Record<string, string | number>) => string;
  state: AppState;
  onKind: (kind: AppState["reportKind"]) => void;
}) {
  const report = usageReports[0];
  const max = Math.max(...report.buckets.map((bucket) => bucket.promptTokens + bucket.completionTokens));
  const totalRequests = report.buckets.reduce((sum, bucket) => sum + bucket.requests, 0);
  const totalTokens = report.buckets.reduce((sum, bucket) => sum + bucket.promptTokens + bucket.completionTokens, 0);
  const kinds: AppState["reportKind"][] = ["overview", "provider", "model", "agent", "comparison"];
  return (
    <div className="usage-layout">
      <div className="tab-list horizontal">
        {kinds.map((kind) => (
          <button key={kind} type="button" className={props.state.reportKind === kind ? "active" : ""} onClick={() => props.onKind(kind)}>
            {props.t(kind)}
          </button>
        ))}
      </div>
      <div className="usage-chart">
        {report.buckets.map((bucket) => (
          <div key={bucket.day} className="usage-bar">
            <span style={{ height: `${((bucket.promptTokens + bucket.completionTokens) / max) * 100}%` }} />
            <small>{bucket.day}</small>
          </div>
        ))}
      </div>
      <div className="usage-metrics">
        <Metric label={props.t("requests")} value={String(totalRequests)} />
        <Metric label={props.t("tokens")} value={String(totalTokens)} />
        <Metric label={props.t("successRate")} value="94%" />
      </div>
      <div className="modal-actions">
        <button type="button">
          <Copy size={15} aria-hidden />
          {props.t("copy")}
        </button>
        <button type="button">
          <Download size={15} aria-hidden />
          {props.t("export")}
        </button>
      </div>
    </div>
  );
}

function FeedEditor(props: {
  t: (key: string) => string;
  status: "idle" | "running" | "error";
  error: string | null;
  onAddFeed: (url: string, sync?: boolean) => Promise<Feed>;
  onClose: () => void;
}) {
  const [url, setUrl] = useState("");
  const [syncOnCreate, setSyncOnCreate] = useState(true);

  async function submit() {
    if (!url.trim()) {
      return;
    }
    try {
      await props.onAddFeed(url.trim(), syncOnCreate);
      props.onClose();
    } catch {
      return;
    }
  }

  return (
    <div className="modal-body">
      <p className="modal-caption">{props.t("feedEditorHint")}</p>
      <SettingRow label={props.t("feedUrl")}>
        <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://devblogs.microsoft.com/python/feed/" />
      </SettingRow>
      <label className="check-row">
        <input type="checkbox" checked={syncOnCreate} onChange={(event) => setSyncOnCreate(event.target.checked)} />
        {props.t("syncAfterAdd")}
      </label>
      {props.error && <p className="panel-status">{props.error}</p>}
      <div className="modal-actions">
        <button type="button" onClick={props.onClose}>
          {props.t("cancel")}
        </button>
        <button type="button" disabled={!url.trim() || props.status === "running"} onClick={() => void submit()}>
          {props.status === "running" ? props.t("loading") : props.t("save")}
        </button>
      </div>
    </div>
  );
}

function SimpleFlow(props: {
  t: (key: string) => string;
  status: "idle" | "running" | "error";
  error: string | null;
  onImportOpml: (file: File, syncAfterImport: boolean) => Promise<unknown>;
  onClose: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [syncAfterImport, setSyncAfterImport] = useState(true);

  async function submit() {
    if (!file) {
      return;
    }
    try {
      await props.onImportOpml(file, syncAfterImport);
      props.onClose();
    } catch {
      return;
    }
  }

  return (
    <div className="modal-body">
      <p className="modal-caption">{props.t("opmlImportHint")}</p>
      <SettingRow label={props.t("importOpml")}>
        <input
          type="file"
          accept=".opml,.xml,text/xml,application/xml"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </SettingRow>
      <label className="check-row">
        <input type="checkbox" checked={syncAfterImport} onChange={(event) => setSyncAfterImport(event.target.checked)} />
        {props.t("syncAfterImport")}
      </label>
      {file && <p className="panel-status">{file.name}</p>}
      {props.error && <p className="panel-status">{props.error}</p>}
      <div className="modal-actions">
        <button type="button" onClick={props.onClose}>
          {props.t("cancel")}
        </button>
        <button type="button" disabled={!file || props.status === "running"} onClick={() => void submit()}>
          {props.status === "running" ? props.t("loading") : props.t("importAction")}
        </button>
      </div>
    </div>
  );
}

function MenuButton(props: {
  label: string;
  icon?: React.ReactNode;
  items: Array<{ label: string; action: () => void; disabled?: boolean; destructive?: boolean }>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="menu-root">
      <button className="icon-button" type="button" onClick={() => setOpen(!open)} title={props.label}>
        {props.icon ?? <MoreHorizontal size={17} aria-hidden />}
      </button>
      {open && (
        <div className="menu-popover">
          {props.items.map((item) => (
            <button
              key={item.label}
              type="button"
              className={item.destructive ? "destructive" : ""}
              disabled={item.disabled}
              onClick={() => {
                item.action();
                setOpen(false);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SettingRow(props: { label: string; children: React.ReactNode }) {
  return (
    <label className="setting-row">
      <span>{props.label}</span>
      <div>{props.children}</div>
    </label>
  );
}

function Slider(props: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return (
    <label className="setting-row">
      <span>{props.label}</span>
      <div className="slider-row">
        <input
          type="range"
          min={props.min}
          max={props.max}
          step={props.step}
          value={props.value}
          onChange={(event) => props.onChange(Number(event.target.value))}
        />
        <output>{props.value}</output>
      </div>
    </label>
  );
}

function Metric(props: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function modalTitle(t: (key: string) => string, modal: ModalState): string {
  switch (modal.type) {
    case "settings":
      return t("settings");
    case "feedEditor":
      return t("addFeed");
    case "importOpml":
      return t("importOpml");
    case "shareDigest":
      return t(modal.exportMode === "share" ? "shareDigest" : "exportDigest");
    case "batchTagging":
      return t("batchTagging");
    case "tagLibrary":
      return t("tagLibrary");
    case "usageReport":
      return t("usageReports");
    case "none":
      return "";
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(
    new Date(value)
  );
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderInlineMarkdown(text: string): string {
  let html = escapeHtml(text);
  // Links: [label](url)
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_match, label, url) =>
    `<a href="${url}" target="_blank" rel="noopener">${label}</a>`
  );
  // Bold then italic, code spans
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  return html;
}

// Minimal markdown -> HTML for translated content (no external deps).
// Handles headings, lists, blockquotes, code fences, and paragraphs.
function markdownToHtml(markdown: string): string {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: string[] = [];
  let paragraph: string[] = [];
  let listItems: string[] = [];
  let listOrdered = false;
  let inCodeFence = false;
  let codeLines: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length > 0) {
      blocks.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
  };
  const flushList = () => {
    if (listItems.length > 0) {
      const tag = listOrdered ? "ol" : "ul";
      blocks.push(`<${tag}>${listItems.join("")}</${tag}>`);
      listItems = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine;

    if (line.trim().startsWith("```")) {
      if (inCodeFence) {
        blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
        inCodeFence = false;
      } else {
        flushParagraph();
        flushList();
        inCodeFence = true;
      }
      continue;
    }
    if (inCodeFence) {
      codeLines.push(line);
      continue;
    }

    if (line.trim() === "") {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      blocks.push(`<h${level}>${renderInlineMarkdown(heading[2].trim())}</h${level}>`);
      continue;
    }

    const ordered = line.match(/^\s*\d+\.\s+(.*)$/);
    const unordered = line.match(/^\s*[-*+]\s+(.*)$/);
    if (ordered || unordered) {
      flushParagraph();
      const ofType = Boolean(ordered);
      if (listItems.length > 0 && ofType !== listOrdered) {
        flushList();
      }
      listOrdered = ofType;
      const item = (ordered ?? unordered)![1];
      listItems.push(`<li>${renderInlineMarkdown(item.trim())}</li>`);
      continue;
    }

    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) {
      flushParagraph();
      flushList();
      blocks.push(`<blockquote>${renderInlineMarkdown(quote[1].trim())}</blockquote>`);
      continue;
    }

    paragraph.push(line.trim());
  }

  if (inCodeFence) {
    blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  flushParagraph();
  flushList();

  return blocks.join("\n");
}

// Render translated content that may contain bilingual wrapper divs
// (<div class="bilingual-original">…</div> / "bilingual-translation").
// The markdown INSIDE each wrapper is rendered via markdownToHtml so bold,
// lists, headings etc. display correctly; the wrapper divs are preserved so
// the bilingual CSS still applies. Plain (non-bilingual) markdown falls
// through to markdownToHtml unchanged.
function renderBilingualMarkdown(text: string): string {
  const blockPattern = /<div class="bilingual-(original|translation)">([\s\S]*?)<\/div>/g;
  if (!blockPattern.test(text)) {
    return markdownToHtml(text);
  }
  blockPattern.lastIndex = 0;
  return text.replace(blockPattern, (_match, variant, inner) =>
    `<div class="bilingual-${variant}">${markdownToHtml(inner.trim())}</div>`
  );
}

function capitalize(value: string): string {
  return `${value[0]?.toUpperCase() ?? ""}${value.slice(1)}`;
}

// Pick the translation target by detecting the article's dominant language:
// Chinese source -> English, otherwise -> Chinese (中文). This keeps the
// bilingual view meaningful regardless of the UI locale, so an English
// article read in an English UI still gets a Chinese translation rather than
// a no-op "English -> English" round trip.
function detectTargetLang(content: string): string {
  const chineseChars = (content.match(/[一-鿿]/g) ?? []).length;
  const asciiLetters = (content.match(/[A-Za-z]/g) ?? []).length;
  // Treat the text as Chinese when CJK characters clearly dominate.
  return chineseChars > asciiLetters ? "English" : "中文";
}

function emptyProviderDraft(): ProviderDraft {
  return {
    name: "",
    kind: "openai_compatible",
    model: "",
    baseUrl: "",
    apiKey: "",
    apiKeyHeader: "",
    isDefault: false,
    clearApiKey: false
  };
}

function providerDraftFromSelection(providers: ProviderSummary[], providerName: string): ProviderDraft {
  const provider = providers.find((candidate) => candidate.name === providerName);
  if (!provider) {
    return emptyProviderDraft();
  }
  return {
    name: provider.name,
    kind: provider.kind,
    model: provider.model,
    baseUrl: provider.baseUrl ?? "",
    apiKey: "",
    apiKeyHeader: provider.apiKeyHeader ?? "",
    isDefault: provider.isDefault,
    clearApiKey: false
  };
}

function pickProviderSelection(providers: ProviderSummary[], currentSelection: string): string {
  if (providers.some((provider) => provider.name === currentSelection)) {
    return currentSelection;
  }
  return providers.find((provider) => provider.isDefault)?.name ?? providers[0]?.name ?? "__new__";
}

function selectedProviderHasKey(providers: ProviderSummary[], providerName: string): boolean {
  return providers.some((provider) => provider.name === providerName && provider.hasApiKey);
}
