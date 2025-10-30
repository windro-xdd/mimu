const PAGE_SIZE = 12;
const FEED_ENDPOINT = "/api/memes";
const RANDOM_ENDPOINT = "/api/memes/random";
const VOTE_ENDPOINT_TEMPLATE = "/api/memes/{id}/vote";

const memesGrid = document.getElementById("memes-grid");
const feedStatus = document.getElementById("feed-status");
const feedLoader = document.getElementById("feed-loader");
const feedEnd = document.getElementById("feed-end");
const loadMoreButton = document.getElementById("load-more-button");
const randomMemeButton = document.getElementById("random-meme-button");
const sentinel = document.getElementById("feed-sentinel");
const cardTemplate = document.getElementById("meme-card-template");

const renderedMemes = new Set();
const memeStates = new Map();

const state = {
  nextRequest: createUrl(),
  loading: false,
  done: false,
  initialLoad: true,
  fallbackPage: 1,
};

const yearElement = document.getElementById("current-year");
if (yearElement) {
  yearElement.textContent = String(new Date().getFullYear());
}

if (memesGrid && cardTemplate) {
  initialize();
} else {
  console.warn("Home feed markup missing; skipping feed initialization.");
}

function initialize() {
  initInfiniteScroll();
  if (loadMoreButton) {
    loadMoreButton.addEventListener("click", () => loadMoreMemes({ force: true }));
  }

  if (randomMemeButton) {
    randomMemeButton.addEventListener("click", handleRandomMeme);
  }

  window.addEventListener("online", () => {
    if (!state.loading && !state.done && memesGrid.childElementCount === 0) {
      loadMoreMemes();
    }
  });

  loadMoreMemes();
}

function initInfiniteScroll() {
  if (!sentinel) {
    revealLoadMoreButton();
    return;
  }

  if (!("IntersectionObserver" in window)) {
    revealLoadMoreButton();
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          loadMoreMemes();
        }
      });
    },
    { root: null, threshold: 0.1, rootMargin: "600px 0px 600px 0px" }
  );

  observer.observe(sentinel);
}

function revealLoadMoreButton() {
  if (loadMoreButton) {
    loadMoreButton.hidden = false;
  }
}

async function loadMoreMemes({ force = false } = {}) {
  if (!force && (state.loading || state.done || !state.nextRequest)) {
    return;
  }

  hideStatus();
  setLoaderState(true);
  state.loading = true;

  try {
    const response = await fetch(state.nextRequest, {
      credentials: "include",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error("Failed to load memes. Please try again.");
    }

    const payload = await safeJson(response);
    const memes = extractMemes(payload);

    if (Array.isArray(memes) && memes.length > 0) {
      renderMemes(memes);
    } else if (state.initialLoad) {
      showStatus("No approved memes yet. Be the first to upload!", "info");
      state.done = true;
      showEndState(true);
    }

    updateNextRequest(payload, Array.isArray(memes) ? memes.length : 0);
  } catch (error) {
    showStatus(error?.message || "Something went wrong while loading memes.", "error");
    revealLoadMoreButton();
  } finally {
    state.loading = false;
    state.initialLoad = false;
    setLoaderState(false);
  }
}

function renderMemes(memes) {
  const fragment = document.createDocumentFragment();

  memes.forEach((meme) => {
    const key = getMemeKey(meme);

    if (key && renderedMemes.has(key)) {
      const existingCard = findCardByKey(key);
      if (existingCard) {
        const scoreEl = existingCard.querySelector('[data-role="score"]');
        const nextScore = normalizeScore(meme.score);
        if (scoreEl && typeof nextScore === "number") {
          scoreEl.textContent = nextScore;
        }
        const storedState = memeStates.get(key);
        if (storedState && typeof nextScore === "number") {
          storedState.score = nextScore;
        }
      }
      return;
    }

    const card = createMemeCard(meme, key);
    if (card) {
      fragment.appendChild(card);
      if (key) {
        renderedMemes.add(key);
      }
    }
  });

  if (fragment.childElementCount > 0) {
    memesGrid.appendChild(fragment);
  }
}

function createMemeCard(meme, key) {
  if (!cardTemplate?.content) {
    return null;
  }

  const clone = cardTemplate.content.firstElementChild?.cloneNode(true);
  if (!clone) {
    return null;
  }

  if (key) {
    clone.dataset.memeKey = String(key);
  }

  const imageWrapper = clone.querySelector(".meme-image-wrapper");
  const imageEl = clone.querySelector('[data-role="image"]');
  const captionEl = clone.querySelector('[data-role="caption"]');
  const scoreEl = clone.querySelector('[data-role="score"]');
  const errorEl = clone.querySelector('[data-role="error"]');

  const imageSrc = resolveImageSource(meme);
  const captionText = resolveCaption(meme);
  const scoreValue = normalizeScore(meme.score);

  if (imageEl) {
    imageEl.loading = "lazy";
    imageEl.decoding = "async";
    imageEl.alt = resolveAltText(meme, captionText);

    if (imageSrc) {
      imageEl.src = imageSrc;
      if (imageWrapper) {
        imageWrapper.hidden = false;
      }
      clone.classList.remove("meme-card--text-only");
    } else {
      imageEl.removeAttribute("src");
      if (imageWrapper) {
        imageWrapper.hidden = true;
      }
      clone.classList.add("meme-card--text-only");
    }
  }

  if (captionEl) {
    captionEl.textContent = captionText;
  }

  if (scoreEl) {
    scoreEl.textContent = typeof scoreValue === "number" ? scoreValue : 0;
  }

  if (errorEl) {
    errorEl.textContent = "";
    errorEl.hidden = true;
  }

  const memeState = {
    key,
    id: resolveIdentifier(meme),
    score: typeof scoreValue === "number" ? scoreValue : 0,
  };

  setupVoting(clone, memeState);

  if (key) {
    memeStates.set(key, memeState);
  }

  return clone;
}

function setupVoting(card, memeState) {
  const upvoteButton = card.querySelector('.vote-button.upvote');
  const downvoteButton = card.querySelector('.vote-button.downvote');
  const scoreEl = card.querySelector('[data-role="score"]');
  const errorEl = card.querySelector('[data-role="error"]');

  if (!upvoteButton || !downvoteButton || !scoreEl) {
    return;
  }

  let isPending = false;

  const setButtonsDisabled = (disabled) => {
    upvoteButton.disabled = disabled;
    downvoteButton.disabled = disabled;
  };

  const updateScore = (nextScore) => {
    memeState.score = nextScore;
    scoreEl.textContent = nextScore;
  };

  const handleVote = async (direction) => {
    if (isPending) {
      return;
    }

    const identifierForPayload = getIdentifierForRequest(memeState);
    if (!identifierForPayload) {
      if (errorEl) {
        errorEl.textContent = "Voting isn't available for this meme yet.";
        errorEl.hidden = false;
      }
      return;
    }

    const delta = direction === "up" ? 1 : -1;
    const previousScore = memeState.score;

    updateScore(previousScore + delta);
    setButtonsDisabled(true);
    isPending = true;

    if (errorEl) {
      errorEl.textContent = "";
      errorEl.hidden = true;
    }

    try {
      const endpoint = buildVoteUrl(identifierForPayload);
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          direction,
          vote: direction,
          value: delta,
          memeId: identifierForPayload,
        }),
      });

      if (!response.ok) {
        throw new Error("Vote failed. Please try again.");
      }

      const payload = await safeJson(response);
      const updatedScore = resolveScoreFromPayload(payload);
      if (typeof updatedScore === "number" && Number.isFinite(updatedScore)) {
        updateScore(updatedScore);
      }

      dispatchVoteEvents(identifierForPayload, direction, memeState.score);
    } catch (error) {
      updateScore(previousScore);
      if (errorEl) {
        errorEl.textContent = error?.message || "Vote failed. Please try again.";
        errorEl.hidden = false;
      }
    } finally {
      setButtonsDisabled(false);
      isPending = false;
    }
  };

  upvoteButton.addEventListener("click", () => handleVote("up"));
  downvoteButton.addEventListener("click", () => handleVote("down"));
}

function dispatchVoteEvents(identifier, direction, score) {
  if (!identifier) {
    return;
  }

  const detail = { memeId: identifier, direction, score };

  window.dispatchEvent(new CustomEvent("meme:vote", { detail }));
  window.dispatchEvent(new CustomEvent("gamification:vote", { detail }));
}

async function handleRandomMeme() {
  if (!randomMemeButton) {
    return;
  }

  const originalText = randomMemeButton.textContent;
  randomMemeButton.disabled = true;
  randomMemeButton.textContent = "Finding a meme…";
  hideStatus();

  try {
    const response = await fetch(RANDOM_ENDPOINT, {
      credentials: "include",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error("Couldn't fetch a random meme. Try again.");
    }

    const payload = await safeJson(response);
    const meme = resolveSingleMeme(payload);
    const destination = resolveMemeDestination(payload, meme);

    if (destination) {
      window.location.assign(destination);
      return;
    }

    if (meme) {
      const key = getMemeKey(meme);
      if (key && renderedMemes.has(key)) {
        const existingCard = findCardByKey(key);
        if (existingCard) {
          existingCard.scrollIntoView({ behavior: "smooth", block: "center" });
          return;
        }
      }

      const card = createMemeCard(meme, getMemeKey(meme));
      if (card) {
        memesGrid.prepend(card);
        const keyForCard = card.dataset.memeKey;
        if (keyForCard) {
          renderedMemes.add(keyForCard);
        }
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
    }

    showStatus("Unable to load a random meme right now.", "error");
  } catch (error) {
    showStatus(error?.message || "Unable to load a random meme right now.", "error");
  } finally {
    randomMemeButton.disabled = false;
    randomMemeButton.textContent = originalText;
  }
}

function extractMemes(payload) {
  if (!payload) {
    return [];
  }

  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload.data)) {
    return payload.data;
  }

  if (Array.isArray(payload.memes)) {
    return payload.memes;
  }

  if (Array.isArray(payload.items)) {
    return payload.items;
  }

  if (Array.isArray(payload.results)) {
    return payload.results;
  }

  return [];
}

function resolveSingleMeme(payload) {
  if (!payload) {
    return null;
  }

  if (Array.isArray(payload)) {
    return payload[0] ?? null;
  }

  if (payload.meme && typeof payload.meme === "object") {
    return payload.meme;
  }

  if (payload.data && !Array.isArray(payload.data) && typeof payload.data === "object") {
    return payload.data;
  }

  if (Array.isArray(payload.data)) {
    return payload.data[0] ?? null;
  }

  if (Array.isArray(payload.memes)) {
    return payload.memes[0] ?? null;
  }

  if (payload.result && typeof payload.result === "object") {
    return payload.result;
  }

  return null;
}

function resolveMemeDestination(payload, meme) {
  const directUrl =
    payload?.redirect || payload?.url || payload?.location || payload?.permalink;

  if (typeof directUrl === "string" && directUrl.length > 0) {
    return directUrl;
  }

  if (meme) {
    if (typeof meme.permalink === "string") {
      return meme.permalink;
    }

    if (typeof meme.url === "string" && meme.url.startsWith("http")) {
      return meme.url;
    }

    if (typeof meme.slug === "string" && meme.slug.length > 0) {
      return `/memes/${meme.slug}`;
    }

    if (typeof meme.id === "string" || typeof meme.id === "number") {
      return `/memes/${meme.id}`;
    }
  }

  return null;
}

function updateNextRequest(payload, receivedCount) {
  const nextLink = resolveNextLink(payload);
  if (nextLink) {
    const normalized = normalizeUrl(nextLink);
    if (normalized) {
      state.nextRequest = normalized;
      state.done = false;
      showEndState(false);
    } else {
      state.nextRequest = null;
      state.done = true;
      showEndState(true);
    }
    return;
  }

  const nextCursor = resolveNextCursor(payload);
  if (nextCursor) {
    state.nextRequest = createUrl({ cursor: nextCursor });
    state.done = false;
    showEndState(false);
    return;
  }

  const nextPage = resolveNextPage(payload);
  if (nextPage) {
    state.nextRequest = createUrl({ page: nextPage });
    state.fallbackPage = nextPage;
    state.done = false;
    showEndState(false);
    return;
  }

  if (resolveHasMore(payload, receivedCount)) {
    state.fallbackPage = (state.fallbackPage || 1) + 1;
    state.nextRequest = createUrl({ page: state.fallbackPage });
    state.done = false;
    showEndState(false);
    return;
  }

  state.nextRequest = null;
  state.done = true;
  showEndState(true);
}

function resolveNextLink(payload) {
  const link =
    payload?.links?.next ||
    payload?.links?.nextUrl ||
    payload?.nextUrl ||
    payload?.next ||
    payload?.meta?.nextUrl ||
    payload?.meta?.next ||
    payload?.pagination?.nextUrl ||
    payload?.pagination?.next;

  if (typeof link === "string" && link.length > 0) {
    return link;
  }

  return null;
}

function resolveNextCursor(payload) {
  const cursor =
    payload?.nextCursor ||
    payload?.cursor ||
    payload?.pagination?.nextCursor ||
    payload?.meta?.nextCursor;

  if (cursor !== undefined && cursor !== null && cursor !== "") {
    return cursor;
  }

  return null;
}

function resolveNextPage(payload) {
  const nextPage =
    payload?.nextPage ||
    payload?.meta?.nextPage ||
    payload?.pagination?.nextPage;

  if (typeof nextPage === "number" && Number.isFinite(nextPage)) {
    return nextPage;
  }

  if (typeof nextPage === "string" && nextPage.trim() !== "") {
    const parsed = Number.parseInt(nextPage, 10);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  const currentPage =
    payload?.meta?.page ||
    payload?.meta?.currentPage ||
    payload?.pagination?.page ||
    payload?.pagination?.currentPage;

  const totalPages =
    payload?.meta?.totalPages || payload?.pagination?.totalPages;

  if (
    typeof currentPage === "number" &&
    Number.isFinite(currentPage) &&
    (!totalPages || currentPage < totalPages)
  ) {
    return currentPage + 1;
  }

  return null;
}

function resolveHasMore(payload, receivedCount) {
  if (!payload || typeof payload !== "object") {
    return receivedCount >= PAGE_SIZE;
  }

  const hasMore =
    payload?.hasMore ??
    payload?.has_more ??
    payload?.meta?.hasMore ??
    payload?.meta?.has_more ??
    payload?.pagination?.hasMore ??
    payload?.pagination?.has_more;

  if (typeof hasMore === "boolean") {
    return hasMore;
  }

  const isEnd = payload?.isEnd ?? payload?.meta?.isEnd ?? payload?.pagination?.isEnd;
  if (typeof isEnd === "boolean") {
    return !isEnd;
  }

  if (payload?.links?.next) {
    return true;
  }

  if (
    typeof payload?.meta?.totalPages === "number" &&
    typeof payload?.meta?.currentPage === "number"
  ) {
    return payload.meta.currentPage < payload.meta.totalPages;
  }

  if (
    typeof payload?.pagination?.totalPages === "number" &&
    typeof payload?.pagination?.currentPage === "number"
  ) {
    return payload.pagination.currentPage < payload.pagination.totalPages;
  }

  return receivedCount >= PAGE_SIZE;
}

function safeJson(response) {
  return response
    .text()
    .then((text) => {
      if (!text) {
        return {};
      }
      try {
        return JSON.parse(text);
      } catch (error) {
        console.warn("Failed to parse JSON response", error);
        return {};
      }
    })
    .catch(() => ({}));
}

function createUrl(options = {}) {
  const url = new URL(FEED_ENDPOINT, window.location.origin);

  if (options.cursor) {
    url.searchParams.set("cursor", options.cursor);
  } else if (options.page) {
    url.searchParams.set("page", options.page);
  }

  url.searchParams.set("limit", PAGE_SIZE);
  return url.toString();
}

function normalizeUrl(maybeUrl) {
  try {
    return new URL(maybeUrl, window.location.origin).toString();
  } catch (error) {
    return null;
  }
}

function findCardByKey(key) {
  if (!key) {
    return null;
  }

  const selectorKey = escapeForSelector(String(key));
  return memesGrid.querySelector(`[data-meme-key="${selectorKey}"]`);
}

function escapeForSelector(value) {
  if (window.CSS && typeof window.CSS.escape === "function") {
    return window.CSS.escape(value);
  }

  return value.replace(/[^\w-]/g, (char) => `\\${char}`);
}

function getMemeKey(meme) {
  if (!meme || typeof meme !== "object") {
    return null;
  }

  return (
    meme.id ??
    meme.uuid ??
    meme.slug ??
    meme.identifier ??
    meme._id ??
    meme.guid ??
    meme.externalId ??
    meme.reference ??
    (meme.imageUrl ? `image:${meme.imageUrl}` : null) ??
    (meme.url ? `url:${meme.url}` : null) ??
    null
  );
}

function resolveIdentifier(meme) {
  if (!meme || typeof meme !== "object") {
    return null;
  }

  const candidates = [
    meme.id,
    meme.uuid,
    meme.slug,
    meme.identifier,
    meme._id,
    meme.guid,
    meme.externalId,
    meme.reference,
  ];

  for (const candidate of candidates) {
    if (
      (typeof candidate === "string" && candidate.trim() !== "") ||
      (typeof candidate === "number" && Number.isFinite(candidate))
    ) {
      return candidate;
    }
  }

  return null;
}

function resolveImageSource(meme) {
  if (!meme || typeof meme !== "object") {
    return "";
  }

  return (
    meme.imageUrl ||
    meme.image ||
    meme.url ||
    meme.mediaUrl ||
    meme.src ||
    ""
  );
}

function resolveCaption(meme) {
  if (!meme || typeof meme !== "object") {
    return "Untitled meme";
  }

  return meme.caption || meme.title || meme.description || "Untitled meme";
}

function resolveAltText(meme, caption) {
  if (!meme || typeof meme !== "object") {
    return caption || "Meme image";
  }

  return meme.alt || meme.altText || caption || "Meme image";
}

function normalizeScore(score) {
  if (typeof score === "number" && Number.isFinite(score)) {
    return score;
  }

  if (typeof score === "string" && score.trim() !== "") {
    const parsed = Number.parseInt(score, 10);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return 0;
}

function resolveScoreFromPayload(payload) {
  if (typeof payload === "number") {
    return payload;
  }

  if (!payload || typeof payload !== "object") {
    return undefined;
  }

  if (typeof payload.score === "number") {
    return payload.score;
  }

  if (typeof payload.newScore === "number") {
    return payload.newScore;
  }

  if (typeof payload.updatedScore === "number") {
    return payload.updatedScore;
  }

  if (payload.data) {
    if (typeof payload.data === "number") {
      return payload.data;
    }
    if (typeof payload.data.score === "number") {
      return payload.data.score;
    }
    if (Array.isArray(payload.data) && typeof payload.data[0]?.score === "number") {
      return payload.data[0].score;
    }
  }

  if (payload.meme && typeof payload.meme.score === "number") {
    return payload.meme.score;
  }

  return undefined;
}

function getIdentifierForRequest(memeState) {
  if (!memeState) {
    return null;
  }

  const isUsable = (value) =>
    (typeof value === "string" && value.trim() !== "") ||
    (typeof value === "number" && Number.isFinite(value));

  if (isUsable(memeState.id)) {
    return memeState.id;
  }

  if (isUsable(memeState.key) && typeof memeState.key === "string") {
    if (!memeState.key.startsWith("image:") && !memeState.key.startsWith("url:")) {
      return memeState.key;
    }
  }

  return null;
}

function buildVoteUrl(identifier) {
  if (!identifier) {
    return VOTE_ENDPOINT_TEMPLATE.replace("/{id}", "").replace("{id}", "");
  }

  return VOTE_ENDPOINT_TEMPLATE.replace("{id}", encodeURIComponent(identifier));
}

function showStatus(message, variant = "info") {
  if (!feedStatus) {
    return;
  }

  feedStatus.textContent = message;
  feedStatus.dataset.variant = variant;
  feedStatus.hidden = false;
}

function hideStatus() {
  if (!feedStatus) {
    return;
  }

  feedStatus.textContent = "";
  feedStatus.dataset.variant = "";
  feedStatus.hidden = true;
}

function setLoaderState(active) {
  if (!feedLoader) {
    return;
  }

  feedLoader.dataset.state = active ? "visible" : "hidden";
}

function showEndState(visible) {
  if (!feedEnd) {
    return;
  }

  feedEnd.dataset.state = visible ? "visible" : "hidden";
}
