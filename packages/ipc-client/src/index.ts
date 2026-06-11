export interface ClientOptions {
  baseUrl: string;
  fetch?: typeof fetch;
  headers?: HeadersInit;
}

export class IpcError extends Error {
  constructor(
    public readonly status: number,
    public readonly url: string,
    public readonly body: unknown,
  ) {
    super(`IPC ${status} ${url}`);
  }
}

export interface IpcClient {
  request<TResponse, TBody = unknown>(
    method: string,
    path: string,
    init?: {
      body?: TBody;
      query?: Record<string, string | number | boolean | undefined>;
      headers?: HeadersInit;
      bodyType?: "json" | "raw";
    },
  ): Promise<TResponse>;
}

export function createClient(options: ClientOptions): IpcClient {
  const fetchImpl = options.fetch ?? globalThis.fetch.bind(globalThis);
  const baseUrl = options.baseUrl.replace(/\/$/, "");
  const baseHeaders = options.headers;

  return {
    async request<TResponse, TBody = unknown>(
      method: string,
      path: string,
      init?: {
        body?: TBody;
        query?: Record<string, string | number | boolean | undefined>;
        headers?: HeadersInit;
        bodyType?: "json" | "raw";
      },
    ): Promise<TResponse> {
      const url = new URL(baseUrl + path);
      if (init?.query) {
        for (const [key, value] of Object.entries(init.query)) {
          if (value !== undefined) url.searchParams.set(key, String(value));
        }
      }

      const headers = new Headers(baseHeaders);
      if (init?.headers) {
        new Headers(init.headers).forEach((value, key) => headers.set(key, value));
      }
      let body: BodyInit | undefined;
      if (init?.body !== undefined) {
        if (init.bodyType === "raw") {
          body = init.body as BodyInit;
        } else {
          headers.set("content-type", "application/json");
          body = JSON.stringify(init.body);
        }
      }

      const response = await fetchImpl(url.toString(), { method, headers, body });
      const text = await response.text();
      const parsed = text.length > 0 ? JSON.parse(text) : undefined;

      if (!response.ok) {
        throw new IpcError(response.status, url.toString(), parsed);
      }
      return parsed as TResponse;
    },
  };
}

export * from "./entries";
export * from "./feeds";
export * from "./content";
export * from "./summary";
export * from "./tags";
export * from "./providers";
