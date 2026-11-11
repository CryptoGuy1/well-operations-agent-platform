// Snapshots of the console for the README: serves the production build (dist/) locally and
// saves PNGs to docs/images/console/. Run through `make console-screenshots`, which builds first.
// Runs and claims are found through the console itself, never named here, so the snapshots
// follow the committed data bundle. Every later page adds its snapshots to SHOTS.
import { spawn } from "node:child_process";
import { mkdir, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const PORT = 4179;
const BASE = `http://127.0.0.1:${PORT}/`;
const OUT = fileURLToPath(new URL("../../docs/images/console/", import.meta.url));
const MAX_BYTES = 400 * 1024;

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  phone: { width: 390, height: 844 },
};

const F11_T2 = "15/9-F-11 T2"; // the worked example of the repository

/** The run page of the first 15/9-F-11 T2 run in the runs list, with its first verified claim
 *  selected. */
async function f11RunWithClaim(page) {
  await open(page, `#/runs?${new URLSearchParams({ wellbore: F11_T2 }).toString()}`);
  await page.locator("table a[href*='/runs/']").first().click();
  await settle(page);
  await page.locator("button.claim--verified").first().click();
  return page.url();
}

/** The run behind the overview's "See the checker catch an error" button, its contradicted
 *  claim selected. */
async function checkerCatch(page) {
  await open(page, "#/");
  await page.getByRole("link", { name: "See the checker catch an error" }).click();
  return page.url();
}

/** The 15/9-F-11 T2 well page, through the wells list. */
async function f11Well(page) {
  await open(page, "#/wells");
  await page.getByRole("link", { name: F11_T2, exact: true }).click();
  return page.url();
}

// name, viewport, colour scheme, the page (an address, or a function that finds one) and,
// optionally, an element to start the snapshot at.
const SHOTS = [
  ["overview-desktop-light", "desktop", "light", "#/"],
  ["overview-desktop-dark", "desktop", "dark", "#/"],
  ["overview-phone-light", "phone", "light", "#/"],
  ["runs-list-desktop-light", "desktop", "light", "#/runs"],
  ["run-claim-desktop-light", "desktop", "light", f11RunWithClaim],
  ["run-claim-phone-light", "phone", "light", f11RunWithClaim],
  ["checker-catch-desktop-dark", "desktop", "dark", checkerCatch],
  ["well-page-desktop-light", "desktop", "light", f11Well],
  ["well-page-phone-light", "phone", "light", f11Well, "#depth-heading"],
];

async function open(page, hash) {
  await page.goto(BASE + hash);
  await settle(page);
}

/** Wait until the data is loaded, the fonts are in and layout has settled. */
async function settle(page) {
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() => !/Loading/.test(document.body.innerText));
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  });
}

/** Lay out and paint the page again, now that the fonts are in. Native controls (selects, the
 *  replay slider) painted while fonts were loading land half a pixel apart from one run to the
 *  next. Scroll positions are kept, in whole pixels. */
async function repaint(page) {
  await page.evaluate(async () => {
    const scrolled = [document.scrollingElement, ...document.querySelectorAll(".panel")]
      .filter((el) => el !== null)
      .map((el) => [el, el.scrollTop]);
    document.body.style.display = "none";
    void document.body.offsetHeight;
    document.body.style.display = "";
    for (const [el, top] of scrolled) el.scrollTop = Math.round(top);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  });
}

async function serve() {
  const server = spawn(
    "npx",
    ["vite", "preview", "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"],
    { stdio: "ignore" },
  );
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(BASE)).ok) return server;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  server.kill();
  throw new Error(`The preview server did not start on port ${PORT}.`);
}

async function main() {
  await mkdir(OUT, { recursive: true });
  const server = await serve();
  // Software rendering with fixed colour and text settings, so that two runs give the same pixels.
  const browser = await chromium.launch({
    args: [
      "--disable-gpu",
      "--force-color-profile=srgb",
      "--font-render-hinting=none",
      "--disable-lcd-text",
    ],
  });
  const oversized = [];
  try {
    for (const [name, viewport, scheme, target, startAt] of SHOTS) {
      const context = await browser.newContext({
        viewport: VIEWPORTS[viewport],
        deviceScaleFactor: 1,
        colorScheme: scheme,
        reducedMotion: "reduce",
      });
      const page = await context.newPage();
      // A function finds the address with a page of its own; the snapshot then opens it fresh,
      // as a visitor following the link would.
      const address = typeof target === "string" ? BASE + target : await target(page);
      await page.goto("about:blank");
      await page.goto(address);
      await settle(page);
      if (startAt) {
        await page.locator(startAt).evaluate((el) => el.scrollIntoView({ block: "start" }));
      }
      await repaint(page);
      await page.mouse.move(0, 0);
      const path = `${OUT}${name}.png`;
      await page.screenshot({ path, animations: "disabled", caret: "hide" });
      await context.close();
      const { size } = await stat(path);
      console.log(`${name}.png  ${(size / 1024).toFixed(0)} KB`);
      if (size >= MAX_BYTES) oversized.push(name);
    }
  } finally {
    await browser.close();
    server.kill();
  }
  if (oversized.length) {
    throw new Error(`Over ${MAX_BYTES / 1024} KB: ${oversized.join(", ")}`);
  }
}

await main();
