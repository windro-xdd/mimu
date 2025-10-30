const EXCUSE_API_ENDPOINT = "/api/excuse";
const TIMER_SCORE_SUBMIT_ENDPOINT = "/api/leaderboard/timer";
const TIMER_TOKEN_ENDPOINT = "/api/leaderboard/timer/token";
const SCORE_LEADERBOARD_ENDPOINT = "/api/leaderboard/score";
const TIMER_LEADERBOARD_ENDPOINT = "/api/leaderboard/timer";
const TIMER_DURATION_MS = 5000;
const TIMER_BEST_STORAGE_KEY = "frontend-modules.timer.bestAccuracy";
const MAX_SAFE_DEPTH = 4;

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const getTimestamp = () =>
  typeof performance !== "undefined" && typeof performance.now === "function"
    ? performance.now()
    : Date.now();

const updateStatus = (element, message, state = "info") => {
  if (!element) {
    return;
  }
  element.textContent = message ?? "";
  if (state) {
    element.dataset.state = state;
  } else {
    delete element.dataset.state;
  }
};

const parseResponsePayload = async (response) => {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    return text;
  }
};

const deepFindString = (value, candidateKeys, depth = 0) => {
  if (value == null || depth > MAX_SAFE_DEPTH) {
    return undefined;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : undefined;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const found = deepFindString(item, candidateKeys, depth + 1);
      if (found) {
        return found;
      }
    }
    return undefined;
  }

  if (typeof value === "object") {
    for (const key of candidateKeys) {
      if (Object.prototype.hasOwnProperty.call(value, key)) {
        const candidate = value[key];
        if (typeof candidate === "string" && candidate.trim()) {
          return candidate.trim();
        }
        const nested = deepFindString(candidate, candidateKeys, depth + 1);
        if (nested) {
          return nested;
        }
      }
    }
  }

  return undefined;
};

const formatTimeMs = (ms) => {
  if (!Number.isFinite(ms)) {
    return "—";
  }
  return `${(ms / 1000).toFixed(3)}s`;
};

const formatCountdown = (ms) => {
  if (!Number.isFinite(ms)) {
    return "0.000s";
  }
  const absolute = Math.abs(ms);
  const formatted = (absolute / 1000).toFixed(3);
  if (ms > 0) {
    return `${formatted}s`;
  }
  if (ms < 0) {
    return `+${formatted}s`;
  }
  return "0.000s";
};

const normaliseEntries = (payload, depth = 0) => {
  if (payload == null || depth > MAX_SAFE_DEPTH) {
    return [];
  }

  if (Array.isArray(payload)) {
    return payload;
  }

  if (typeof payload === "object") {
    const candidateKeys = [
      "entries",
      "data",
      "results",
      "items",
      "leaderboard",
      "scores",
      "records",
    ];

    for (const key of candidateKeys) {
      if (Object.prototype.hasOwnProperty.call(payload, key)) {
        const nested = normaliseEntries(payload[key], depth + 1);
        if (Array.isArray(nested)) {
          return nested;
        }
      }
    }

    for (const value of Object.values(payload)) {
      const nested = normaliseEntries(value, depth + 1);
      if (Array.isArray(nested)) {
        return nested;
      }
    }
  }

  return [];
};

const normaliseNumber = (value) => {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
};

class ExcuseGenerator {
  constructor(root) {
    this.root = root;
    this.outputEl = root?.querySelector("[data-excuse-text]") ?? null;
    this.generateButton = root?.querySelector("[data-excuse-generate]") ?? null;
    this.copyButton = root?.querySelector("[data-excuse-copy]") ?? null;
    this.statusEl = root?.querySelector("[data-excuse-status]") ?? null;
    this.latestExcuse = "";
    this.isLoading = false;

    if (!this.root) {
      return;
    }

    this.generateButton?.addEventListener("click", () => {
      this.requestExcuse();
    });

    this.copyButton?.addEventListener("click", () => {
      this.copyToClipboard();
    });
  }

  async requestExcuse() {
    if (this.isLoading) {
      return;
    }

    this.setLoading(true);
    updateStatus(this.statusEl, "Fetching a brand new excuse…", "info");

    try {
      const response = await fetch(EXCUSE_API_ENDPOINT, {
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const payload = await parseResponsePayload(response);
      const excuse = this.resolveExcuse(payload);

      if (!excuse) {
        throw new Error("Excuse payload did not include a usable message");
      }

      this.latestExcuse = excuse;

      if (this.outputEl) {
        this.outputEl.textContent = excuse;
      }

      if (this.copyButton) {
        this.copyButton.disabled = false;
      }

      updateStatus(this.statusEl, "Excuse ready to copy.", "success");
    } catch (error) {
      this.latestExcuse = "";
      if (this.copyButton) {
        this.copyButton.disabled = true;
      }
      const message = error instanceof Error ? error.message : "Unknown error";
      updateStatus(this.statusEl, `Unable to fetch excuse: ${message}`, "error");
    } finally {
      this.setLoading(false);
    }
  }

  resolveExcuse(payload) {
    if (!payload) {
      return "";
    }

    if (typeof payload === "string") {
      return payload.trim();
    }

    const keys = ["excuse", "message", "text", "reason", "content", "value"];
    const found = deepFindString(payload, keys);
    return found ?? "";
  }

  async copyToClipboard() {
    if (!this.latestExcuse) {
      updateStatus(this.statusEl, "Generate an excuse before copying.", "error");
      return;
    }

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(this.latestExcuse);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = this.latestExcuse;
        textarea.setAttribute("readonly", "true");
        textarea.style.position = "absolute";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }

      updateStatus(this.statusEl, "Excuse copied to clipboard.", "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      updateStatus(this.statusEl, `Clipboard copy failed: ${message}`, "error");
    }
  }

  setLoading(isLoading) {
    this.isLoading = isLoading;
    if (this.generateButton) {
      this.generateButton.disabled = isLoading;
    }
  }
}

class CountdownTimerGame {
  constructor(root, options = {}) {
    this.root = root;
    this.options = options;
    this.displayEl = root?.querySelector("[data-timer-display]") ?? null;
    this.progressEl = root?.querySelector("[data-timer-progress]") ?? null;
    this.bestEl = root?.querySelector("[data-timer-best]") ?? null;
    this.lastEl = root?.querySelector("[data-timer-last]") ?? null;
    this.statusEl = root?.querySelector("[data-timer-status]") ?? null;
    this.startButton = root?.querySelector('[data-timer-action="start"]') ?? null;
    this.stopButton = root?.querySelector('[data-timer-action="stop"]') ?? null;
    this.resetButton = root?.querySelector('[data-timer-action="reset"]') ?? null;
    this.submitButton = root?.querySelector("[data-timer-submit]") ?? null;
    this.form = root?.querySelector("[data-timer-form]") ?? null;
    this.nameInput = this.form?.querySelector("input[name=\"playerName\"]") ?? null;

    this.durationMs = options.durationMs ?? TIMER_DURATION_MS;
    this.activeFrame = null;
    this.running = false;
    this.startTimestamp = null;
    this.targetTimestamp = null;
    this.latestRemaining = this.durationMs;
    this.latestResult = null;
    this.bestAccuracy = this.loadBestAccuracy();
    this.currentToken = null;
    this.submissionInFlight = false;

    if (!this.root) {
      return;
    }

    this.updateDisplay(this.durationMs);
    this.updateBestDisplay();
    this.updateLastDisplay();
    updateStatus(this.statusEl, "Press start to begin the countdown.", "info");

    this.startButton?.addEventListener("click", () => this.start());
    this.stopButton?.addEventListener("click", () => this.stop());
    this.resetButton?.addEventListener("click", () => this.reset());

    this.form?.addEventListener("submit", (event) => {
      event.preventDefault();
      this.submitScore();
    });

    this.nameInput?.addEventListener("input", () => this.updateSubmitButtonState());
    this.updateControls();
  }

  start() {
    if (this.running) {
      return;
    }

    this.latestResult = null;
    this.updateLastDisplay();
    this.updateSubmitButtonState();
    updateStatus(this.statusEl, "Countdown running… stop as close to zero as possible!", "info");

    this.running = true;
    this.startTimestamp = getTimestamp();
    this.targetTimestamp = this.startTimestamp + this.durationMs;
    this.tick();
    this.updateControls();

    // Fetch anti-cheat token in the background; ignore failures until submission time.
    this.prepareToken().catch(() => {
      /* token fetch failure handled during submission */
    });
  }

  stop() {
    if (!this.running) {
      return;
    }

    this.running = false;
    if (this.activeFrame) {
      cancelAnimationFrame(this.activeFrame);
      this.activeFrame = null;
    }

    const currentTime = getTimestamp();
    const remaining = (this.targetTimestamp ?? currentTime) - currentTime;
    this.latestRemaining = remaining;
    this.updateDisplay(remaining);

    const deviation = Math.abs(remaining);
    const roundedDeviation = Math.round(deviation);
    const overshot = remaining < 0;
    const deviationText = formatTimeMs(roundedDeviation);

    this.latestResult = {
      deviationMs: roundedDeviation,
      overshot,
      finishedAt: new Date().toISOString(),
      durationMs: this.durationMs,
      elapsedMs: Math.round(this.durationMs - remaining),
    };

    if (this.lastEl) {
      this.lastEl.textContent = deviationText;
    }

    if (this.bestAccuracy == null || roundedDeviation < this.bestAccuracy) {
      this.bestAccuracy = roundedDeviation;
      this.persistBestAccuracy(roundedDeviation);
      this.updateBestDisplay();
    }

    const statusMessage = overshot
      ? `Overshot by ${formatTimeMs(roundedDeviation)}.`
      : `Stopped ${formatTimeMs(roundedDeviation)} before zero.`;
    updateStatus(this.statusEl, `${statusMessage} Accuracy logged.`, "success");

    this.startTimestamp = null;
    this.targetTimestamp = null;

    this.updateControls();
    this.updateSubmitButtonState();
  }

  reset() {
    if (this.activeFrame) {
      cancelAnimationFrame(this.activeFrame);
      this.activeFrame = null;
    }
    this.running = false;
    this.startTimestamp = null;
    this.targetTimestamp = null;
    this.latestRemaining = this.durationMs;
    this.latestResult = null;
    this.updateDisplay(this.durationMs);
    this.updateControls();
    this.updateSubmitButtonState();
    this.updateLastDisplay();
    updateStatus(this.statusEl, "Timer reset. Ready for a new attempt.", "info");
  }

  tick() {
    if (!this.running) {
      return;
    }

    const currentTime = getTimestamp();
    const remaining = (this.targetTimestamp ?? currentTime) - currentTime;
    this.latestRemaining = remaining;
    this.updateDisplay(remaining);

    this.activeFrame = requestAnimationFrame(() => this.tick());
  }

  updateDisplay(remainingMs) {
    if (this.displayEl) {
      this.displayEl.textContent = formatCountdown(remainingMs);
    }

    if (this.progressEl) {
      const progressRatio = 1 - remainingMs / this.durationMs;
      const constrained = clamp(progressRatio, 0, 1);
      this.progressEl.style.width = `${(clamp(constrained, 0, 1) * 100).toFixed(1)}%`;
      if (progressRatio > 1) {
        this.progressEl.dataset.state = "overshoot";
      } else {
        delete this.progressEl.dataset.state;
      }
    }
  }

  updateControls() {
    if (this.startButton) {
      this.startButton.disabled = this.running;
    }
    if (this.stopButton) {
      this.stopButton.disabled = !this.running;
    }
    if (this.resetButton) {
      const hasAttempt = this.latestResult != null || this.startTimestamp != null;
      this.resetButton.disabled = this.running || !hasAttempt;
    }
  }

  updateSubmitButtonState() {
    if (!this.submitButton) {
      return;
    }
    const hasResult = Boolean(this.latestResult);
    const hasName = Boolean(this.nameInput?.value.trim().length >= 2);
    const disabled = !hasResult || !hasName || this.submissionInFlight;
    this.submitButton.disabled = disabled;
  }

  updateBestDisplay() {
    if (this.bestEl) {
      this.bestEl.textContent =
        this.bestAccuracy != null ? formatTimeMs(this.bestAccuracy) : "No attempts yet";
    }
  }

  updateLastDisplay() {
    if (this.lastEl) {
      this.lastEl.textContent = this.latestResult
        ? formatTimeMs(this.latestResult.deviationMs)
        : "—";
    }
  }

  loadBestAccuracy() {
    try {
      const stored = window.localStorage?.getItem(TIMER_BEST_STORAGE_KEY);
      if (!stored) {
        return null;
      }
      const numeric = Number.parseInt(stored, 10);
      return Number.isFinite(numeric) ? numeric : null;
    } catch (error) {
      return null;
    }
  }

  persistBestAccuracy(value) {
    try {
      window.localStorage?.setItem(TIMER_BEST_STORAGE_KEY, String(value));
    } catch (error) {
      // Ignore storage errors
    }
  }

  async prepareToken(force = false) {
    if (!force && this.currentToken) {
      return this.currentToken;
    }

    try {
      const response = await fetch(TIMER_TOKEN_ENDPOINT, {
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`Token endpoint returned ${response.status}`);
      }

      const payload = await parseResponsePayload(response);
      const token = deepFindString(payload, [
        "token",
        "antiCheatToken",
        "value",
        "data",
        "result",
      ]);

      if (!token) {
        throw new Error("Token was not present in the response");
      }

      this.currentToken = token;
      return token;
    } catch (error) {
      this.currentToken = null;
      throw error;
    }
  }

  async submitScore() {
    if (!this.latestResult) {
      updateStatus(this.statusEl, "Complete a run before submitting.", "error");
      return;
    }

    if (!this.nameInput) {
      updateStatus(this.statusEl, "Name field unavailable.", "error");
      return;
    }

    const name = this.nameInput.value.trim();
    if (name.length < 2) {
      updateStatus(this.statusEl, "Enter a display name to submit.", "error");
      return;
    }

    let token = this.currentToken;
    if (!token) {
      try {
        token = await this.prepareToken(true);
      } catch (error) {
        // continue without token, but surface warning below
      }
    }

    const payload = {
      name,
      deviationMs: this.latestResult.deviationMs,
      overshot: this.latestResult.overshot,
      finishedAt: this.latestResult.finishedAt,
      durationMs: this.latestResult.durationMs,
      elapsedMs: this.latestResult.elapsedMs,
      token: token ?? undefined,
    };

    const headers = { "Content-Type": "application/json" };
    if (token) {
      headers["X-Anti-Cheat-Token"] = token;
    }

    this.submissionInFlight = true;
    this.updateSubmitButtonState();
    updateStatus(this.statusEl, "Submitting score…", "info");

    try {
      const response = await fetch(TIMER_SCORE_SUBMIT_ENDPOINT, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorPayload = await parseResponsePayload(response);
        const errorMessage =
          (typeof errorPayload === "string" && errorPayload.trim()) ||
          deepFindString(errorPayload, ["detail", "message", "error", "reason"]) ||
          `Server responded with status ${response.status}`;
        throw new Error(errorMessage);
      }

      updateStatus(
        this.statusEl,
        "Score submitted successfully. Leaderboard will refresh shortly.",
        "success",
      );

      this.currentToken = null;
      this.latestResult = null;
      this.updateSubmitButtonState();
      if (typeof this.options.onSubmitSuccess === "function") {
        this.options.onSubmitSuccess();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      updateStatus(this.statusEl, `Submission failed: ${message}`, "error");
    } finally {
      this.submissionInFlight = false;
      this.updateSubmitButtonState();
    }
  }
}

class LeaderboardModule {
  constructor(root, { endpoint, type }) {
    this.root = root;
    this.endpoint = endpoint;
    this.type = type;
    this.refreshButton = root?.querySelector("[data-leaderboard-refresh]") ?? null;
    this.placeholderEl = root?.querySelector("[data-leaderboard-placeholder]") ?? null;
    this.tableWrapper = root?.querySelector("[data-leaderboard-table-wrapper]") ?? null;
    this.tableBody = root?.querySelector("[data-leaderboard-table-body]") ?? null;
    this.cardsContainer = root?.querySelector("[data-leaderboard-cards]") ?? null;
    this.statusEl = root?.querySelector("[data-leaderboard-status]") ?? null;
    this.isLoading = false;

    if (!this.root) {
      return;
    }

    this.refreshButton?.addEventListener("click", () => this.refresh());
    this.refresh();
  }

  async refresh() {
    if (this.isLoading) {
      return;
    }

    this.setLoading(true);
    updateStatus(this.statusEl, "Loading leaderboard…", "info");

    try {
      const response = await fetch(this.endpoint, {
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const payload = await parseResponsePayload(response);
      const entries = normaliseEntries(payload);
      this.render(entries);
      updateStatus(
        this.statusEl,
        `Last updated ${new Date().toLocaleTimeString()}.`,
        "success",
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      this.render([]);
      updateStatus(this.statusEl, `Unable to load leaderboard: ${message}`, "error");
    } finally {
      this.setLoading(false);
    }
  }

  setLoading(isLoading) {
    this.isLoading = isLoading;
    if (this.placeholderEl) {
      this.placeholderEl.hidden = !isLoading;
      this.placeholderEl.textContent = isLoading
        ? "Loading leaderboard…"
        : this.placeholderEl.textContent;
    }
    if (isLoading) {
      this.tableWrapper?.setAttribute("hidden", "");
      this.cardsContainer?.setAttribute("hidden", "");
      this.tableBody?.replaceChildren();
      this.cardsContainer?.replaceChildren();
    }
  }

  render(entries) {
    if (!entries || entries.length === 0) {
      if (this.placeholderEl) {
        this.placeholderEl.hidden = false;
        this.placeholderEl.textContent = "No leaderboard data yet.";
      }
      this.tableWrapper?.setAttribute("hidden", "");
      this.cardsContainer?.setAttribute("hidden", "");
      this.tableBody?.replaceChildren();
      this.cardsContainer?.replaceChildren();
      return;
    }

    this.placeholderEl?.setAttribute("hidden", "");
    this.tableWrapper?.removeAttribute("hidden");
    this.cardsContainer?.removeAttribute("hidden");

    if (this.tableBody) {
      this.tableBody.replaceChildren();
      entries.forEach((entry, index) => {
        const row = document.createElement("tr");
        const rankCell = document.createElement("td");
        const nameCell = document.createElement("td");
        const valueCell = document.createElement("td");

        rankCell.textContent = this.resolveRank(entry, index);
        nameCell.textContent = this.resolveName(entry);
        valueCell.textContent = this.resolveValue(entry);

        row.append(rankCell, nameCell, valueCell);
        this.tableBody.appendChild(row);
      });
    }

    if (this.cardsContainer) {
      this.cardsContainer.replaceChildren();
      entries.forEach((entry, index) => {
        const card = document.createElement("article");
        card.className = "leaderboard-card";

        const meta = document.createElement("div");
        meta.className = "leaderboard-card__meta";
        const rankLabel = document.createElement("span");
        rankLabel.textContent = "Rank";
        const rankValue = document.createElement("span");
        rankValue.textContent = this.resolveRank(entry, index);
        meta.append(rankLabel, rankValue);

        const name = document.createElement("div");
        name.className = "leaderboard-card__name";
        name.textContent = this.resolveName(entry);

        const value = document.createElement("div");
        value.className = "leaderboard-card__value";
        value.textContent = this.resolveValue(entry);

        card.append(meta, name, value);
        this.cardsContainer.appendChild(card);
      });
    }
  }

  resolveRank(entry, index) {
    const keys = ["rank", "position", "place", "index"];
    for (const key of keys) {
      if (entry && entry[key] != null) {
        const value = normaliseNumber(entry[key]);
        if (Number.isFinite(value)) {
          return String(Math.round(value));
        }
        return String(entry[key]);
      }
    }
    return String(index + 1);
  }

  resolveName(entry) {
    const keys = ["name", "player", "playerName", "displayName", "username", "handle"];
    for (const key of keys) {
      if (entry && typeof entry[key] === "string") {
        const trimmed = entry[key].trim();
        if (trimmed) {
          return trimmed;
        }
      }
    }
    return "Anonymous";
  }

  resolveValue(entry) {
    const scoreKeys = ["score", "points", "value", "total", "amount"];
    const timeKeys = [
      "accuracyMs",
      "accuracy",
      "deviationMs",
      "deviation",
      "deltaMs",
      "timeMs",
      "time",
      "milliseconds",
      "best",
    ];

    const keys = this.type === "timer" ? timeKeys : scoreKeys;

    for (const key of keys) {
      if (entry && entry[key] != null) {
        const numeric = normaliseNumber(entry[key]);
        if (numeric != null) {
          if (this.type === "timer") {
            return formatTimeMs(Math.round(Math.abs(numeric)));
          }
          return Number.isInteger(numeric) ? numeric.toLocaleString() : numeric.toFixed(2);
        }
        if (typeof entry[key] === "string" && entry[key].trim()) {
          return entry[key].trim();
        }
      }
    }

    if (this.type === "timer") {
      return "—";
    }

    return "0";
  }
}

const initialise = () => {
  const excuseModule = document.querySelector("[data-module-excuse]");
  if (excuseModule) {
    new ExcuseGenerator(excuseModule);
  }

  const timerLeaderboardRoot = document.querySelector('[data-leaderboard="timer"]');
  const timerLeaderboardInstance = timerLeaderboardRoot
    ? new LeaderboardModule(timerLeaderboardRoot, {
        endpoint: TIMER_LEADERBOARD_ENDPOINT,
        type: "timer",
      })
    : null;

  const scoreLeaderboardRoot = document.querySelector('[data-leaderboard="score"]');
  if (scoreLeaderboardRoot) {
    new LeaderboardModule(scoreLeaderboardRoot, {
      endpoint: SCORE_LEADERBOARD_ENDPOINT,
      type: "score",
    });
  }

  const timerGameRoot = document.querySelector("[data-module-timer] [data-timer]");
  if (timerGameRoot) {
    new CountdownTimerGame(timerGameRoot, {
      durationMs: TIMER_DURATION_MS,
      onSubmitSuccess: () => {
        if (typeof timerLeaderboardInstance?.refresh === "function") {
          timerLeaderboardInstance.refresh();
        }
      },
    });
  }

  // Footer year stamp
  const yearEl = document.querySelector("[data-year]");
  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initialise);
} else {
  initialise();
}
