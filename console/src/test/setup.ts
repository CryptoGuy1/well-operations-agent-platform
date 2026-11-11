import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import { clearBundleCache } from "../data/loader";

afterEach(() => {
  cleanup();
  clearBundleCache();
});
