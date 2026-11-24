/**
 * E-Doot Emergency Flow Frontend Interactions:
 * - Browser SpeechSynthesis Voice Prompts (English, Hindi, Marathi)
 * - 10-Second False Alarm Cancel Window
 * - Golden Hour Survival Timer (60:00)
 * - Web Audio API CPR Metronome (110 bpm)
 * - Leaflet OpenStreetMap Hospital Marker Visualizer
 */

// Voice Synthesis Helper
function speakPrompt(text, lang = "en") {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel(); // Stop any pending speech

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95; // Slightly slower for clarity under stress
  utterance.pitch = 1.0;

  if (lang === "hi") {
    utterance.lang = "hi-IN";
  } else if (lang === "mr") {
    utterance.lang = "mr-IN";
  } else {
    utterance.lang = "en-IN";
  }

  window.speechSynthesis.speak(utterance);
}

// 10-Second False Alarm Cancel Timer
function initCancelWindow(durationSeconds = 10, progressBarId = "cancelProgress", countdownTextId = "cancelCountdown", cancelFormId = "cancelForm") {
  let remaining = durationSeconds;
  const progressBar = document.getElementById(progressBarId);
  const countdownText = document.getElementById(countdownTextId);

  if (!progressBar || !countdownText) return;

  const interval = setInterval(() => {
    remaining -= 1;
    const percent = (remaining / durationSeconds) * 100;
    progressBar.style.width = percent + "%";
    countdownText.innerText = `${remaining}s`;

    if (remaining <= 0) {
      clearInterval(interval);
      countdownText.innerText = "Locked";
      progressBar.style.width = "0%";
      const cancelNotice = document.getElementById("cancelWindowNotice");
      if (cancelNotice) {
        cancelNotice.innerHTML = "<em>False-alarm cancel window passed. Emergency teams alerted.</em>";
      }
    }
  }, 1000);
}

// Golden Hour Survival Timer (60:00 countdown)
function initGoldenHourTimer(timerElementId = "goldenHourTimer", initialMinutes = 60) {
  const el = document.getElementById(timerElementId);
  if (!el) return;

  let totalSeconds = initialMinutes * 60;
  const interval = setInterval(() => {
    if (totalSeconds <= 0) {
      clearInterval(interval);
      el.innerText = "00:00";
      return;
    }
    totalSeconds -= 1;
    const mins = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const secs = String(totalSeconds % 60).padStart(2, "0");
    el.innerText = `${mins}:${secs}`;
  }, 1000);
}

// Web Audio API CPR Metronome (110 bpm rhythmic pulse for chest compressions)
let audioCtx = null;
let metronomeInterval = null;
let isMetronomePlaying = false;

function toggleCprMetronome(btnId = "metronomeBtn", bpm = 110) {
  const btn = document.getElementById(btnId);
  if (!btn) return;

  if (isMetronomePlaying) {
    clearInterval(metronomeInterval);
    isMetronomePlaying = false;
    btn.innerHTML = "▶️ Start CPR Beat (110 BPM)";
    btn.classList.remove("active-beat");
    return;
  }

  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }

  const intervalMs = (60 / bpm) * 1000;
  isMetronomePlaying = true;
  btn.innerHTML = "⏹️ Stop CPR Beat";
  btn.classList.add("active-beat");

  function playTick() {
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.value = 880; // High pitch clean beep
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.08);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.08);

    // Pulse button animation
    btn.style.transform = "scale(1.06)";
    setTimeout(() => { btn.style.transform = "scale(1)"; }, 60);
  }

  playTick();
  metronomeInterval = setInterval(playTick, intervalMs);
}
