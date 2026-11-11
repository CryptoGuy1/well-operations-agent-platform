import { useEffect, useState } from "react";

import { loadJson } from "./loader";

export type Loaded<T> =
  { state: "loading" } | { state: "error"; error: Error } | { state: "ready"; data: T };

type Settled<T> = { state: "error"; error: Error } | { state: "ready"; data: T };

/** One bundle file for a component: loading, then ready or error. */
export function useBundle<T>(path: string, check?: (value: unknown) => value is T): Loaded<T> {
  // The settled result is kept with its path, so a new path reads as loading at once.
  const [settled, setSettled] = useState<{ path: string; result: Settled<T> } | null>(null);
  useEffect(() => {
    let current = true;
    loadJson(path, check).then(
      (data) => {
        if (current) setSettled({ path, result: { state: "ready", data } });
      },
      (error: unknown) => {
        if (current) {
          const e = error instanceof Error ? error : new Error(String(error));
          setSettled({ path, result: { state: "error", error: e } });
        }
      },
    );
    return () => {
      current = false;
    };
  }, [path, check]);
  return settled?.path === path ? settled.result : { state: "loading" };
}
