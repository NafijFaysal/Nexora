import { describe, expect, it } from "vitest";

import { createDraftSignature, getAIErrorMessage, hasStaleResult } from "./decision-state";

describe("decision-state", () => {
  it("detects stale analysis when the draft changes", () => {
    const draft = {
      title: "Laptop",
      description: "",
      options: [{ name: "A" }, { name: "B" }],
      criteria: [{ name: "Price", direction: "cost", weight: "1", unit: "USD" }],
      values: {
        A: { Price: "100" },
        B: { Price: "200" },
      },
      constraints: [],
    };

    const before = createDraftSignature(draft);
    const after = createDraftSignature({
      ...draft,
      options: [{ name: "A" }, { name: "C" }],
      values: {
        A: { Price: "100" },
        C: { Price: "200" },
      },
    });

    expect(hasStaleResult(before, after)).toBe(true);
  });

  it("adds the retry guidance to transient Gemini messages", () => {
    const message = "503 UNAVAILABLE: This model is currently experiencing high demand. Please try again later.";
    expect(getAIErrorMessage(message)).toContain("Manual Setup stays available");
  });
});
