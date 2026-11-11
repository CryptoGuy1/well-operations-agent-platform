// Reads the committed data bundle (public/data/, served next to the page). The console makes no
// other requests: there is no API and nothing to authenticate.

export class BundleError extends Error {
  readonly path: string;

  constructor(path: string, message: string) {
    super(`${path}: ${message}`);
    this.name = "BundleError";
    this.path = path;
  }
}

const cache = new Map<string, Promise<unknown>>();

/** The URL of a bundle file, relative to the page's base (the site may live under any path). */
export function bundleUrl(path: string, base: string = import.meta.env.BASE_URL): string {
  if (path.startsWith("/") || path.includes("..")) {
    throw new BundleError(path, "not a bundle path");
  }
  return `${base.endsWith("/") ? base : `${base}/`}data/${path}`;
}

/** One bundle file, parsed. Each file is fetched once; a failed fetch is not cached. */
export function loadJson<T>(path: string, check?: (value: unknown) => value is T): Promise<T> {
  const cached = cache.get(path);
  if (cached) {
    return cached as Promise<T>;
  }
  const loading = fetchJson(path).then((value) => {
    if (check && !check(value)) {
      throw new BundleError(path, "unexpected content");
    }
    return value as T;
  });
  cache.set(path, loading);
  loading.catch(() => cache.delete(path));
  return loading;
}

async function fetchJson(path: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(bundleUrl(path));
  } catch {
    throw new BundleError(path, "could not be fetched");
  }
  if (!response.ok) {
    throw new BundleError(path, `HTTP ${response.status}`);
  }
  try {
    return (await response.json()) as unknown;
  } catch {
    throw new BundleError(path, "is not JSON");
  }
}

export function clearBundleCache(): void {
  cache.clear();
}
