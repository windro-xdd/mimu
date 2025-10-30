const DEFAULT_TIMEOUT = 4500;

function getContainer() {
  const container = document.getElementById("notifications");
  if (!container) {
    throw new Error("Notifications container element not found");
  }
  return container;
}

function removeNotification(element) {
  if (!element) return;
  element.classList.add("notification--closing");
  requestAnimationFrame(() => {
    element.style.opacity = "0";
    element.style.transform = "translateY(8px)";
    setTimeout(() => {
      element.remove();
    }, 250);
  });
}

export function notify({ type = "info", message, timeout = DEFAULT_TIMEOUT } = {}) {
  if (!message) return () => undefined;
  const container = getContainer();
  const element = document.createElement("div");
  element.className = `notification notification--${type}`;
  element.setAttribute("role", "alert");

  const messageSpan = document.createElement("span");
  messageSpan.className = "notification__message";
  messageSpan.textContent = message;

  const closeButton = document.createElement("button");
  closeButton.className = "notification__close";
  closeButton.setAttribute("aria-label", "Dismiss notification");
  closeButton.textContent = "×";
  closeButton.addEventListener("click", () => removeNotification(element));

  element.appendChild(messageSpan);
  element.appendChild(closeButton);
  container.appendChild(element);

  if (timeout > 0) {
    setTimeout(() => removeNotification(element), timeout);
  }

  return () => removeNotification(element);
}

export function notifySuccess(message, timeout) {
  return notify({ type: "success", message, timeout });
}

export function notifyError(message, timeout) {
  return notify({ type: "error", message, timeout });
}

export function notifyInfo(message, timeout) {
  return notify({ type: "info", message, timeout });
}
