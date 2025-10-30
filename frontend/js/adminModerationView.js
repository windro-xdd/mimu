import {
  fetchPendingSubmissions,
  approveSubmission,
  rejectSubmission,
} from "./api.js";
import { notifyError, notifyInfo, notifySuccess } from "./notifications.js";

const STATUS_PENDING = "pending";
const STATUS_PROCESSING = "processing";

export function mountAdminModeration(rootElement) {
  if (!rootElement) {
    throw new Error("Root element is required to mount admin moderation view");
  }

  const state = {
    loading: true,
    error: null,
    submissions: [],
  };

  const section = document.createElement("section");
  section.className = "section";
  section.innerHTML = `
    <div class="section__header">
      <h2 class="section__title">Pending submissions</h2>
      <p class="section__subtitle">Review user uploads, approve standout content, or reject items that violate policy.</p>
    </div>
    <div class="table-wrapper" data-role="table-wrapper"></div>
  `;

  rootElement.innerHTML = "";
  rootElement.appendChild(section);

  const tableWrapper = section.querySelector('[data-role="table-wrapper"]');

  function render() {
    tableWrapper.innerHTML = "";

    if (state.loading) {
      tableWrapper.appendChild(renderLoader());
      return;
    }

    if (state.error) {
      tableWrapper.appendChild(renderError(state.error));
      return;
    }

    if (!state.submissions.length) {
      tableWrapper.appendChild(renderEmpty());
      return;
    }

    tableWrapper.appendChild(renderTable(state.submissions));
  }

  function renderLoader() {
    const wrapper = document.createElement("div");
    wrapper.className = "empty-state";
    wrapper.innerHTML = `
      <span class="loader">
        <span class="loader__spinner" aria-hidden="true"></span>
        Loading pending submissions...
      </span>
    `;
    return wrapper;
  }

  function renderError(error) {
    const wrapper = document.createElement("div");
    wrapper.className = "error-state";
    const message = error?.message || "Unable to load moderation queue.";
    wrapper.innerHTML = `
      <strong>Something went wrong.</strong>
      <div>${message}</div>
      <button type="button" class="button button--approve" data-role="retry">Retry</button>
    `;

    wrapper.querySelector('[data-role="retry"]').addEventListener("click", () => {
      loadSubmissions();
    });

    return wrapper;
  }

  function renderEmpty() {
    const wrapper = document.createElement("div");
    wrapper.className = "empty-state";
    wrapper.innerHTML = `
      <h3>You're all caught up</h3>
      <p>No pending submissions right now. New uploads will appear here automatically.</p>
    `;
    return wrapper;
  }

  function renderTable(submissions) {
    const table = document.createElement("table");
    table.className = "pending-table";
    table.setAttribute("aria-describedby", "pending-submissions-caption");

    table.innerHTML = `
      <caption id="pending-submissions-caption" class="sr-only">Pending submissions awaiting moderation</caption>
      <thead>
        <tr>
          <th scope="col">Uploader</th>
          <th scope="col">Caption</th>
          <th scope="col">Preview</th>
          <th scope="col">Submitted</th>
          <th scope="col"><span class="sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody></tbody>
    `;

    const tbody = table.querySelector("tbody");

    submissions.forEach((submission) => {
      const row = document.createElement("tr");
      row.dataset.submissionId = submission.id;

      const disabled = submission.status === STATUS_PROCESSING;
      const caption = submission.caption || "—";
      const emailHtml = submission.uploaderEmail
        ? `<div class="time">${escapeHtml(submission.uploaderEmail)}</div>`
        : "";

      row.innerHTML = `
        <td>
          <div>
            <strong>${escapeHtml(submission.uploader)}</strong>
            ${emailHtml}
          </div>
        </td>
        <td class="caption">${escapeHtml(caption)}</td>
        <td>${renderPreview(submission)}</td>
        <td class="time">${formatTimestamp(submission.submittedAt)}</td>
        <td>
          <div class="actions">
            <button
              type="button"
              class="button button--approve"
              data-action="approve"
              data-id="${submission.id}"
              ${disabled ? "disabled" : ""}
            >Approve</button>
            <button
              type="button"
              class="button button--reject"
              data-action="reject"
              data-id="${submission.id}"
              ${disabled ? "disabled" : ""}
            >Reject</button>
          </div>
        </td>
      `;

      tbody.appendChild(row);
    });

    return table;
  }

  tableWrapper.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;

    const { action, id } = button.dataset;
    if (!id || !action) return;

    handleModeration(action, id);
  });

  async function handleModeration(action, submissionId) {
    const submissionIndex = state.submissions.findIndex((item) => item.id === submissionId);
    if (submissionIndex === -1) {
      return;
    }

    const submission = state.submissions[submissionIndex];
    if (submission.status === STATUS_PROCESSING) {
      return;
    }

    state.submissions[submissionIndex] = {
      ...submission,
      status: STATUS_PROCESSING,
    };
    render();

    const dismiss = notifyInfo(
      `${action === "approve" ? "Approving" : "Rejecting"} “${submission.caption || submission.id}”...`,
      0,
    );

    try {
      if (action === "approve") {
        await approveSubmission(submission.id);
      } else {
        await rejectSubmission(submission.id);
      }

      dismiss();
      notifySuccess(
        `Submission “${submission.caption || submission.id}” ${action === "approve" ? "approved" : "rejected"}.`,
      );

      state.submissions.splice(submissionIndex, 1);
      render();
    } catch (error) {
      dismiss();
      notifyError(error?.message || "Unable to update submission. Please try again.");
      state.submissions[submissionIndex] = {
        ...submission,
        status: STATUS_PENDING,
      };
      render();
    }
  }

  async function loadSubmissions() {
    state.loading = true;
    state.error = null;
    render();

    try {
      const payload = await fetchPendingSubmissions();
      state.submissions = normalizeSubmissions(payload);
    } catch (error) {
      state.error = error;
    } finally {
      state.loading = false;
      render();
    }
  }

  render();
  loadSubmissions();
}

function normalizeSubmissions(payload) {
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.results)
    ? payload.results
    : Array.isArray(payload?.items)
    ? payload.items
    : Array.isArray(payload?.pending)
    ? payload.pending
    : [];

  return list
    .map((entry) => mapSubmission(entry))
    .filter(Boolean)
    .map((submission) => ({ ...submission, status: STATUS_PENDING }));
}

function mapSubmission(entry) {
  if (!entry) return null;

  const id = entry.id ?? entry.submissionId ?? entry.assetId ?? entry.uuid ?? entry.reference;
  if (id === undefined || id === null) {
    return null;
  }

  const uploader =
    entry.uploader?.name ??
    entry.uploaderName ??
    entry.uploadedBy ??
    entry.user?.name ??
    entry.user?.username ??
    entry.user ??
    "Unknown uploader";

  const uploaderEmail =
    entry.uploader?.email ?? entry.uploaderEmail ?? entry.user?.email ?? entry.email ?? "";

  const caption = entry.caption ?? entry.description ?? entry.title ?? "";
  const previewUrl =
    entry.previewUrl ?? entry.thumbnailUrl ?? entry.imageUrl ?? entry.preview_image ?? entry.preview;
  const submittedAt = entry.submittedAt ?? entry.createdAt ?? entry.timestamp ?? entry.created_at;

  return {
    id: String(id),
    uploader,
    uploaderEmail,
    caption,
    previewUrl,
    submittedAt,
  };
}

function renderPreview(submission) {
  if (!submission.previewUrl) {
    return `<div class="time">No preview</div>`;
  }
  const escapedCaption = escapeHtml(submission.caption || "Preview image");
  const escapedSrc = escapeAttribute(submission.previewUrl);
  return `<img src="${escapedSrc}" alt="Preview for ${escapedCaption}" />`;
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

function escapeAttribute(value) {
  if (value === undefined || value === null) return "";
  return escapeHtml(value).replace(/`/g, "&#96;");
}

function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return escapeHtml(value);
  }

  const datePart = date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const timePart = date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  return `${datePart} • ${timePart}`;
}
