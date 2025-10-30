const defaultHeaders = {
  Accept: "application/json",
};

async function request(url, options = {}) {
  const config = {
    credentials: "include",
    ...options,
  };

  if (config.body && typeof config.body === "object" && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
    config.headers = {
      "Content-Type": "application/json",
      ...config.headers,
    };
  }

  config.headers = {
    ...defaultHeaders,
    ...config.headers,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const errorText = await safeReadText(response);
    const error = new Error(errorText || `Request failed with status ${response.status}`);
    error.status = response.status;
    throw error;
  }

  const data = await safeReadJson(response);
  return data;
}

async function safeReadText(response) {
  try {
    return await response.text();
  } catch (error) {
    console.error("Failed to read response text", error);
    return "";
  }
}

async function safeReadJson(response) {
  const text = await safeReadText(response);
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (error) {
    console.warn("Failed to parse JSON response", error);
    return null;
  }
}

export function fetchPendingSubmissions() {
  return request("/admin/pending");
}

export function approveSubmission(submissionId) {
  return request(`/admin/pending/${encodeURIComponent(submissionId)}/approve`, {
    method: "POST",
  });
}

export function rejectSubmission(submissionId, payload = {}) {
  return request(`/admin/pending/${encodeURIComponent(submissionId)}/reject`, {
    method: "POST",
    body: payload,
  });
}
