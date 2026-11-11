import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppRoutes } from "../App";
import { mockFetch } from "../test/fixtures";
import { FAILED_RUN, INDEX, RUN } from "../test/runFixture";

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

function stepLabel(trace: HTMLElement): HTMLElement {
  const label = trace.querySelector<HTMLElement>(".replay__label");
  if (!label) throw new Error("no replay label");
  return label;
}

async function openRun() {
  mockFetch({ "runs/run-fixture-1.json": RUN, "runs/run-fixture-failed.json": FAILED_RUN });
  renderAt("/runs/run-fixture-1");
  await screen.findByRole("heading", { level: 1, name: /Review of/ });
}

describe("Run page", () => {
  it("has three labelled panels and the run's facts", async () => {
    await openRun();
    expect(screen.getByRole("region", { name: "Step trace" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "The draft" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Evidence" })).toBeInTheDocument();
    expect(screen.getByText("USD 0.0123")).toBeInTheDocument();
    expect(screen.getByText("1 min 05 s")).toBeInTheDocument();
  });

  it("explains every mark in a legend, each with its text label", async () => {
    await openRun();
    const legend = screen.getByRole("group", { name: "Legend" });
    const terms = within(legend).getAllByRole("term");
    expect(terms.map((t) => t.textContent)).toEqual([
      "✓ verified",
      "✕ contradicted",
      "! unsupported",
      "? unverifiable",
      "! unclaimed",
    ]);
    expect(terms[4]!.querySelector(".unclaimed")).not.toBeNull();
  });

  it("brings a linked claim into view on arrival", async () => {
    const scroll = vi.spyOn(HTMLElement.prototype, "scrollIntoView");
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as unknown as MediaQueryList);
    mockFetch({ "runs/run-fixture-1.json": RUN });
    renderAt("/runs/run-fixture-1?claim=c4");
    const claim = await screen.findByRole("button", { name: /17\.5 in.*contradicted/ });
    expect(claim).toHaveAttribute("aria-pressed", "true");
    expect(scroll.mock.contexts).toContain(claim);
    vi.restoreAllMocks();
  });

  it("marks every claim with its status label, and unclaimed numbers", async () => {
    await openRun();
    const draft = screen.getByRole("region", { name: "The draft" });
    expect(within(draft).getByRole("button", { name: /2\.5.*verified/ })).toBeInTheDocument();
    expect(
      within(draft).getByRole("button", { name: /1,108\.0.*unsupported/ }),
    ).toBeInTheDocument();
    expect(
      within(draft).getByRole("button", { name: /17\.5 in.*contradicted/ }),
    ).toBeInTheDocument();
    expect(within(draft).getByRole("button", { name: /9 h.*unverifiable/ })).toBeInTheDocument();
    expect(within(draft).getByText("12").closest("mark")).toHaveTextContent("unclaimed");
  });

  it("shows a selected claim's check and evidence, reached with the keyboard", async () => {
    await openRun();
    const user = userEvent.setup();
    const target = screen.getByRole("button", { name: /17\.5 in.*contradicted/ });
    let tabs = 0;
    while (document.activeElement !== target && tabs < 60) {
      await user.tab();
      tabs += 1;
    }
    expect(document.activeElement).toBe(target);
    await user.keyboard("{Enter}");
    const evidence = screen.getByRole("region", { name: "Evidence" });
    expect(within(evidence).getByText("c4")).toBeInTheDocument();
    expect(within(evidence).getByText("17.5 in")).toBeInTheDocument();
    expect(within(evidence).getByText("Contradicted")).toBeInTheDocument();
    expect(within(evidence).getByText("26 in")).toBeInTheDocument();
    expect(within(evidence).getByText("stated 17.5, computed 26.0")).toBeInTheDocument();
    expect(within(evidence).getByText("wellbore 9001:T2, section 1")).toBeInTheDocument();
    expect(within(evidence).getByText("ddr:hole-section:9001:T2#1")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /2\.5.*verified/ }));
    expect(
      within(evidence).getByText("Waited on weather. [redacted] on deck."),
    ).toBeInTheDocument();
    expect(within(evidence).getByText("ddr:activity:R1#1")).toBeInTheDocument();
  });

  it("switches between the first draft, the final draft and what the revision removed", async () => {
    await openRun();
    const user = userEvent.setup();
    expect(screen.getByRole("button", { name: /9 h.*unverifiable/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Final draft" }));
    expect(screen.queryByRole("button", { name: /9 h.*unverifiable/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Removed during revision" }));
    expect(screen.getByText("Claims removed (1)")).toBeInTheDocument();
    expect(screen.getByText("9.0")).toBeInTheDocument();
  });

  it("replays the run step by step", async () => {
    await openRun();
    const user = userEvent.setup();
    const trace = screen.getByRole("region", { name: "Step trace" });
    expect(stepLabel(trace)).toHaveTextContent("Step 7 of 7");
    await user.click(within(trace).getByRole("button", { name: "First" }));
    expect(stepLabel(trace)).toHaveTextContent("Step 1 of 7");
    expect(screen.getByText("No draft yet at this step of the replay.")).toBeInTheDocument();
    // The replay buttons work from the keyboard.
    within(trace).getByRole("button", { name: "Next" }).focus();
    await user.keyboard("{Enter}{Enter}");
    expect(stepLabel(trace)).toHaveTextContent("Step 3 of 7");
    expect(screen.getByText(/Not checked yet at this step/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /2\.5.*not checked/ })).toBeInTheDocument();
    fireEvent.change(within(trace).getByRole("slider"), { target: { value: "4" } });
    expect(screen.getByRole("button", { name: /2\.5.*verified/ })).toBeInTheDocument();
    expect(within(trace).getByText("lost_time").closest("li")).not.toHaveAttribute("aria-current");
  });

  it("records a decision on the page only", async () => {
    await openRun();
    const user = userEvent.setup();
    expect(screen.getByText("Demonstration: decisions are not saved.")).toBeInTheDocument();
    const approve = screen.getByRole("button", { name: "Approve" });
    await user.click(approve);
    expect(approve).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Approved on this page only/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reject" }));
    expect(approve).toHaveAttribute("aria-pressed", "false");
  });

  it("shows a failed run with its reason", async () => {
    mockFetch({ "runs/run-fixture-failed.json": FAILED_RUN });
    renderAt("/runs/run-fixture-failed");
    expect(await screen.findByText("Failed: TestTimeout")).toBeInTheDocument();
    expect(screen.getByText(/This run produced no draft/)).toHaveTextContent("TestTimeout");
  });

  it("opens with the claim named in the address selected", async () => {
    mockFetch({ "runs/run-fixture-1.json": RUN });
    renderAt("/runs/run-fixture-1?claim=c3");
    const evidence = await screen.findByRole("region", { name: "Evidence" });
    expect(await within(evidence).findByText("c3")).toBeInTheDocument();
    expect(within(evidence).getByText("The claim cites no evidence id.")).toBeInTheDocument();
  });

  it("says when a run does not exist", async () => {
    mockFetch({});
    renderAt("/runs/no-such-run");
    expect(await screen.findByRole("heading", { name: "Run not found" })).toBeInTheDocument();
  });
});

describe("Runs list", () => {
  it("lists every run with its figures, failed runs included, and filters them", async () => {
    mockFetch({ "runs/index.json": INDEX, "evaluation/r2.json": { release: "r2", runs: [] } });
    renderAt("/runs");
    const table = await screen.findByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(4);
    expect(within(table).getByText("Failed: TestTimeout")).toBeInTheDocument();
    expect(within(table).getAllByText("66.7%")).toHaveLength(2);
    await userEvent.selectOptions(screen.getByLabelText("System"), "primary");
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("Showing 1 of 3 runs.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(within(table).getAllByRole("row")).toHaveLength(4);
  });
});
