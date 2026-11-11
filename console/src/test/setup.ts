import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import { clearBundleCache } from "../data/loader";

// jsdom has no layout: scrolling is a no-op, and every media query is false.
Element.prototype.scrollIntoView = () => undefined;
window.matchMedia = (query: string) =>
  ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList;

afterEach(() => {
  cleanup();
  clearBundleCache();
});
