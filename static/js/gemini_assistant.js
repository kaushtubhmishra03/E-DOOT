/**
 * Arogya Saathi - Gemini AI Health Assistant Client
 */

document.addEventListener("DOMContentLoaded", () => {
  const triggerBtn = document.getElementById("geminiTriggerBtn");
  const modal = document.getElementById("geminiModal");
  const closeBtn = document.getElementById("geminiCloseBtn");
  const chatForm = document.getElementById("geminiChatForm");
  const queryInput = document.getElementById("geminiQueryInput");
  const chatBody = document.getElementById("geminiChatMessages");
  const quickChips = document.querySelectorAll(".quick-chip");

  if (!modal) return;

  const openModal = () => {
    modal.style.display = "flex";
    if (queryInput) queryInput.focus();
  };

  const closeModal = () => {
    modal.style.display = "none";
  };

  if (triggerBtn) triggerBtn.addEventListener("click", openModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);

  // Close on outside backdrop click
  window.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  // Quick suggestion chips
  quickChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const text = chip.getAttribute("data-query");
      if (text && queryInput) {
        queryInput.value = text;
        submitQuery(text);
      }
    });
  });

  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const query = queryInput.value.trim();
      if (!query) return;
      submitQuery(query);
    });
  }

  async function submitQuery(queryText) {
    appendUserMessage(queryText);
    queryInput.value = "";

    // Show typing loader
    const typingIndicator = appendTypingIndicator();

    try {
      const response = await fetch("/api/doubt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText })
      });
      const data = await response.json();
      typingIndicator.remove();

      if (data.is_emergency) {
        appendEmergencyWarning(data.answer);
      } else {
        appendAssistantMessage(data.answer, data.provider);
      }
    } catch (err) {
      typingIndicator.remove();
      appendAssistantMessage("⚠️ Network error. Please check your connectivity and try again.", "system");
    }
  }

  function appendUserMessage(text) {
    const div = document.createElement("div");
    div.className = "chat-msg user-msg";
    div.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function appendAssistantMessage(text, provider) {
    const div = document.createElement("div");
    div.className = "chat-msg assistant-msg";
    // Convert newlines to breaks & simple bold formatting
    const formatted = text.replace(/\n/g, "<br>").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    const providerBadge = provider === "gemini-api" ? `<span class="provider-pill">Gemini Live</span>` : `<span class="provider-pill">Local Health AI</span>`;
    div.innerHTML = `
      <div class="msg-bubble">
        ${formatted}
        <div class="msg-meta">${providerBadge}</div>
      </div>
    `;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function appendEmergencyWarning(text) {
    const div = document.createElement("div");
    div.className = "chat-msg emergency-alert-msg";
    const formatted = text.replace(/\n/g, "<br>").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    div.innerHTML = `
      <div class="msg-bubble emergency-bubble">
        ${formatted}
      </div>
    `;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function appendTypingIndicator() {
    const div = document.createElement("div");
    div.className = "chat-msg assistant-msg typing";
    div.innerHTML = `<div class="msg-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>`;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
    return div;
  }

  function escapeHtml(str) {
    const p = document.createElement("p");
    p.appendChild(document.createTextNode(str));
    return p.innerHTML;
  }
});
