import type { components } from "@mercury/shared-types";

import type { IpcClient } from "./index";

export function translateArticle(
  client: IpcClient,
  body: components["schemas"]["TranslationRequest"]
) {
  return client.request<components["schemas"]["TranslationResult"], components["schemas"]["TranslationRequest"]>(
    "POST",
    "/agents/translation",
    { body }
  );
}
