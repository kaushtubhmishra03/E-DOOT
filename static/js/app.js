/**
 * E-Doot Core Application Script
 */

document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = "0";
      alert.style.transition = "opacity 0.4s ease";
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // Language switcher quick listener
  const langSelector = document.getElementById("langSelector");
  if (langSelector) {
    langSelector.addEventListener("change", (e) => {
      window.location.href = `/set-language/${e.target.value}`;
    });
  }
});
