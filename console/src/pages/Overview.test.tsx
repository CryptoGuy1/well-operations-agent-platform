import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppRoutes } from "../App";
import { RELEASE, mockFetch } from "../test/fixtures";
import { INDEX, RUN } from "../test/runFixture";

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

describe("Overview", () => {
  it("states the release result from the bundle", async () => {
    const fetchMock = mockFetch({ "evaluation/r2.json": RELEASE });
    renderAt("/");
    const statement = await screen.findByText(/wells the agent had never seen/);
    expect(statement).toHaveTextContent(
      "On two wells the agent had never seen: about 769 checked claims per review, 1 contradicted in 2,307, no answer-key fact wrong, 64% of key facts covered in the first draft.",
    );
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/data\/evaluation\/r2\.json$/));
  });

  it("gives each rate with its status label, and links to the evaluation", async () => {
    mockFetch({ "evaluation/r2.json": RELEASE });
    renderAt("/");
    expect(await screen.findByText("Unsupported")).toBeInTheDocument();
    expect(screen.getByText("Unverifiable")).toBeInTheDocument();
    expect(screen.getByText("Unclaimed")).toBeInTheDocument();
    expect(screen.getByText("6.7%")).toBeInTheDocument();
    expect(screen.getByText("1.0%")).toBeInTheDocument();
    expect(screen.getByText("2.7%")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "See the evaluation" })).toHaveAttribute(
      "href",
      "/evaluation",
    );
  });

  it("reports answer-key facts stated wrongly", async () => {
    const runs = RELEASE.runs.map((r) =>
      r.first_draft
        ? {
            ...r,
            first_draft: { ...r.first_draft, coverage: { ...r.first_draft.coverage, wrong: 1 } },
          }
        : r,
    );
    mockFetch({ "evaluation/r2.json": { ...RELEASE, runs } });
    renderAt("/");
    expect(await screen.findByText(/wells the agent had never seen/)).toHaveTextContent(
      "3 answer-key facts wrong",
    );
  });

  it("says so when the bundle cannot be read", async () => {
    mockFetch({});
    renderAt("/");
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 404");
  });

  it("shows the pipeline in order", () => {
    mockFetch({ "evaluation/r2.json": RELEASE });
    renderAt("/");
    const steps = screen.getAllByRole("listitem").filter((li) => li.closest(".pipeline"));
    expect(steps.map((s) => s.querySelector(".pipeline__name")?.firstChild?.textContent)).toEqual([
      "Data sources",
      "Warehouse",
      "Connectors",
      "Agent",
      "Checker",
      "Reviewer",
    ]);
  });
});

describe("Overview actions", () => {
  it("links to the latest completed review of 15/9-F-11 T2, and to the evaluation", async () => {
    const index = INDEX.map((e) => ({ ...e, wellbore_name: "15/9-F-11 T2" }));
    mockFetch({ "evaluation/r2.json": RELEASE, "runs/index.json": index });
    renderAt("/");
    const watch = await screen.findByRole("link", { name: "Watch an agent review a well" });
    expect(watch).toHaveAttribute("href", "/runs/run-fixture-r9");
    expect(screen.getByRole("link", { name: "See the evaluation" })).toHaveAttribute(
      "href",
      "/evaluation",
    );
  });

  it("opens the release run with a contradicted claim, with that claim selected", async () => {
    const index = INDEX.map((e) => (e.source === "r9" ? { ...e, source: "r2" } : e));
    mockFetch({
      "evaluation/r2.json": RELEASE,
      "runs/index.json": index,
      "runs/run-fixture-1.json": RUN,
    });
    renderAt("/");
    const link = await screen.findByRole("link", { name: "See the checker catch an error" });
    expect(link).toHaveAttribute("href", "/runs/run-fixture-r9?claim=c4");
  });

  it("has no checker button when the release has no contradicted claim", async () => {
    // The fixture's release run is in r9, not the headline release.
    const index = INDEX.map((e) => ({ ...e, wellbore_name: "15/9-F-11 T2" }));
    mockFetch({ "evaluation/r2.json": RELEASE, "runs/index.json": index });
    renderAt("/");
    await screen.findByRole("link", { name: "Watch an agent review a well" });
    expect(screen.queryByRole("link", { name: "See the checker catch an error" })).toBeNull();
  });

  it("marks the checker as the deterministic step", () => {
    mockFetch({ "evaluation/r2.json": RELEASE });
    renderAt("/");
    expect(screen.getByText("deterministic").closest("li")).toHaveClass("pipeline__step--key");
  });
});

describe("Layout", () => {
  it("has a skip link, the attributions and a placeholder for later pages", () => {
    mockFetch({ "evaluation/r2.json": RELEASE });
    renderAt("/evaluation");
    expect(screen.getByRole("link", { name: "Skip to content" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Evaluation" })).toBeInTheDocument();
    expect(screen.getByText("Coming next")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toHaveTextContent("Equinor Open Data Licence");
    expect(screen.getByRole("contentinfo")).toHaveTextContent("NLOD 2.0");
    expect(screen.getByRole("link", { name: "Evaluation" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    // The author, under the title in the navigation and at the top of the footer.
    for (const where of [screen.getByRole("banner"), screen.getByRole("contentinfo")]) {
      expect(within(where).getByRole("link", { name: "Benjamin Nweke" })).toHaveAttribute(
        "href",
        "https://github.com/CryptoGuy1",
      );
      expect(within(where).getByRole("link", { name: "Source on GitHub" })).toHaveAttribute(
        "href",
        "https://github.com/CryptoGuy1/well-operations-agent-platform",
      );
    }
  });

  it("opens and closes the menu", async () => {
    mockFetch({ "evaluation/r2.json": RELEASE });
    renderAt("/");
    const button = screen.getByRole("button", { name: "Menu" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(button);
    expect(screen.getByRole("button", { name: "Close" })).toHaveAttribute("aria-expanded", "true");
  });
});
