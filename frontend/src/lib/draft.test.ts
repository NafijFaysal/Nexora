import { describe, expect, it } from "vitest";

import { buildPayload, hydrateDraftFromPayload, mergeAIIntoDraft, type Draft } from "./draft";

describe("draft flow safety", () => {
  it("preserves manual values and omits blank AI fields without deleting data", () => {
    const draft: Draft = {
      title: "Laptop",
      description: "Existing plan",
      options: [
        { id: "o1", name: "Option A" },
        { id: "o2", name: "Option B" },
      ],
      criteria: [
        { id: "c1", name: "Price", direction: "cost", weight: "1", unit: "USD" },
      ],
      values: {
        o1: { c1: "1500" },
        o2: { c1: "1600" },
      },
      constraints: [
        { id: "k1", criterionId: "c1", operator: "<=", threshold: "1800" },
      ],
    };

    const merged = mergeAIIntoDraft(draft, {
      title: "Laptop",
      description: "",
      options: ["Option A", "Option B"],
      criteria: [{ name: "Performance", direction: "benefit", weight: null, unit: "score" }],
      values: {
        "Option A": { Performance: 90 },
        "Option B": { Performance: 80 },
      },
      constraints: [{ criterion: "Price", operator: "<=", threshold: 1800 }],
      unknowns: ["budget"],
      notes: "",
    });

    expect(merged.options).toHaveLength(2);
    expect(merged.values.o1.c1).toBe("1500");
    expect(merged.values.o2.c1).toBe("1600");
    expect(merged.criteria.some((criterion) => criterion.name === "Performance")).toBe(true);
    expect(merged.criteria.some((criterion) => criterion.name === "Price")).toBe(true);
    expect(merged.constraints.some((constraint) => constraint.criterionId === "c1")).toBe(true);
  });

  it("keeps unmatched AI constraints visible instead of attaching them to the first criterion", () => {
    const draft: Draft = {
      title: "Plan",
      description: "",
      options: [
        { id: "o1", name: "A" },
        { id: "o2", name: "B" },
      ],
      criteria: [
        { id: "c1", name: "Cost", direction: "cost", weight: "1", unit: "USD" },
        { id: "c2", name: "Quality", direction: "benefit", weight: "2", unit: "score" },
      ],
      values: {
        o1: { c1: "100", c2: "90" },
        o2: { c1: "120", c2: "80" },
      },
      constraints: [],
    };

    const merged = mergeAIIntoDraft(draft, {
      title: "Plan",
      description: "",
      options: ["A", "B"],
      criteria: [{ name: "Cost", direction: "cost", weight: 1, unit: "USD" }],
      values: { A: { Cost: 100 }, B: { Cost: 120 } },
      constraints: [{ criterion: "Delivery", operator: "<=", threshold: 7 }],
      unknowns: [],
      notes: "",
    });

    expect(merged.criteria.some((criterion) => criterion.name === "Delivery")).toBe(true);
    expect(
      merged.constraints.some(
        (constraint) =>
          constraint.criterionId === merged.criteria.find((criterion) => criterion.name === "Delivery")?.id,
      ),
    ).toBe(true);
  });

  it("does not silently set missing AI weights to 1 or drop data during hydration", () => {
    const hydrated = hydrateDraftFromPayload({
      title: "Saved decision",
      description: "",
      options: ["A", "B"],
      criteria: [
        { name: "Price", direction: "cost", weight: 5, unit: "USD" },
        { name: "Quality", direction: "benefit", weight: 3, unit: "score" },
      ],
      values: {
        A: { Price: 100, Quality: 9 },
        B: { Price: 120, Quality: 7 },
      },
      constraints: [{ criterion: "Price", operator: "<=", threshold: 150 }],
    });

    expect(hydrated.criteria[0].weight).toBe("5");
    expect(hydrated.values[hydrated.options[0].id][hydrated.criteria[0].id]).toBe("100");
    expect(hydrated.constraints[0].criterionId).toBe(hydrated.criteria[0].id);
  });

  it("rejects incomplete payloads and keeps empty weights invalid", () => {
    const result = buildPayload({
      title: "",
      description: "",
      options: [{ id: "o1", name: "A" }, { id: "o2", name: "B" }],
      criteria: [{ id: "c1", name: "Price", direction: "cost", weight: "", unit: "USD" }],
      values: {
        o1: { c1: "10" },
        o2: { c1: "20" },
      },
      constraints: [],
    });

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("Expected payload validation to fail.");
    }
    expect(result.errors.join(" ")).toContain("weight");
  });
});
