"use strict";

const MAX_CHARACTERS = 4000;
const REQUEST_TIMEOUT_MS = 30000;

const form = document.querySelector("#analyzerForm");
const messageInput = document.querySelector("#messageInput");
const characterCount = document.querySelector("#characterCount");
const submitButton = document.querySelector("#submitButton");
const submitLabel = document.querySelector("#submitLabel");
const statusMessage = document.querySelector("#statusMessage");
const sampleButtons = [...document.querySelectorAll("[data-sample]")];

const errorCard = document.querySelector("#errorCard");
const errorMessage = document.querySelector("#errorMessage");
const retryButton = document.querySelector("#retryButton");

const resultCard = document.querySelector("#resultCard");
const demoNotice = document.querySelector("#demoNotice");
const modeTag = document.querySelector("#modeTag");
const assessmentBadge = document.querySelector("#assessmentBadge");
const summarySection = document.querySelector("#summarySection");
const summaryText = document.querySelector("#summaryText");
const originalSection = document.querySelector("#originalSection");
const originalText = document.querySelector("#originalText");
const highlightHint = document.querySelector("#highlightHint");
const signalsSection = document.querySelector("#signalsSection");
const signalsList = document.querySelector("#signalsList");
const nextStepsSection = document.querySelector("#nextStepsSection");
const nextStepsList = document.querySelector("#nextStepsList");
const checkAnotherButton = document.querySelector("#checkAnotherButton");

const ASSESSMENT_LABELS = {
  warning: "Warning",
  no_clear_signals: "No clear signals",
  insufficient_information: "Insufficient information",
};

let inFlight = false;
let lastSubmittedText = "";

/* ---------- small helpers ---------- */

function readString(value) {
  return typeof value === "string" ? value : "";
}

function updateCharacterCount() {
  const length = messageInput.value.length;
  characterCount.textContent = `${length} / ${MAX_CHARACTERS}`;
  characterCount.classList.toggle("over-limit", length > MAX_CHARACTERS);
}

function setBusy(isBusy) {
  inFlight = isBusy;
  messageInput.disabled = isBusy;
  submitButton.disabled = isBusy;
  retryButton.disabled = isBusy;
  sampleButtons.forEach((button) => { button.disabled = isBusy; });
  submitLabel.textContent = isBusy ? "Checking…" : "Help me check";
  form.setAttribute("aria-busy", String(isBusy));
}

function setStatus(text, kind) {
  statusMessage.textContent = text;
  statusMessage.dataset.kind = kind || "";
}

function hideResult() {
  resultCard.hidden = true;
}

function hideError() {
  errorCard.hidden = true;
  errorMessage.textContent = "";
}

function showError(text) {
  hideResult();
  errorMessage.textContent = text;
  errorCard.hidden = false;
  errorCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---------- original text with exact highlights ---------- */

function findRanges(text, quotes) {
  const ranges = [];
  const matched = new Set();
  quotes.forEach((quote, index) => {
    if (!quote) return;
    let from = 0;
    let found = false;
    while (from <= text.length) {
      const at = text.indexOf(quote, from);
      if (at === -1) break;
      found = true;
      ranges.push({ start: at, end: at + quote.length, index });
      from = at + quote.length;
    }
    if (found) matched.add(index);
  });

  ranges.sort((a, b) => a.start - b.start || b.end - a.end);
  const merged = [];
  ranges.forEach((range) => {
    const last = merged[merged.length - 1];
    if (last && range.start <= last.end) {
      last.end = Math.max(last.end, range.end);
    } else {
      merged.push({ start: range.start, end: range.end });
    }
  });
  return { merged, matched };
}

function renderOriginal(text, signals) {
  originalText.replaceChildren();
  if (!text) {
    originalSection.hidden = true;
    return new Set();
  }

  const quotes = signals.map((signal) => signal.quote);
  const { merged, matched } = findRanges(text, quotes);

  let cursor = 0;
  merged.forEach((range, position) => {
    if (range.start > cursor) {
      originalText.append(document.createTextNode(text.slice(cursor, range.start)));
    }
    const mark = document.createElement("mark");
    mark.className = "highlight";
    mark.textContent = text.slice(range.start, range.end);
    mark.setAttribute("aria-label", `Highlighted wording ${position + 1}: ${text.slice(range.start, range.end)}`);
    originalText.append(mark);
    cursor = range.end;
  });
  if (cursor < text.length) {
    originalText.append(document.createTextNode(text.slice(cursor)));
  }

  if (merged.length === 0) {
    highlightHint.textContent = signals.length === 0
      ? "No specific wording was highlighted."
      : "The wording mentioned below was not found word-for-word in your message, so nothing is highlighted.";
  } else {
    highlightHint.textContent = `Highlighted wording is explained below (${merged.length} ${merged.length === 1 ? "passage" : "passages"}).`;
  }
  originalSection.hidden = false;
  return matched;
}

/* ---------- result sections ---------- */

function normalizeSignals(rawSignals) {
  if (!Array.isArray(rawSignals)) return [];
  return rawSignals
    .map((signal) => ({
      quote: readString(signal?.quote),
      reason: readString(signal?.reason).trim(),
    }))
    .filter((signal) => signal.quote.trim() || signal.reason);
}

function renderSignals(signals, matched) {
  signalsList.replaceChildren();
  if (signals.length === 0) {
    signalsSection.hidden = true;
    return;
  }

  signals.forEach((signal, index) => {
    const item = document.createElement("article");
    item.className = "signal-item";

    if (signal.quote.trim()) {
      const quoteElement = document.createElement("blockquote");
      quoteElement.className = "signal-quote";
      quoteElement.textContent = signal.quote;
      item.append(quoteElement);
      if (!matched.has(index)) {
        const note = document.createElement("p");
        note.className = "signal-note";
        note.textContent = "Not found word-for-word in your message, so it is not highlighted above.";
        item.append(note);
      }
    }
    if (signal.reason) {
      const reasonElement = document.createElement("p");
      reasonElement.className = "signal-reason";
      reasonElement.textContent = signal.reason;
      item.append(reasonElement);
    }
    signalsList.append(item);
  });
  signalsSection.hidden = false;
}

function renderNextSteps(steps) {
  nextStepsList.replaceChildren();
  if (!Array.isArray(steps)) {
    nextStepsSection.hidden = true;
    return;
  }
  steps.forEach((step) => {
    const text = readString(step).trim();
    if (!text) return;
    const item = document.createElement("li");
    item.textContent = text;
    nextStepsList.append(item);
  });
  nextStepsSection.hidden = nextStepsList.childElementCount === 0;
}

function renderMode(mode) {
  demoNotice.hidden = mode !== "demo";
  modeTag.hidden = true;
  modeTag.textContent = "";
  modeTag.dataset.mode = "";
  if (mode === "live") {
    modeTag.textContent = "Live analysis";
    modeTag.dataset.mode = "live";
    modeTag.hidden = false;
  } else if (mode === "demo") {
    modeTag.textContent = "Demo";
    modeTag.dataset.mode = "demo";
    modeTag.hidden = false;
  }
}

function renderResult(data, submittedText) {
  hideError();

  const assessment = readString(data?.assessment);
  const label = ASSESSMENT_LABELS[assessment];
  assessmentBadge.textContent = label || "Not reported";
  assessmentBadge.dataset.assessment = label ? assessment : "";

  const summary = readString(data?.summary).trim();
  summaryText.textContent = summary;
  summarySection.hidden = !summary;

  const signals = normalizeSignals(data?.signals);
  const matched = renderOriginal(submittedText, signals);
  renderSignals(signals, matched);
  renderNextSteps(data?.next_steps);
  renderMode(data?.mode);

  resultCard.hidden = false;
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  resultCard.setAttribute("tabindex", "-1");
  resultCard.focus({ preventScroll: true });
}

/* ---------- request handling ---------- */

async function readBody(response) {
  const raw = await response.text();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function backendDetail(payload) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail.trim();
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === "string" ? item : readString(item?.msg)))
      .filter(Boolean)
      .join(" ");
  }
  return "";
}

function errorTextForResponse(status, payload) {
  const detail = backendDetail(payload);
  if (status === 422) {
    return detail || "The message could not be accepted. Please check it and try again.";
  }
  if (status === 503) {
    return detail
      ? `Analysis is temporarily unavailable. ${detail}`
      : "Analysis is temporarily unavailable right now. Please try again in a moment.";
  }
  if (status === 429) {
    return "Too many checks in a short time. Please wait a moment and try again.";
  }
  return `The check could not be completed (server responded with ${status}). Please try again.`;
}

function validateInput() {
  const raw = messageInput.value;
  const text = raw.trim();
  if (!text) {
    setStatus("Please paste or type a message first.", "error");
    messageInput.focus();
    return null;
  }
  if (text.length > MAX_CHARACTERS) {
    setStatus(`This message is ${text.length.toLocaleString("en-US")} characters. Please shorten it to ${MAX_CHARACTERS.toLocaleString("en-US")} characters or fewer.`, "error");
    messageInput.focus();
    return null;
  }
  return text;
}

async function submitText(text) {
  if (inFlight) return;
  lastSubmittedText = text;
  hideError();
  hideResult();
  setBusy(true);
  setStatus("Checking your message… this can take up to 30 seconds.", "busy");

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });
    const payload = await readBody(response);
    if (!response.ok) {
      setStatus("", "");
      showError(errorTextForResponse(response.status, payload));
      return;
    }
    if (!payload || typeof payload !== "object" || !ASSESSMENT_LABELS[payload.assessment]) {
      setStatus("", "");
      showError("The analysis service sent back a response we could not read. Please try again.");
      return;
    }
    renderResult(payload, text);
    setStatus("Check complete. The result is shown below.", "done");
  } catch (error) {
    setStatus("", "");
    if (controller.signal.aborted) {
      showError("The check took too long and was stopped. Please try again.");
    } else if (error instanceof TypeError) {
      showError("We couldn’t reach the analysis service. Check your internet connection and try again.");
    } else {
      showError("Something went wrong while checking the message. Please try again.");
    }
  } finally {
    window.clearTimeout(timeoutId);
    setBusy(false);
    if (!errorCard.hidden) retryButton.focus({ preventScroll: true });
  }
}

/* ---------- wiring ---------- */

sampleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.sample || "";
    updateCharacterCount();
    setStatus("Example added. Press “Help me check” when you are ready.", "");
    messageInput.focus();
  });
});

messageInput.addEventListener("input", () => {
  updateCharacterCount();
  if (statusMessage.dataset.kind === "error") setStatus("", "");
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (inFlight) return;
  const text = validateInput();
  if (text === null) return;
  submitText(text);
});

retryButton.addEventListener("click", () => {
  if (inFlight) return;
  const current = messageInput.value.trim();
  const text = current || lastSubmittedText;
  if (!text) {
    hideError();
    setStatus("Please paste or type a message first.", "error");
    messageInput.focus();
    return;
  }
  if (text.length > MAX_CHARACTERS) {
    hideError();
    validateInput();
    return;
  }
  submitText(text);
});

checkAnotherButton.addEventListener("click", () => {
  hideResult();
  setStatus("", "");
  messageInput.focus();
  messageInput.select();
  messageInput.scrollIntoView({ behavior: "smooth", block: "center" });
});

updateCharacterCount();
