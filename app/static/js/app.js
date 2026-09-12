(function () {
  function scrollMessages() {
    // Keep the newest assistant response visible after HTMX appends a fragment.
    const messages = document.getElementById("messages");
    if (messages) messages.scrollTop = messages.scrollHeight;
  }

  function clearInputAndScroll() {
    const input = document.getElementById("message-input");
    if (input) input.value = "";
    const emptyState = document.querySelector(".empty-state");
    // Remove the first-use prompt once the conversation contains a response.
    if (emptyState) emptyState.remove();
    scrollMessages();
  }

  function openHistoryPanel() {
    const overlay = document.getElementById("history-overlay");
    if (overlay) overlay.classList.add("open");
  }

  function closeHistoryPanel() {
    const overlay = document.getElementById("history-overlay");
    if (overlay) overlay.classList.remove("open");
  }

  document.addEventListener("DOMContentLoaded", function () {
    scrollMessages();

    const fileInput = document.getElementById("file-input");
    if (fileInput) {
      fileInput.addEventListener("change", function () {
        const fileName = document.getElementById("file-name");
        if (fileName) {
          // Show the selected display name before the multipart request starts.
          fileName.textContent =
            fileInput.files && fileInput.files[0]
              ? "\uD83D\uDCCE " + fileInput.files[0].name
              : "";
        }
      });
    }

    const input = document.getElementById("message-input");
    if (input) {
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          const form = document.getElementById("chat-form");
          // Enter submits; Shift+Enter remains available for multi-line prompts.
          if (form && window.htmx) window.htmx.trigger(form, "submit");
        }
      });
    }
  });

  window.scrollMessages = scrollMessages;
  window.clearInputAndScroll = clearInputAndScroll;
  window.openHistoryPanel = openHistoryPanel;
  window.closeHistoryPanel = closeHistoryPanel;
})();