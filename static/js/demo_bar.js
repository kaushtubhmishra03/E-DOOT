/**
 * Judge Demo Director Toolbar & Simulated SMS Drawer
 */

document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("demoBarToggle");
  const barContent = document.getElementById("demoBarContent");
  const smsDrawerBtn = document.getElementById("smsDrawerBtn");
  const smsModal = document.getElementById("smsModal");
  const smsCloseBtn = document.getElementById("smsCloseBtn");
  const smsList = document.getElementById("smsList");
  const smsBadge = document.getElementById("smsCountBadge");

  // Toggle demo dock
  if (toggleBtn && barContent) {
    toggleBtn.addEventListener("click", () => {
      barContent.classList.toggle("collapsed");
      toggleBtn.innerText = barContent.classList.contains("collapsed") ? "⚡ Demo Director ▲" : "⚡ Demo Director ▼";
    });
  }

  // Open / Close SMS Drawer
  if (smsDrawerBtn && smsModal) {
    smsDrawerBtn.addEventListener("click", () => {
      smsModal.style.display = "flex";
      fetchSmsMessages();
    });
  }

  if (smsCloseBtn && smsModal) {
    smsCloseBtn.addEventListener("click", () => {
      smsModal.style.display = "none";
    });
  }

  window.addEventListener("click", (e) => {
    if (e.target === smsModal) smsModal.style.display = "none";
  });

  // Polling simulated SMS
  async function fetchSmsMessages() {
    try {
      const res = await fetch("/api/simulated-sms");
      const data = await res.json();
      if (data.status === "success" && data.messages) {
        if (smsBadge) {
          smsBadge.innerText = data.messages.length;
          smsBadge.style.display = data.messages.length > 0 ? "inline-block" : "none";
        }
        if (smsList) {
          if (data.messages.length === 0) {
            smsList.innerHTML = `<div class="empty-state">No SMS messages sent yet. Trigger an emergency alert to see family SMS dispatch.</div>`;
          } else {
            smsList.innerHTML = data.messages.map(msg => `
              <div class="sms-card">
                <div class="sms-head">
                  <span class="sms-to">To: <strong>${escapeHtml(msg.to)}</strong></span>
                  <span class="sms-time">${escapeHtml(msg.timestamp)}</span>
                </div>
                <div class="sms-body">${escapeHtml(msg.body).replace(/\n/g, "<br>")}</div>
                <div class="sms-status">${escapeHtml(msg.status)}</div>
              </div>
            `).join("");
          }
        }
      }
    } catch (e) {
      console.error("Failed to fetch simulated SMS", e);
    }
  }

  // Poll SMS count every 5 seconds
  setInterval(fetchSmsMessages, 5000);
  fetchSmsMessages();

  function escapeHtml(str) {
    const p = document.createElement("p");
    p.appendChild(document.createTextNode(str || ""));
    return p.innerHTML;
  }
});
