"use client";

import { useEffect, useState } from "react";
import { chatWithAI, getAIStatus } from "@/lib/ai";
import {
  analyzeDecision,
  deleteJournalEntry,
  listJournalEntries,
  listTemplates,
  saveJournalEntry,
  updateJournalEntry,
} from "@/lib/api";
import {
  addConstraint,
  addCriterion,
  addOption,
  applyTemplate,
  buildPayload,
  emptyDraft,
  exampleDraft,
  hydrateDraftFromPayload,
  mergeAIIntoDraft,
  removeConstraint,
  removeCriterion,
  removeOption,
  renameOption,
  setValue,
  updateConstraint,
  updateCriterion,
  type Draft,
} from "@/lib/draft";
import { createDraftSignature, createDraftSignatureFromPayload, getAIErrorMessage, hasStaleResult } from "@/lib/decision-state";
import type { AIChatMessage, AIStatus, AIDecisionDraft, AnalysisResponse, DecisionPayload, JournalEntry, Template } from "@/lib/types";

export default function Home() {
  const [mode, setMode] = useState<"manual" | "ai">("manual");
  const [draft, setDraft] = useState(emptyDraft());
  const [templates, setTemplates] = useState<Template[]>([]);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [resultDraftSignature, setResultDraftSignature] = useState<string>("");
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([]);
  const [selectedJournalId, setSelectedJournalId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [journalError, setJournalError] = useState("");
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [chatMessages, setChatMessages] = useState<AIChatMessage[]>([
    {
      role: "assistant",
      content:
        "AI Assistant can help you shape a decision draft from your own situation. Tell me what decision you need to make, what options you know about, and what matters most. I will ask only for missing facts and keep every suggestion reviewable before it becomes a final decision.",
    },
  ]);
  const [aiInput, setAiInput] = useState("");
  const [lastAiPrompt, setLastAiPrompt] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [aiDraft, setAiDraft] = useState<AIDecisionDraft | null>(null);

  const draftSignature = createDraftSignature({
    title: draft.title,
    description: draft.description,
    options: draft.options.map((option) => ({ name: option.name })),
    criteria: draft.criteria.map((criterion) => ({
      name: criterion.name,
      direction: criterion.direction,
      weight: criterion.weight,
      unit: criterion.unit,
    })),
    values: draft.values,
    constraints: draft.constraints.map((constraint) => ({
      criterionId: constraint.criterionId,
      operator: constraint.operator,
      threshold: constraint.threshold,
    })),
  });

  const staleResultNotice =
    result && resultDraftSignature && hasStaleResult(resultDraftSignature, draftSignature)
      ? "This result is based on an earlier version of the draft. Analyze again to refresh it."
      : "";

  const handleRetryAI = async () => {
    if (!lastAiPrompt) return;
    await handleSendAI(lastAiPrompt);
  };

  const initializeClientState = async () => {
    try {
      const [items, journalItems, status] = await Promise.all([
        listTemplates(),
        listJournalEntries(),
        getAIStatus().catch(() => ({
          available: false,
          provider: "not-configured",
          requires_configuration: true,
          message:
            "AI Assistant is unavailable. Manual Setup remains fully available without a configured AI provider.",
        })),
      ]);

      setTemplates(items);
      if (items.length > 0) {
        setDraft((current) => applyTemplate(current, items[0]));
      }

      setJournalEntries(journalItems);
      setAIStatus(status);
    } catch {
      setTemplates([]);
      setJournalEntries([]);
      setAIStatus({
        available: false,
        provider: "not-configured",
        requires_configuration: true,
        message:
          "AI Assistant is unavailable. Manual Setup remains fully available without a configured AI provider.",
      });
    }
  };

  useEffect(() => {
    // This is the app's intentional one-time bootstrap fetch for starter data.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void initializeClientState();
  }, []);

  const loadJournal = async () => {
    try {
      const items = await listJournalEntries();
      setJournalEntries(items);
    } catch {
      setJournalEntries([]);
    }
  };

  const clearStaleAnalysis = () => {
    setResult(null);
    setResultDraftSignature("");
  };

  const markResultCurrent = (analysis: AnalysisResponse) => {
    setResult(analysis);
    setResultDraftSignature(draftSignature);
  };

  const handleAnalyze = async () => {
    const built = buildPayload(draft);
    if (!built.ok) {
      setError(built.errors.join(" "));
      setResult(null);
      setResultDraftSignature("");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const analysis = await analyzeDecision(built.payload);
      markResultCurrent(analysis);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Analysis failed.";
      setError(message);
      setResult(null);
      setResultDraftSignature("");
    } finally {
      setLoading(false);
    }
  };

  const beginNewDraft = (nextDraft: Draft) => {
    setSelectedJournalId(null);
    setDraft(nextDraft);
  };

  const handleSave = async () => {
    const built = buildPayload(draft);
    if (!built.ok) {
      setJournalError(built.errors.join(" "));
      return;
    }

    const currentResult = result && resultDraftSignature === draftSignature ? result : null;

    try {
      setSaving(true);
      setJournalError("");
      const payload: Record<string, unknown> = {
        id: selectedJournalId ?? undefined,
        title: draft.title.trim() || "Untitled decision",
        description: draft.description.trim(),
        decision: built.payload as DecisionPayload,
        analysis: currentResult,
        notes: "",
      };

      const savedEntry = selectedJournalId
        ? await updateJournalEntry(selectedJournalId, payload)
        : await saveJournalEntry(payload);
      setSelectedJournalId(savedEntry.id);
      await loadJournal();
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Could not save the decision.";
      setJournalError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteJournal = async (id: string) => {
    try {
      await deleteJournalEntry(id);
      setJournalEntries((current) => current.filter((entry) => entry.id !== id));
      if (selectedJournalId === id) {
        setSelectedJournalId(null);
      }
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Could not delete the saved decision.";
      setJournalError(message);
    }
  };

  const handleOpenJournal = (entry: JournalEntry) => {
    const hydrated = hydrateDraftFromPayload(entry.decision);
    setSelectedJournalId(entry.id);
    setDraft(hydrated);
    setResult(entry.analysis ?? null);
    setResultDraftSignature(createDraftSignatureFromPayload(entry.decision));
    setJournalError("");
  };

  const renderValueCell = (optionId: string, criterionId: string) => {
    const value = draft.values[optionId]?.[criterionId] ?? "";
    return (
      <input
        value={value}
        onChange={(event) => setDraft((current) => setValue(current, optionId, criterionId, event.target.value))}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
        placeholder="0"
      />
    );
  };

  const handleSendAI = async (promptOverride?: string) => {
    const prompt = (promptOverride ?? aiInput).trim();
    if (!prompt) return;
    if (aiLoading) return;
    if (!aiStatus?.available) {
      setAiError(aiStatus?.message ?? "AI Assistant is unavailable.");
      return;
    }

    const userMessage: AIChatMessage = { role: "user", content: prompt };
    const nextMessages = [...chatMessages, userMessage];
    setChatMessages(nextMessages);
    setAiInput("");
    setLastAiPrompt(prompt);
    setAiLoading(true);
    setAiError("");

    try {
      const response = await chatWithAI(nextMessages);
      const assistantMessage: AIChatMessage = { role: "assistant", content: response.message };
      setChatMessages([...nextMessages, assistantMessage]);
      setAiDraft(response.draft ?? null);
      setLastAiPrompt("");
      if (!response.draft) {
        setAiError("The AI returned no structured draft to review.");
      }
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "AI request failed.";
      const uiMessage = getAIErrorMessage(message);
      setAiError(uiMessage);
      setChatMessages([...nextMessages, { role: "assistant", content: message }]);
    } finally {
      setAiLoading(false);
    }
  };

  const handleAcceptAIDraft = () => {
    if (!aiDraft) {
      return;
    }
    setSelectedJournalId(null);
    setDraft((current) => mergeAIIntoDraft(current, aiDraft));
    setMode("manual");
    clearStaleAnalysis();
    setError("");
    setAiError("");
    setAiDraft(null);
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-8 rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950/30">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">Decision Intelligence Platform</p>
              <h1 className="mt-3 text-3xl font-bold tracking-tight text-white md:text-5xl">What If?</h1>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setMode("manual")}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  mode === "manual"
                    ? "bg-cyan-400 text-slate-950"
                    : "border border-slate-700 bg-slate-950 text-slate-200 hover:border-slate-500"
                }`}
              >
                Manual Setup
              </button>
              <button
                type="button"
                onClick={() => setMode("ai")}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  mode === "ai"
                    ? "bg-violet-400 text-slate-950"
                    : "border border-violet-400/40 bg-violet-500/10 text-violet-100 hover:bg-violet-500/20"
                }`}
              >
                AI Assistant
              </button>
              <button
                type="button"
                onClick={() => beginNewDraft(emptyDraft())}
                className="rounded-full border border-slate-700 bg-slate-950 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500"
              >
                New blank
              </button>
              <button
                type="button"
                onClick={() => beginNewDraft(exampleDraft())}
                className="rounded-full border border-cyan-400/50 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20"
              >
                Load example
              </button>
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={loading}
                className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Analyzing..." : "Analyze decision"}
              </button>
            </div>
          </div>
        </header>

        <div className="mb-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="text-sm text-slate-400">Options</div>
            <div className="mt-2 text-3xl font-semibold text-white">{draft.options.length}</div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="text-sm text-slate-400">Criteria</div>
            <div className="mt-2 text-3xl font-semibold text-white">{draft.criteria.length}</div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="text-sm text-slate-400">Saved</div>
            <div className="mt-2 text-3xl font-semibold text-white">{journalEntries.length}</div>
          </div>
        </div>

        {error ? (
          <div className="mb-8 rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        {mode === "ai" ? (
          <section className="mb-8 rounded-2xl border border-violet-500/30 bg-slate-900 p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-white">AI Assistant</h2>
              <span className="rounded-full border border-violet-400/40 bg-violet-500/10 px-2.5 py-1 text-xs text-violet-200">
                {aiStatus?.available ? "Available" : "Unavailable"}
              </span>
            </div>

            <div className="mb-4 rounded-2xl border border-violet-500/30 bg-violet-500/5 p-4 text-sm text-violet-100">
              <p className="font-medium">How to describe your decision</p>
              <p className="mt-2 leading-6 text-violet-50/90">
                Tell the assistant what decision you need to make, the available options if you know them, what matters most to you,
                your budget, deadlines, limitations, and any known measurements. Include what you do not know yet.
                You do not need to fill out a rigid form first.
              </p>
              <p className="mt-3 text-violet-100/80">
                Example: “I need to choose a laptop for university. I’m comparing Lenovo, MacBook Air, and a budget Windows option. I care most
                about performance, cost, battery life, and reliability. My budget is about $1,200 and I need it before semester starts.”
              </p>
            </div>

            {aiStatus && !aiStatus.available ? (
              <div className="mb-4 rounded-xl border border-amber-400/40 bg-amber-500/10 p-3 text-sm text-amber-100">
                {aiStatus.message}
              </div>
            ) : null}

            <div className="mb-4 space-y-3 rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              {chatMessages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`rounded-xl border p-3 text-sm ${
                    message.role === "assistant"
                      ? "border-slate-700 bg-slate-900 text-slate-100"
                      : "border-cyan-500/30 bg-cyan-500/5 text-cyan-50"
                  }`}
                >
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                    {message.role === "assistant" ? "Assistant" : "You"}
                  </div>
                  <div className="whitespace-pre-wrap leading-6">{message.content}</div>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3 md:flex-row">
              <textarea
                value={aiInput}
                onChange={(event) => setAiInput(event.target.value)}
                rows={3}
                placeholder="Describe the decision, your options, constraints, and what matters most..."
                disabled={!aiStatus?.available || aiLoading}
                className="min-h-[96px] flex-1 rounded-2xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-violet-400 disabled:cursor-not-allowed disabled:opacity-60"
              />
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={() => handleSendAI()}
                  disabled={!aiStatus?.available || aiLoading || !aiInput.trim()}
                  className="rounded-2xl bg-violet-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {aiLoading ? "Thinking..." : "Send"}
                </button>
              </div>
            </div>

            {aiError ? (
              <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
                <div>{aiError}</div>
                {lastAiPrompt ? (
                  <button
                    type="button"
                    onClick={handleRetryAI}
                    disabled={aiLoading}
                    className="mt-3 rounded-full border border-red-400/60 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-100 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Retry
                  </button>
                ) : null}
              </div>
            ) : null}

            {aiDraft ? (
              <div className="mt-6 rounded-2xl border border-violet-500/30 bg-violet-500/5 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="text-base font-semibold text-white">Draft preview</h3>
                  <span className="rounded-full border border-violet-400/40 bg-violet-500/10 px-2 py-1 text-[10px] font-medium uppercase tracking-[0.2em] text-violet-200">
                    Review required
                  </span>
                </div>
                <div className="mb-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Title</div>
                    <div className="mt-1 text-sm text-white">{aiDraft.title || "Untitled"}</div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Options</div>
                    <div className="mt-1 text-sm text-white">{aiDraft.options.join(", ") || "None"}</div>
                  </div>
                </div>
                <div className="mb-3">
                  <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Criteria</div>
                  <ul className="mt-2 space-y-2 text-sm text-slate-200">
                    {aiDraft.criteria.map((criterion) => (
                      <li key={`${criterion.name}-${criterion.direction}`} className="rounded-lg border border-slate-700 bg-slate-950/60 p-2">
                        {criterion.name} · {criterion.direction === "benefit" ? "higher is better" : "lower is better"} · weight {criterion.weight ?? "unknown"}
                        {criterion.unit ? ` · ${criterion.unit}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
                {aiDraft.unknowns.length > 0 ? (
                  <div className="mb-3">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Unknown or missing</div>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-100">
                      {aiDraft.unknowns.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </div>
                ) : null}
                {aiDraft.notes ? (
                  <div className="mb-4 rounded-xl border border-slate-700 bg-slate-950/60 p-3 text-sm text-slate-200">
                    {aiDraft.notes}
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={handleAcceptAIDraft}
                    className="rounded-full bg-emerald-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300"
                  >
                    Accept draft
                  </button>
                  <button
                    type="button"
                    onClick={() => setAiDraft(null)}
                    className="rounded-full border border-slate-700 bg-slate-950 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500"
                  >
                    Reject draft
                  </button>
                </div>
              </div>
            ) : null}
          </section>
        ) : null}

        <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="mb-4 text-lg font-semibold text-white">Decision Studio</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm text-slate-300">
              Title
              <input
                value={draft.title}
                onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none transition focus:border-cyan-400"
                placeholder="Which laptop should I buy?"
              />
            </label>
            <label className="block text-sm text-slate-300">
              Description
              <input
                value={draft.description}
                onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none transition focus:border-cyan-400"
                placeholder="Decision context and constraints"
              />
            </label>
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">Templates</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {templates.map((template) => (
              <button
                key={template.id}
                type="button"
                onClick={() => {
                  setSelectedJournalId(null);
                  setDraft((current) => applyTemplate(current, template));
                }}
                className="rounded-full border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 transition hover:border-cyan-400 hover:text-cyan-200"
              >
                {template.name}
              </button>
            ))}
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">Options</h2>
            <button
              type="button"
              onClick={() => setDraft((current) => addOption(current))}
              className="rounded-full bg-slate-800 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              Add option
            </button>
          </div>
          <div className="space-y-3">
            {draft.options.map((option) => (
              <div key={option.id} className="flex gap-3">
                <input
                  value={option.name}
                  onChange={(event) =>
                    setDraft((current) => renameOption(current, option.id, event.target.value))
                  }
                  className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none transition focus:border-cyan-400"
                />
                <button
                  type="button"
                  onClick={() => setDraft((current) => removeOption(current, option.id))}
                  disabled={draft.options.length <= 2}
                  className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">Criteria</h2>
            <button
              type="button"
              onClick={() => setDraft((current) => addCriterion(current))}
              className="rounded-full bg-slate-800 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              Add criterion
            </button>
          </div>
          <div className="space-y-4">
            {draft.criteria.map((criterion) => (
              <div key={criterion.id} className="grid gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-3 md:grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr_auto]">
                <input
                  value={criterion.name}
                  onChange={(event) =>
                    setDraft((current) =>
                      updateCriterion(current, criterion.id, { name: event.target.value })
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                  placeholder="Criterion name"
                />
                <select
                  value={criterion.direction}
                  onChange={(event) =>
                    setDraft((current) =>
                      updateCriterion(current, criterion.id, {
                        direction: event.target.value as "benefit" | "cost",
                      })
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                >
                  <option value="benefit">Higher is better</option>
                  <option value="cost">Lower is better</option>
                </select>
                <input
                  value={criterion.weight}
                  onChange={(event) =>
                    setDraft((current) =>
                      updateCriterion(current, criterion.id, { weight: event.target.value })
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                  placeholder="Weight"
                />
                <input
                  value={criterion.unit}
                  onChange={(event) =>
                    setDraft((current) =>
                      updateCriterion(current, criterion.id, { unit: event.target.value })
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                  placeholder="Unit"
                />
                <button
                  type="button"
                  onClick={() => setDraft((current) => removeCriterion(current, criterion.id))}
                  disabled={draft.criteria.length <= 1}
                  className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">Hard constraints</h2>
            <button
              type="button"
              onClick={() => setDraft((current) => addConstraint(current))}
              disabled={draft.criteria.length === 0}
              className="rounded-full bg-slate-800 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Add limit
            </button>
          </div>
          <div className="space-y-3">
            {draft.constraints.length === 0 ? (
              <div className="text-sm text-slate-400">No hard limits yet.</div>
            ) : null}
            {draft.constraints.map((constraint) => (
              <div key={constraint.id} className="grid gap-3 md:grid-cols-[1.4fr_0.7fr_1fr_auto]">
                <select
                  value={constraint.criterionId}
                  onChange={(event) =>
                    setDraft((current) =>
                      updateConstraint(current, constraint.id, { criterionId: event.target.value })
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                >
                  {draft.criteria.map((criterion) => (
                    <option key={criterion.id} value={criterion.id}>
                      {criterion.name || "Unnamed criterion"}
                    </option>
                  ))}
                </select>
                <select
                  value={constraint.operator}
                  onChange={(event) =>
                    setDraft((current) =>
                      updateConstraint(current, constraint.id, {
                        operator: event.target.value as "<=" | ">=",
                      })
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                >
                  <option value="<=">≤</option>
                  <option value=">=">≥</option>
                </select>
                <input
                  value={constraint.threshold}
                  onChange={(event) =>
                    setDraft((current) =>
                      updateConstraint(current, constraint.id, { threshold: event.target.value })
                    )
                  }
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
                  placeholder="Threshold"
                />
                <button
                  type="button"
                  onClick={() => setDraft((current) => removeConstraint(current, constraint.id))}
                  className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="mb-4 text-lg font-semibold text-white">Values</h2>
          {draft.criteria.length === 0 || draft.options.length === 0 ? (
            <div className="text-sm text-slate-400">Add at least one option and one criterion to start entering values.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-2 text-left text-sm">
                <thead>
                  <tr>
                    <th className="min-w-28 pb-2 text-slate-400">Option</th>
                    {draft.criteria.map((criterion) => (
                      <th key={criterion.id} className="min-w-28 pb-2 text-slate-400">
                        {criterion.name || "Unnamed criterion"}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {draft.options.map((option) => (
                    <tr key={option.id}>
                      <td className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-slate-100">
                        {option.name || "Unnamed option"}
                      </td>
                      {draft.criteria.map((criterion) => (
                        <td key={`${option.id}-${criterion.id}`} className="rounded-xl border border-slate-800 bg-slate-950 px-2 py-2">
                          {renderValueCell(option.id, criterion.id)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={loading}
              className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Analyzing..." : "Analyze decision"}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded-full border border-emerald-400/50 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-200 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving..." : selectedJournalId ? "Update saved decision" : "Save to journal"}
            </button>
          </div>
          {journalError ? (
            <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
              {journalError}
            </div>
          ) : null}
        </section>

        {result ? (
          <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-white">Results</h2>
              {result.has_tie_for_first ? (
                <span className="rounded-full border border-amber-400/40 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-200">
                  Tie for first
                </span>
              ) : null}
            </div>
            {staleResultNotice ? (
              <div className="mb-4 rounded-xl border border-amber-400/40 bg-amber-500/10 p-3 text-sm text-amber-100">
                {staleResultNotice}
              </div>
            ) : null}
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-slate-400">
                  <tr>
                    <th className="pb-3 pr-4 font-medium">Rank</th>
                    <th className="pb-3 pr-4 font-medium">Option</th>
                    <th className="pb-3 pr-4 font-medium">Score</th>
                    <th className="pb-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {result.options.map((option) => (
                    <tr key={option.name} className="border-t border-slate-800 text-slate-200">
                      <td className="py-3 pr-4">{option.rank ?? "—"}</td>
                      <td className="py-3 pr-4 font-medium text-white">{option.name}</td>
                      <td className="py-3 pr-4">{option.score !== null ? option.score.toFixed(3) : "—"}</td>
                      <td className="py-3">
                        {option.eligible ? "Eligible" : option.violations.join(" ") || "Excluded"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <h3 className="mb-3 text-base font-semibold text-white">Explainability</h3>
              <ul className="space-y-2 text-sm text-slate-300">
                {result.explanation.map((sentence, index) => (
                  <li key={`${sentence}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                    {sentence}
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ) : null}

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">Decision journal</h2>
          </div>
          {journalEntries.length === 0 ? (
            <div className="text-sm text-slate-400">No saved decisions yet.</div>
          ) : (
            <div className="space-y-3">
              {journalEntries.map((entry) => (
                <div key={entry.id} className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="font-medium text-white">{entry.title || "Untitled decision"}</div>
                    <div className="text-sm text-slate-400">{entry.description || "No description"}</div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleOpenJournal(entry)}
                      className="rounded-full border border-cyan-400/50 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-200"
                    >
                      Open
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteJournal(entry.id)}
                      className="rounded-full border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
