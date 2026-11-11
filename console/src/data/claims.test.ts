import { FAILED_RUN, RUN } from "../test/runFixture";
import { firstContradictedClaim, scopeText, segmentSentence } from "./claims";

const sentence = RUN.drafts[0]!.document.sections[0]!.sentences[0]!;

describe("segmentSentence", () => {
  it("places each claim on the number or date it states, and marks unclaimed numbers", () => {
    const { segments, unplaced } = segmentSentence(sentence.text, sentence.claims, ["12"]);
    expect(unplaced).toEqual([]);
    expect(segments.map((s) => [s.kind, s.text])).toEqual([
      ["text", "Section 1 lost "],
      ["claim", "2.5"],
      ["text", " h, from "],
      ["claim", "2020-01-02"],
      ["text", ", and drilled "],
      ["claim", "1,108.0"],
      ["text", " m in "],
      ["unclaimed", "12"],
      ["text", " days."],
    ]);
  });

  it("lists a claim whose value is not written in the sentence", () => {
    const s = RUN.drafts[0]!.document.sections[0]!.sentences[1]!;
    const { segments, unplaced } = segmentSentence(s.text, s.claims);
    expect(unplaced.map((c) => c.id)).toEqual(["c4"]);
    expect(segments).toEqual([{ kind: "text", text: s.text }]);
  });

  it("does not place a number inside a wellbore name or a section number twice", () => {
    const claims = [{ ...sentence.claims[0]!, value: 1 }];
    const { segments, unplaced } = segmentSentence("Wellbore 15/9-F-1 had 1 section.", claims);
    expect(unplaced).toEqual([]);
    expect(segments.filter((s) => s.kind === "claim").map((s) => s.text)).toEqual(["1"]);
    expect(segments[0]).toEqual({ kind: "text", text: "Wellbore 15/9-F-1 had " });
  });

  it("finds a quoted text value", () => {
    const quote = { ...sentence.claims[0]!, type: "quote", value: "20 in casing", unit: null };
    const { segments } = segmentSentence('The comment says "20 in casing" here.', [quote]);
    expect(segments.find((s) => s.kind === "claim")?.text).toBe("20 in casing");
  });

  it("describes a claim's scope", () => {
    expect(scopeText(sentence.claims[0]!)).toBe("wellbore 9001:T2, section 1");
  });
});

describe("firstContradictedClaim", () => {
  it("names the first draft's contradicted claim, or null", () => {
    expect(firstContradictedClaim(RUN)).toBe("c4");
    expect(firstContradictedClaim(FAILED_RUN)).toBeNull();
  });
});
