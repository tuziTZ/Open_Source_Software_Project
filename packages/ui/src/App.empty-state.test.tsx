import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("App empty state", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/feeds") || url.endsWith("/tags") || url.endsWith("/entries")) {
        return new Response("[]", {
          status: 200,
          headers: { "content-type": "application/json" }
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    }) as typeof fetch);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("does not show an error when backend data is empty", async () => {
    const { App } = await import("./App");

    render(<App />);

    await waitFor(() => {
      expect(document.querySelector(".reader-workspace")?.getAttribute("aria-busy")).toBe("false");
    });

    expect(screen.queryByText("Entry list failed to load.")).toBeNull();
    expect(screen.getByText("No entries match this scope.")).toBeTruthy();
    expect(screen.queryByText("Loading...")).toBeNull();
  });

  it("exposes OPML import from the feed add menu", async () => {
    const { App } = await import("./App");

    render(<App />);

    await waitFor(() => {
      expect(document.querySelector(".reader-workspace")?.getAttribute("aria-busy")).toBe("false");
    });

    fireEvent.click(screen.getByTitle("Add Feed..."));
    fireEvent.click(screen.getByText("Import OPML..."));

    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText("Choose an OPML file to merge subscriptions into your library. Existing feeds are preserved.")).toBeTruthy();
  });
});
