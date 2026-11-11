import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { AppRoutes } from "../App";
import { RELEASE, mockFetch } from "../test/fixtures";

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
  it("offers the run viewer disabled until it exists, and the evaluation", async () => {
    mockFetch({ "evaluation/r2.json": RELEASE });
    renderAt("/");
    const watch = await screen.findByRole("button", { name: /Watch an agent review a well/ });
    expect(watch).toBeDisabled();
    expect(watch).toHaveTextContent("Coming next");
    expect(screen.getByRole("link", { name: "See the evaluation" })).toHaveAttribute(
      "href",
      "/evaluation",
    );
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
    renderAt("/wells");
    expect(screen.getByRole("link", { name: "Skip to content" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Wells" })).toBeInTheDocument();
    expect(screen.getByText("Coming next")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toHaveTextContent("Equinor Open Data Licence");
    expect(screen.getByRole("contentinfo")).toHaveTextContent("NLOD 2.0");
    expect(screen.getByRole("link", { name: "Wells" })).toHaveAttribute("aria-current", "page");
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
