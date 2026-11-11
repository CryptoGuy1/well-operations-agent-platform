import { useEffect } from "react";
import { HashRouter, Route, Routes, useLocation } from "react-router";

import { Layout } from "./components/Layout";
import { PAGES } from "./pages";
import { ComingNext } from "./pages/ComingNext";
import { Overview } from "./pages/Overview";

const SITE = "Well Operations Agent Platform";

const NEXT: Record<string, string> = {
  "/wells":
    "Each development wellbore: hole sections, lost time by section and cause, campaigns, depth against time and data-quality flags.",
  "/runs":
    "Recorded agent runs: every tool call, the first and final drafts claim by claim, the evidence each claim cites, cost and latency.",
  "/evaluation":
    "Every metric of the scored releases, the baseline, and the record of the failed release r1.",
  "/reconciliation":
    "The field's monthly production in the Volve workbook and in Sodir's gross and net series, and the attribution override.",
  "/method":
    "How the warehouse is built and tested, row, null and flag counts, and how claims are checked.",
};

function Title() {
  const { pathname } = useLocation();
  useEffect(() => {
    const page = PAGES.find((p) => p.path === pathname);
    document.title = page && page.path !== "/" ? `${page.label} · ${SITE}` : SITE;
  }, [pathname]);
  return null;
}

export function AppRoutes() {
  return (
    <Layout>
      <Title />
      <Routes>
        <Route path="/" element={<Overview />} />
        {PAGES.filter((p) => p.path !== "/").map((p) => (
          <Route
            key={p.path}
            path={p.path}
            element={<ComingNext title={p.label} summary={NEXT[p.path] ?? ""} />}
          />
        ))}
        <Route
          path="*"
          element={
            <ComingNext title="Page not found" summary="Choose a page from the navigation." />
          }
        />
      </Routes>
    </Layout>
  );
}

export function App() {
  return (
    <HashRouter>
      <AppRoutes />
    </HashRouter>
  );
}
