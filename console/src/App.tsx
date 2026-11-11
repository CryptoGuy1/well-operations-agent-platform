import { useEffect } from "react";
import { HashRouter, Route, Routes, useLocation } from "react-router";

import { Layout } from "./components/Layout";
import { PAGES } from "./pages";
import { ComingNext } from "./pages/ComingNext";
import { Overview } from "./pages/Overview";
import { RunPage } from "./pages/RunPage";
import { RunsList } from "./pages/RunsList";
import { WellPage } from "./pages/WellPage";
import { WellsList } from "./pages/WellsList";

const SITE = "Well Operations Agent Platform";

const NEXT: Record<string, string> = {
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
    const page = PAGES.find((p) => p.path === pathname || pathname.startsWith(`${p.path}/`));
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
        <Route path="/wells" element={<WellsList />} />
        <Route path="/wells/:slug" element={<WellPage />} />
        <Route path="/runs" element={<RunsList />} />
        <Route path="/runs/:runId" element={<RunPage />} />
        {PAGES.filter((p) => p.path in NEXT).map((p) => (
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
