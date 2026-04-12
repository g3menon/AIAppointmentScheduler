import "./style.css";

const API_BASE = import.meta.env.VITE_CHAT_API_URL || "";
const USE_WEB_SPEECH = import.meta.env.VITE_USE_WEB_SPEECH !== "false";
const SPEECH_LANG = import.meta.env.VITE_SPEECH_LANG || "en-IN";

let sessionId = `web-${crypto.randomUUID().slice(0, 8)}`;
let lastSession = null;
let sending = false;

const app = document.getElementById("app");

app.innerHTML = `
  <header class="app-header">
    <div class="app-header__brand">
      <span class="app-header__dot" aria-hidden="true"></span>
      <div>
        <h1 class="app-header__title">Advisor assistant</h1>
        <p class="app-header__subtitle">Informational scheduling · not investment advice</p>
      </div>
    </div>
    <div class="app-header__meta">
      <span class="session-pill" id="session-pill" title="Session id"></span>
      <button type="button" class="btn-ghost btn-new" id="btn-new-chat" title="Start fresh">New chat</button>
    </div>
  </header>

  <main class="chat-main">
    <div class="chat-messages" id="messages" aria-live="polite"></div>

    <section class="starter-panel" id="starter-panel" hidden>
      <div class="starter-panel__head">
        <span class="starter-panel__kicker">Get started</span>
        <h2 class="starter-panel__title">What would you like to do?</h2>
        <p class="starter-panel__hint">Tap a button or use the mic to choose an option.</p>
      </div>
      <div class="chip-grid" id="intent-preview"></div>
    </section>

    <div class="quick-replies" id="quick-replies" hidden></div>

    <div class="composer">
      <div class="voice-bar" id="voice-bar" aria-label="Voice controls">
        <button
          type="button"
          class="voice-btn voice-btn--mic"
          id="btn-mic"
          title="Tap to start/stop voice mode"
          aria-pressed="false"
        >
          <span class="voice-icon mic" aria-hidden="true"></span>
          <span class="voice-label">Mic</span>
        </button>
        <div class="waveform" id="waveform" aria-hidden="true" data-voice-idle="true">
          <span></span><span></span><span></span><span></span><span></span>
        </div>
        <button type="button" class="voice-btn" id="btn-speaker" disabled title="Replay last response">
          <span class="voice-icon speaker" aria-hidden="true"></span>
          <span class="voice-label">Play</span>
        </button>
        <span class="voice-phase-tag" id="voice-status">Tap mic to start voice mode</span>
      </div>

      <div class="composer__row">
        <input
          id="input"
          type="text"
          placeholder="Or type a message…"
          autocomplete="off"
          maxlength="16000"
        />
        <button type="button" class="btn-send" id="send">Send</button>
      </div>
    </div>
  </main>
`;

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const quickRepliesEl = document.getElementById("quick-replies");
const starterPanel = document.getElementById("starter-panel");
const intentPreviewEl = document.getElementById("intent-preview");
const sessionPill = document.getElementById("session-pill");
const btnNewChat = document.getElementById("btn-new-chat");
const voiceBar = document.getElementById("voice-bar");
const btnMic = document.getElementById("btn-mic");
const waveformEl = document.getElementById("waveform");
const voiceStatusEl = document.getElementById("voice-status");

let processingIndicatorEl = null;

function updateSessionPill() {
  sessionPill.textContent = sessionId;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addBubble(text, role, index = 0) {
  const wrap = document.createElement("div");
  wrap.className = `bubble-wrap bubble-wrap--${role}`;
  wrap.style.setProperty("--stagger", String(index));

  const div = document.createElement("div");
  div.className = `bubble bubble--${role}`;
  div.textContent = text;

  wrap.appendChild(div);
  messagesEl.appendChild(wrap);
  requestAnimationFrame(() => {
    wrap.classList.add("bubble-wrap--in");
    scrollToBottom();
  });
}

function removeCompletionCards() {
  messagesEl.querySelectorAll(".completion-card").forEach((el) => el.remove());
}

function renderCompletionCard(summary) {
  removeCompletionCards();
  const wrap = document.createElement("div");
  wrap.className = "bubble-wrap bubble-wrap--completion";
  const card = document.createElement("article");
  card.className = "completion-card";
  card.innerHTML = `
    <div class="completion-card__icon" aria-hidden="true">✓</div>
    <h3 class="completion-card__title">Booking complete</h3>
    <p class="completion-card__lead">${escapeHtml(summary.detail)}</p>
    <dl class="completion-card__facts">
      ${summary.slot ? `<div class="fact"><dt>Date &amp; time</dt><dd>${escapeHtml(summary.slot)}</dd></div>` : ""}
      <div class="fact"><dt>Booking code</dt><dd><code>${escapeHtml(summary.booking_code || "—")}</code></dd></div>
      <div class="fact fact--copy">
        <dt>Calendar event id</dt>
        <dd>
          <code id="copy-eid">${escapeHtml(summary.calendar_event_id)}</code>
          <button type="button" class="btn-copy" data-copy-target="copy-eid">Copy</button>
        </dd>
      </div>
      ${
        summary.gmail_draft_id
          ? `<div class="fact fact--copy"><dt>Gmail draft id</dt><dd><code id="copy-did">${escapeHtml(
              summary.gmail_draft_id,
            )}</code><button type="button" class="btn-copy" data-copy-target="copy-did">Copy</button></dd></div>`
          : ""
      }
    </dl>
    <p class="completion-card__foot">No further steps are required in this chat.</p>
  `;
  wrap.appendChild(card);
  messagesEl.appendChild(wrap);
  requestAnimationFrame(() => {
    wrap.classList.add("bubble-wrap--in");
    scrollToBottom();
  });

  card.querySelectorAll(".btn-copy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-copy-target");
      const node = document.getElementById(id);
      const text = node ? node.textContent.trim() : "";
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied";
        setTimeout(() => {
          btn.textContent = "Copy";
        }, 1600);
      } catch {
        btn.textContent = "Copy failed";
        setTimeout(() => {
          btn.textContent = "Copy";
        }, 1600);
      }
    });
  });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function clearQuickReplies() {
  quickRepliesEl.innerHTML = "";
  quickRepliesEl.hidden = true;
}

function renderQuickReplies(items) {
  clearQuickReplies();
  if (!items || items.length === 0) return;
  quickRepliesEl.hidden = false;
  const label = document.createElement("span");
  label.className = "quick-replies__label";
  label.textContent = "Next step — tap a button";
  quickRepliesEl.appendChild(label);
  const row = document.createElement("div");
  row.className = "quick-replies__row";
  row.setAttribute("role", "group");
  row.setAttribute("aria-label", "Suggested replies");
  items.forEach((item) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn-next-step";
    b.textContent = item.label;
    b.addEventListener("click", () => onQuickReply(item));
    row.appendChild(b);
  });
  quickRepliesEl.appendChild(row);
}

function renderIntentPreview(items) {
  intentPreviewEl.innerHTML = "";
  if (!items || items.length === 0) {
    starterPanel.hidden = true;
    return;
  }
  starterPanel.hidden = false;
  intentPreviewEl.setAttribute("role", "group");
  intentPreviewEl.setAttribute("aria-label", "Choose an action");
  items.forEach((item) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn-next-step btn-next-step--primary";
    b.textContent = item.label;
    b.addEventListener("click", () => onIntentPreview(item));
    intentPreviewEl.appendChild(b);
  });
}

function applyChrome(data) {
  lastSession = data.session || null;

  const showPreview =
    Array.isArray(data.intent_preview) &&
    data.intent_preview.length > 0 &&
    lastSession &&
    !lastSession.disclaimer_acknowledged;
  if (showPreview) {
    renderIntentPreview(data.intent_preview);
  } else {
    starterPanel.hidden = true;
    intentPreviewEl.innerHTML = "";
  }

  renderQuickReplies(data.quick_replies || []);

  inputEl.disabled = Boolean(lastSession && lastSession.state === "CLOSE");
  sendBtn.disabled = inputEl.disabled;
}

function scheduleCompletionIfNeeded(data) {
  removeCompletionCards();
  if (!data.booking_summary || data.booking_summary.kind !== "booking_confirmed") {
    return;
  }
  const n = data.messages?.length || 0;
  const delay = Math.max(0, (n - 1) * 70 + 120);
  window.setTimeout(() => renderCompletionCard(data.booking_summary), delay);
}

async function apiPost(text) {
  const res = await fetch(`${API_BASE}/api/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

function showProcessingIndicator() {
  if (processingIndicatorEl) return;
  const wrap = document.createElement("div");
  wrap.className = "bubble-wrap bubble-wrap--assistant bubble-wrap--processing";
  wrap.id = "processing-indicator";
  const bubble = document.createElement("div");
  bubble.className = "bubble bubble--assistant bubble--processing";
  bubble.setAttribute("role", "status");
  bubble.setAttribute("aria-live", "polite");
  bubble.innerHTML =
    '<span class="processing-text">Working on your request</span><span class="typing-dots" aria-hidden="true"><span></span><span></span><span></span></span>';
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  requestAnimationFrame(() => {
    wrap.classList.add("bubble-wrap--in");
    scrollToBottom();
  });
  processingIndicatorEl = wrap;
}

function hideProcessingIndicator() {
  if (!processingIndicatorEl) return;
  processingIndicatorEl.remove();
  processingIndicatorEl = null;
}

async function apiPostTracked(text) {
  let slowShown = false;
  const tid = window.setTimeout(() => {
    showProcessingIndicator();
    slowShown = true;
  }, 1000);
  try {
    return await apiPost(text);
  } finally {
    window.clearTimeout(tid);
    if (slowShown) hideProcessingIndicator();
  }
}

/* ─── Voice mode state ─────────────────────────────────────────────── */
let voiceModeOn = false;
let lastInputWasVoice = false;
let speechRecognition = null;
let speechSessionActive = false;
let lastSpokenMessages = [];

const btnSpeaker = document.getElementById("btn-speaker");

function setVoiceVisual(listening, statusText) {
  if (!voiceBar || !waveformEl || !btnMic || !voiceStatusEl) return;
  voiceBar.classList.toggle("voice-bar--active", listening);
  btnMic.classList.toggle("voice-btn--on", voiceModeOn);
  if (listening) {
    waveformEl.removeAttribute("data-voice-idle");
  } else {
    waveformEl.setAttribute("data-voice-idle", "true");
  }
  btnMic.setAttribute("aria-pressed", voiceModeOn ? "true" : "false");
  if (statusText != null) {
    voiceStatusEl.textContent = statusText;
    return;
  }
  if (listening) {
    voiceStatusEl.textContent = "Listening… speak now";
  } else if (voiceModeOn) {
    voiceStatusEl.textContent = "Voice mode on · waiting…";
  } else {
    voiceStatusEl.textContent = "Tap mic to start voice mode";
  }
}

function createSpeechRecognition() {
  const Ctor = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = SPEECH_LANG;
  r.continuous = false;
  r.interimResults = false;
  r.maxAlternatives = 1;
  return r;
}

let ttsKeepAlive = null;

function stopSpeaking() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  if (ttsKeepAlive) { clearInterval(ttsKeepAlive); ttsKeepAlive = null; }
}

function startTtsKeepAlive() {
  if (ttsKeepAlive) clearInterval(ttsKeepAlive);
  ttsKeepAlive = setInterval(() => {
    if (!window.speechSynthesis.speaking) {
      clearInterval(ttsKeepAlive);
      ttsKeepAlive = null;
      return;
    }
    window.speechSynthesis.pause();
    window.speechSynthesis.resume();
  }, 10000);
}

function makeUtterance(text) {
  const cleaned = text
    .replace(/\n/g, ". ")
    .replace(/https?:\/\/\S+/g, "link")
    .replace(/[_*`]/g, "");
  const utt = new SpeechSynthesisUtterance(cleaned);
  utt.lang = SPEECH_LANG;
  utt.rate = 1.0;
  return utt;
}

function speakMessages(messages, onDone) {
  if (!messages || !messages.length) { onDone?.(); return; }
  if (!("speechSynthesis" in window)) { onDone?.(); return; }

  window.speechSynthesis.cancel();

  let callbackFired = false;
  const finish = () => {
    if (callbackFired) return;
    callbackFired = true;
    onDone?.();
  };

  setTimeout(() => {
    if (callbackFired) return;
    messages.forEach((text, i) => {
      const utt = makeUtterance(text);
      if (i === messages.length - 1) {
        utt.onend = finish;
        utt.onerror = finish;
      }
      window.speechSynthesis.speak(utt);
    });
    startTtsKeepAlive();
    setTimeout(finish, messages.join(" ").length * 85 + 5000);
  }, 150);
}

function startListeningRound() {
  if (!voiceModeOn || speechSessionActive || sending) return;
  if (inputEl.disabled) {
    setVoiceVisual(false, "Voice mode on · session complete");
    return;
  }

  speechRecognition = createSpeechRecognition();
  if (!speechRecognition) {
    setVoiceVisual(false, "Voice not supported — use Chrome or Edge");
    voiceModeOn = false;
    return;
  }

  let capturedText = "";

  speechRecognition.onresult = (ev) => {
    stopSpeaking();
    for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
      const t = ev.results[i][0].transcript.trim();
      if (t) capturedText = t;
    }
  };

  speechRecognition.onerror = (ev) => {
    speechSessionActive = false;
    if (ev.error === "aborted") return;
    if (ev.error === "no-speech") {
      if (voiceModeOn && !inputEl.disabled) {
        setTimeout(() => startListeningRound(), 200);
      }
      return;
    }
    if (ev.error === "not-allowed") {
      setVoiceVisual(false, "Microphone blocked — allow access in browser settings");
      voiceModeOn = false;
      return;
    }
    setVoiceVisual(false, `Voice error: ${ev.error}`);
    voiceModeOn = false;
  };

  speechRecognition.onend = () => {
    speechSessionActive = false;

    if (!voiceModeOn) {
      setVoiceVisual(false);
      return;
    }

    if (capturedText && !sending && !inputEl.disabled) {
      setVoiceVisual(false, "Processing…");
      sendToApi(capturedText, { userBubble: true, userLabel: capturedText, fromVoice: true });
    } else if (voiceModeOn && !inputEl.disabled) {
      setTimeout(() => startListeningRound(), 200);
    } else {
      setVoiceVisual(false);
    }
  };

  try {
    speechRecognition.start();
    speechSessionActive = true;
    setVoiceVisual(true);
  } catch (err) {
    speechSessionActive = false;
    setTimeout(() => {
      if (voiceModeOn) startListeningRound();
    }, 500);
  }
}

function enableVoiceMode() {
  voiceModeOn = true;
  lastInputWasVoice = true;
  stopSpeaking();
  setVoiceVisual(false);
  startListeningRound();
}

function disableVoiceMode() {
  voiceModeOn = false;
  lastInputWasVoice = false;
  stopSpeaking();
  if (speechRecognition && speechSessionActive) {
    try { speechRecognition.abort(); } catch { /* ignore */ }
  }
  speechSessionActive = false;
  speechRecognition = null;
  setVoiceVisual(false);
}

function resumeListeningAfterResponse() {
  if (voiceModeOn && !inputEl.disabled) {
    setTimeout(() => startListeningRound(), 300);
  }
}

if (btnMic) {
  btnMic.addEventListener("click", () => {
    if (!USE_WEB_SPEECH) {
      setVoiceVisual(false, "Voice is off (set VITE_USE_WEB_SPEECH=true to enable)");
      return;
    }
    if (voiceModeOn) {
      disableVoiceMode();
    } else {
      enableVoiceMode();
    }
  });
}

if (btnSpeaker) {
  btnSpeaker.disabled = false;
  btnSpeaker.title = "Tap to replay last response aloud";
  btnSpeaker.addEventListener("click", () => {
    if (lastSpokenMessages.length) speakMessages(lastSpokenMessages);
  });
}

if (typeof window !== "undefined") {
  window.__advisorVoice = { setListening: setVoiceVisual };
}

/* ─── Message display + TTS ────────────────────────────────────────── */

function shouldSuppressTextBubble(text, quickReplies) {
  if (!quickReplies || quickReplies.length === 0) return false;
  const labels = quickReplies.map((r) => r.label.toLowerCase());
  const lines = text.split("\n").map((l) => l.replace(/^[-·•\d)]+\s*/, "").trim().toLowerCase()).filter(Boolean);
  if (lines.length < 2) return false;
  const matchCount = lines.filter((line) => labels.some((lbl) => lbl.includes(line) || line.includes(lbl))).length;
  return matchCount >= labels.length * 0.5;
}

function appendAssistantStagger(messages, speakAloud = false, quickReplies = []) {
  const filtered = (messages || []).filter((text) => !shouldSuppressTextBubble(text, quickReplies));
  filtered.forEach((text, i) => {
    window.setTimeout(() => addBubble(text, "assistant", i), i * 70);
  });
  const toSpeak = messages || [];
  lastSpokenMessages = toSpeak;
  if (speakAloud && toSpeak.length) {
    const delay = Math.max(0, (filtered.length - 1) * 70 + 50);
    window.setTimeout(() => speakMessages(toSpeak, resumeListeningAfterResponse), delay);
  } else {
    resumeListeningAfterResponse();
  }
}

async function sendToApi(text, { userBubble = true, userLabel, fromVoice = false, fromTyping = false } = {}) {
  if (sending) return;
  sending = true;
  sendBtn.disabled = true;
  if (fromVoice) lastInputWasVoice = true;
  if (fromTyping) { lastInputWasVoice = false; disableVoiceMode(); }
  const shouldSpeak = lastInputWasVoice;
  try {
    if (userBubble) {
      addBubble(userLabel || text, "user", 0);
    }
    const data = await apiPostTracked(text);
    applyChrome(data);
    appendAssistantStagger(data.messages, shouldSpeak, data.quick_replies);
    scheduleCompletionIfNeeded(data);
  } catch {
    addBubble("Could not reach the server. Is the API running on port 8000?", "system", 0);
    resumeListeningAfterResponse();
  } finally {
    sending = false;
    if (!inputEl.disabled) sendBtn.disabled = false;
    if (!inputEl.disabled && !voiceModeOn) inputEl.focus();
  }
}

async function onQuickReply(item) {
  if (item.action === "new_session") {
    stopSpeaking();
    disableVoiceMode();
    resetChat();
    return;
  }
  await sendToApi(item.value, { userBubble: true, userLabel: item.label });
}

async function onIntentPreview(item) {
  if (sending) return;
  if (lastSession && !lastSession.disclaimer_acknowledged) {
    sending = true;
    sendBtn.disabled = true;
    const speak = lastInputWasVoice;
    try {
      const ack = await apiPostTracked("ok");
      applyChrome(ack);
      appendAssistantStagger(ack.messages, speak, ack.quick_replies);
      scheduleCompletionIfNeeded(ack);
      await new Promise((r) => setTimeout(r, (ack.messages?.length || 0) * 70 + 40));
      const data = await apiPostTracked(item.value);
      addBubble(item.label, "user", 0);
      applyChrome(data);
      appendAssistantStagger(data.messages, speak, data.quick_replies);
      scheduleCompletionIfNeeded(data);
    } catch {
      addBubble("Could not reach the server.", "system", 0);
    } finally {
      sending = false;
      sendBtn.disabled = inputEl.disabled;
      if (!inputEl.disabled && !voiceModeOn) inputEl.focus();
    }
    return;
  }
  await sendToApi(item.value, { userBubble: true, userLabel: item.label });
}

async function bootstrap() {
  updateSessionPill();
  sending = true;
  sendBtn.disabled = true;
  try {
    const data = await apiPostTracked("hello");
    applyChrome(data);
    appendAssistantStagger(data.messages, false, data.quick_replies);
    scheduleCompletionIfNeeded(data);
  } catch {
    addBubble("Could not reach the server. Start the API: uvicorn src.api.http.chat_app:app --port 8000", "system", 0);
  } finally {
    sending = false;
    sendBtn.disabled = inputEl.disabled;
    if (!voiceModeOn) inputEl.focus();
  }
}

function resetChat() {
  sessionId = `web-${crypto.randomUUID().slice(0, 8)}`;
  lastSession = null;
  lastInputWasVoice = false;
  messagesEl.innerHTML = "";
  clearQuickReplies();
  starterPanel.hidden = true;
  intentPreviewEl.innerHTML = "";
  inputEl.disabled = false;
  sendBtn.disabled = false;
  disableVoiceMode();
  updateSessionPill();
  bootstrap();
}

sendBtn.addEventListener("click", () => {
  const text = inputEl.value.trim();
  if (!text || sending || inputEl.disabled) return;
  inputEl.value = "";
  sendToApi(text, { userBubble: true, fromTyping: true });
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

btnNewChat.addEventListener("click", resetChat);

bootstrap();
