import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export function cleanStoredContent(client: IpcClient, articleId: string) {
  return client.request<components["schemas"]["CleanContentResponse"]>("GET", `/content/entries/${articleId}/clean`);
}

export function getEntryWebPage(client: IpcClient, articleId: string) {
  return client.request<components["schemas"]["WebPageResponse"]>("GET", `/content/entries/${articleId}/web`);
}
