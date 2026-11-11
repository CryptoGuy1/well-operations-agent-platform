import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppRoutes } from "../App";
import { mockFetch } from "../test/fixtures";
import { INDEX } from "../test/runFixture";
import { WELL, WELLS } from "../test/wellFixture";

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

const RUNS = INDEX.map((e) => ({ ...e, wellbore_name: "XX/1-A-1 T2" }));

function bundle() {
  return mockFetch({
    "wells.json": WELLS,
    "wells/9001-T2.json": WELL,
    "runs/index.json": RUNS,
  });
}

describe("Wells list", () => {
  it("lists every wellbore with its role; held-out ones link to their runs only", async () => {
    bundle();
    renderAt("/wells");
    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    // Natural order: A-1 T2, A-2, A-10.
    expect(rows.map((r) => within(r).getByRole("rowheader").textContent)).toEqual([
      "XX/1-A-1 T29001:T2",
      "XX/1-A-2",
      "XX/1-A-109003",
    ]);
    expect(within(rows[0]!).getByRole("link", { name: "XX/1-A-1 T2" })).toHaveAttribute(
      "href",
      "/wells/9001-T2",
    );
    expect(rows[0]).toHaveTextContent("2019-12-20 to 2020-03-02");
    expect(rows[0]).toHaveTextContent("2 flags");
    const held = rows[1]!;
    expect(held).toHaveTextContent("Held out");
    expect(within(held).getAllByRole("link")).toHaveLength(1);
    expect(within(held).getByRole("link")).toHaveAttribute("href", "/runs?wellbore=XX%2F1-A-2");
    expect(rows[2]).toHaveTextContent("Outside the evaluation");
  });
});

describe("Well page", () => {
  async function openWell() {
    const fetchMock = bundle();
    renderAt("/wells/9001-T2");
    await screen.findByRole("heading", { level: 2, name: "Drilling history" });
    return fetchMock;
  }

  it("gives the header facts, with the tiers apart", async () => {
    await openWell();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("XX/1-A-1 T2");
    expect(screen.getByText("Primary lost time").nextSibling).toHaveTextContent("3.5 h");
    expect(screen.getByText("Possible lost time").nextSibling).toHaveTextContent("2 h");
    expect(screen.getByText("Deepest reported MD").nextSibling).toHaveTextContent("1,000 m");
  });

  it("draws the depth chart with a summary, a legend and its data as tables", async () => {
    await openWell();
    const chart = screen.getByRole("img", { name: /Depth against time, XX\/1-A-1 T2/ });
    expect(chart).toHaveAccessibleDescription(/5 reports in 2 campaigns/);
    // One line per campaign; the report before spud is not plotted.
    expect(chart.querySelectorAll(".chart__line")).toHaveLength(2);
    expect(chart.querySelectorAll(".chart__dot")).toHaveLength(4);
    expect(chart.querySelectorAll(".chart__dot--open")).toHaveLength(1);
    // Hole sections as bands, lost time by day in two styles.
    expect(chart.querySelectorAll(".chart__band")).toHaveLength(2);
    expect(chart.querySelectorAll(".chart__lost--primary")).toHaveLength(2);
    expect(chart.querySelectorAll(".chart__lost--possible")).toHaveLength(1);
    expect(screen.getAllByRole("list", { name: "Legend" })[0]).toHaveTextContent(
      "Possible lost time (hatched)",
    );
    await userEvent.click(screen.getByText("Show the chart's data as tables"));
    const depth = screen.getByRole("table", { name: "Depth per report" });
    expect(within(depth).getAllByRole("row")).toHaveLength(6);
    expect(depth).toHaveTextContent("not recorded");
    const days = screen.getByRole("table", { name: "Lost time by day, by tier" });
    expect(within(days).getAllByRole("row")[1]).toHaveTextContent("2020-01-012.5 h–");
  });

  it("lists hole sections with an unknown size and a rate's null reason", async () => {
    await openWell();
    const table = screen.getByRole("table", { name: "Hole sections of XX/1-A-1 T2" });
    const [first, second] = within(table).getAllByRole("row").slice(1);
    expect(first).toHaveTextContent("26 in");
    expect(first).toHaveTextContent("50.00");
    expect(first).toHaveTextContent("990 m");
    expect(second).toHaveTextContent("unknown");
    expect(second).toHaveTextContent("none: no new hole drilled");
  });

  it("charts lost time per tier by cause, with tables and no combined total", async () => {
    await openWell();
    const primary = screen.getByRole("img", { name: "Primary lost time by cause" });
    expect(primary).toHaveAccessibleDescription(
      /3\.5 h in 2 causes; the largest is interruption -- wait/,
    );
    expect(screen.getByRole("img", { name: "Possible lost time by cause" })).toBeInTheDocument();
    const lost = screen.getByRole("region", { name: "Lost time by tier and cause" });
    expect(within(lost).queryByText(/drilling -- drill/)).toBeNull(); // not lost time
    expect(screen.getByRole("table", { name: "Primary lost time by cause" })).toHaveTextContent(
      "Total, primary only3.5 h2",
    );
    expect(screen.queryByText("5.5 h")).toBeNull();
  });

  it("explains the flags and links to the well's runs", async () => {
    await openWell();
    expect(
      screen.getByRole("heading", { name: /Dated before the spud date in Sodir/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/placeholder for a missing value/)).toBeInTheDocument();
    const runs = await screen.findByRole("link", { name: "run-fixture-r9" });
    expect(runs).toHaveAttribute("href", "/runs/run-fixture-r9");
    expect(
      screen.getByRole("link", { name: "run-fixture-failed" }).closest("li"),
    ).toHaveTextContent("Failed: TestTimeout");
  });

  it("never loads a held-out wellbore's detail", async () => {
    const fetchMock = bundle();
    renderAt("/wells/9002");
    expect(await screen.findByRole("link", { name: "See its evaluation runs" })).toHaveAttribute(
      "href",
      "/runs?wellbore=XX%2F1-A-2",
    );
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringMatching(/wells\/9002/));
  });

  it("says so for an unknown well", async () => {
    bundle();
    renderAt("/wells/0000");
    expect(await screen.findByRole("heading", { name: "Well not found" })).toBeInTheDocument();
  });
});

describe("Runs list from a well", () => {
  it("reads the wellbore filter from the address", async () => {
    mockFetch({ "runs/index.json": INDEX });
    renderAt("/runs?wellbore=XX%2F1-A-2");
    expect(await screen.findByText("Showing 1 of 3 runs.")).toBeInTheDocument();
    expect(screen.getByLabelText("Wellbore")).toHaveValue("XX/1-A-2");
    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByText("Showing 3 of 3 runs.")).toBeInTheDocument();
  });
});
