"use strict";

const form = document.querySelector("#analyzerForm");
const messageInput = document.querySelector("#messageInput");
const characterCount = document.querySelector("#characterCount");
const submitButton = document.querySelector("#submitButton");
const statusMessage = document.querySelector("#statusMessage");
const sampleButtons = [...document.querySelectorAll("[data-sample]")];
const resultCard = document.querySelector("#resultCard");
const demoNotice = document.querySelector("#demoNotice");
const modeTag = document.querySelector("#modeTag");
const assessmentBadge = document.querySelector("#assessmentBadge");

const assessmentLabels = {
  warning: "Warning",
  no_clear_signals: "No clear signals",
  insufficient_information: "Insufficient information",
};

function updateCharacterCount() {
  characterCount.textContent = `${messageInput.value.length} / 4000`;
}

function setBusy(isBusy) {
  messageInput.disabled = isBusy;
  submitButton.disabled = isBusy;
  sampleButtons.forEach((button) => { button.disabled = isBusy; });
  submitButton.querySelector("span:first-child").textContent = isBusy ? "Reviewing…" : "Review message";
  form.setAttribute("aria-busy", String(isBusy));
}

function addTextSection(container, heading, text) {
  if (!text) return;
  const section = document.createElement("section");
  section.className = "result-section";
  const title = document.createElement("h3");
  title.textContent = heading;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  section.append(title, paragraph);
  container.append(section);
}

function readString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function renderSignals(signals) {
  const section = document.querySelector("#signalsSection");
  const list = document.querySelector("#signalsList");
  list.replaceChildren();
  if (!Array.isArray(signals) || signals.length === 0) {
    section.hidden = true;
    return;
  }

  signals.forEach((signal) => {
    const item = document.createElement("article");
    item.className = "signal-item";
    const quote = readString(signal?.quote);
    const reason = readString(signal?.reason);
    if (quote) {
      const quoteElement = document.createElement("blockquote");
      quoteElement.className = "signal-quote";
      quoteElement.textContent = `“${quote}”`;
      item.append(quoteElement);
    }
    if (reason) {
      const reasonElement = document.createElement("p");
      reasonElement.className = "signal-reason";
      reasonElement.textContent = reason;
      item.append(reasonElement);
    }
    if (quote || reason) list.append(item);
  });
  section.hidden = list.childElementCount === 0;
}

function renderNextSteps(steps) {
  const section = document.querySelector("#nextStepsSection");
  const list = document.querySelector("#nextStepsList");
  list.replaceChildren();
  if (!Array.isArray(steps) || steps.length === 0) {
    section.hidden = true;
    return;
  }

  steps.forEach((step) => {
    const text = typeof step === "string"
      ? step.trim()
      : readString(step?.text) || readString(step?.step);
    if (!text) return;
    const item = document.createElement("li");
    item.textContent = text;
    list.append(item);
  });
  section.hidden = list.childElementCount === 0;
}

function renderResult(data) {
  const assessment = typeof data?.assessment === "string" ? data.assessment : "";
  const summary = readString(data?.summary);
  assessmentBadge.textContent = assessmentLabels[assessment] || "Review complete";
  assessmentBadge.dataset.assessment = assessmentLabels[assessment] ? assessment : "";

  const summarySection = document.querySelector("#summarySection");
  const summaryText = document.querySelector("#summaryText");
  summaryText.textContent = summary;
  summarySection.hidden = !summary;
  renderSignals(data?.signals);
  renderNextSteps(data?.next_steps);

  demoNotice.hidden = data?.mode !== "demo";
  modeTag.hidden = true;
  modeTag.textContent = "";
  if (data?.mode === "live") {
    modeTag.textContent = "Live analysis";
    modeTag.hidden = false;
  }

  resultCard.hidden = false;
  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function readBody(response) {
  const raw = await response.text();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { detail: raw };
  }
}

function errorDetail(payload) {
  const detail = payload?.detail ?? payload?.message ?? payload?.error;
  if (typeof detail === "string") return detail.trim();
  if (Array.isArray(detail)) {
    return detail.map((item) => typeof item === "string" ? item : readString(item?.msg)).filter(Boolean).join(" ");
  }
  if (detail && typeof detail === "object") {
    try { return JSON.stringify(detail); } catch { return ""; }
  }
  return "";
}

sampleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.sample || "";
    updateCharacterCount();
    messageInput.focus();
  });
});

messageInput.addEventListener("input", updateCharacterCount);
updateCharacterCount();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  statusMessage.textContent = "";
  resultCard.hidden = true;

  if (!text) {
    statusMessage.textContent = "Enter a message before starting the review.";
    messageInput.focus();
    return;
  }
  if (messageInput.value.length > 4000) {
    statusMessage.textContent = "Please keep the message to 4,000 characters or fewer.";
    return;
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 20000);
  setBusy(true);
  statusMessage.textContent = "Reviewing your message…";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ text }),
      signal: controller.signal,
    });
    const payload = await readBody(response);
    if (!response.ok) {
      const detail = errorDetail(payload);
      throw new Error(detail ? `Unable to review this message: ${detail}` : `The review request failed (HTTP ${response.status}). Please try again.`);
    }

    renderResult(payload);
    statusMessage.textContent = "Review complete.";
  } catch (error) {
    if (controller.signal.aborted) {
      statusMessage.textContent = "This request took too long. Please try again.";
    } else if (error instanceof TypeError) {
      statusMessage.textContent = "We couldn't reach the review service. Check your connection and try again.";
    } else {
      statusMessage.textContent = error?.message || "Something went wrong. Please try again.";
    }
  } finally {
    window.clearTimeout(timeoutId);
    setBusy(false);
  }
});
