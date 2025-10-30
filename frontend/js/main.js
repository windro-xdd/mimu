import { authContext, onAuthChange, requireRole } from "./authContext.js";
import { mountAdminModeration } from "./adminModerationView.js";

const ROUTES = {
  "/": {
    title: "Content platform",
    render: renderHome,
  },
  "/admin/pending": {
    title: "Moderation queue",
    guard: () => requireRole("admin"),
    blocked: renderBlocked,
    render: mountAdminModeration,
  },
};

const appRoot = document.getElementById("app");

function handleRouteChange() {
  if (!appRoot) {
    console.error("App root element not found");
    return;
  }

  const hash = window.location.hash || "#/";
  const path = normalizeHash(hash);
  const route = ROUTES[path];

  updateNav(hash);

  if (!route) {
    renderNotFound();
    return;
  }

  document.title = route.title ? `${route.title} · Content Platform` : "Content Platform";

  if (route.guard && !route.guard()) {
    route.blocked ? route.blocked() : renderBlocked();
    focusMain();
    return;
  }

  route.render(appRoot);
  focusMain();
}

function normalizeHash(hash) {
  if (!hash.startsWith("#")) return hash;
  const value = hash.slice(1);
  const [rawPath] = value.split("?");
  const trimmed = (rawPath || "/").trim();
  if (!trimmed) return "/";

  let normalised = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  if (normalised.length > 1 && normalised.endsWith("/")) {
    normalised = normalised.replace(/\/+$/, "");
    if (!normalised) {
      normalised = "/";
    }
  }

  return normalised || "/";
}

function renderHome() {
  appRoot.innerHTML = `
    <section class="section">
      <div class="section__header">
        <h2 class="section__title">Welcome back, ${escapeHtml(getUserName())}</h2>
        <p class="section__subtitle">Use the navigation to review pending submissions or explore additional tools as they become available.</p>
      </div>
      <p>Visit the moderation console to review uploads awaiting approval. Only administrators can access moderation tools.</p>
      <p><a class="nav__link nav__link--cta" href="#/admin/pending">Go to moderation queue</a></p>
    </section>
  `;
}

function renderBlocked() {
  appRoot.innerHTML = `
    <section class="blocked-state" role="alert">
      <h2 class="blocked-state__title">Access restricted</h2>
      <p>You need administrator permissions to view the moderation console.</p>
      <p>If you believe this is in error, please contact a system administrator.</p>
    </section>
  `;
}

function renderNotFound() {
  appRoot.innerHTML = `
    <section class="blocked-state" role="alert">
      <h2 class="blocked-state__title">Page not found</h2>
      <p>The page you are looking for doesn’t exist.</p>
      <p><a class="nav__link nav__link--cta" href="#/">Return home</a></p>
    </section>
  `;
}

function updateNav(activeHash) {
  const links = document.querySelectorAll(".nav__link");
  links.forEach((link) => {
    if (link.getAttribute("href") === activeHash) {
      link.classList.add("nav__link--active");
    } else {
      link.classList.remove("nav__link--active");
    }
  });
}

function focusMain() {
  requestAnimationFrame(() => {
    if (!appRoot) return;
    try {
      appRoot.focus({ preventScroll: true });
    } catch (error) {
      appRoot.focus();
    }
  });
}

function getUserName() {
  const user = authContext.getUser();
  if (!user) return "Guest";
  return user.name || user.email || "Team member";
}

function escapeHtml(value) {
  if (value === undefined || value === null) return "";
  const str = String(value);
  const entities = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return str.replace(/[&<>"']/g, (char) => entities[char]);
}

window.addEventListener("hashchange", handleRouteChange);

onAuthChange(() => {
  handleRouteChange();
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", handleRouteChange);
} else {
  handleRouteChange();
}
