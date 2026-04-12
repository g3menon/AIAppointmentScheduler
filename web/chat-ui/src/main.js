import "./style.css";

const API_BASE = import.meta.env.VITE_CHAT_API_URL || "";
/** Set VITE_USE_WEB_SPEECH=false to disable browser speech recognition on the mic. */
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
        <p class="starter-panel__hint">Tap a button below — if the disclaimer is still pending, we acknowledge it for you automatically.</p>
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
          title="Hold to speak (browser speech recognition). Release to send."
          aria-pressed="false"
        >
          <span class="voice-icon mic" aria-hidden="true"></span>
          <span class="voice-label">Mic</span>
        </button>
        <div class="waveform" id="waveform" aria-hidden="true" data-voice-idle="true">
          <span></span><span></span><span></span><span></span><span></span>
        </div>
        <button type="button" class="voice-btn" id="btn-speaker" disabled title="Playback after Phase 6 TTS">
          <span class="voice-icon speaker" aria-hidden="true"></span>
          <span class="voice-label">Play</span>
        </button>
        <span class="voice-phase-tag" id="voice-status">Hold mic to speak · release to send</span>
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

function setVoiceListening(active, statusText) {
  if (!voiceBar || !waveformEl || !btnMic || !voiceStatusEl) return;
  voiceBar.classList.toggle("voice-bar--active", active);
  if (active) {
    waveformEl.removeAttribute("data-voice-idle");
  } else {
    waveformEl.setAttribute("data-voice-idle", "true");
  }
  btnMic.setAttribute("aria-pressed", active ? "true" : "false");
  if (statusText != null) {
    voiceStatusEl.textContent = statusText;
    return;
  }
  voiceStatusEl.textContent = active
    ? "Listening… release when done"
    : "Hold mic to speak · release to send";
}

/** Web Speech API (Chrome/Edge). Sends transcript to the same chat API as typing. */
function createSpeechRecognition() {
  const Ctor = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
  if (!Ctor) return null;
  const r = new Ctor();
  r.lang = SPEECH_LANG;
  r.continuous = true;
  r.interimResults = true;
  r.maxAlternatives = 1;
  return r;
}

let speechRecognition = null;
let speechFinalChunks = [];
let speechSessionActive = false;

function bindVoiceMic() {
  if (!btnMic) return;

  const releaseCapture = (e) => {
    try {
      if (e?.pointerId != null && btnMic.hasPointerCapture(e.pointerId)) {
        btnMic.releasePointerCapture(e.pointerId);
      }
    } catch {
      /* ignore */
    }
  };

  const stopVisualOnly = (e) => {
    setVoiceListening(false);
    releaseCapture(e);
  };

  const onPointerUp = (e) => {
    if (!USE_WEB_SPEECH) {
      stopVisualOnly(e);
      return;
    }
    releaseCapture(e);
    if (speechRecognition && speechSessionActive) {
      try {
        speechRecognition.stop();
      } catch {
        /* ignore */
      }
    } else {
      setVoiceListening(false);
    }
  };

  btnMic.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 && e.pointerType === "mouse") return;
    if (inputEl.disabled || sending) return;
    e.preventDefault();
    try {
      btnMic.setPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }

    if (!USE_WEB_SPEECH) {
      setVoiceListening(false, "Voice input is off (remove VITE_USE_WEB_SPEECH=false to enable)");
      return;
    }

    if (!speechRecognition) {
      speechRecognition = createSpeechRecognition();
    }
    if (!speechRecognition) {
      setVoiceListening(
        false,
        "Voice not supported here — use Chrome or Edge, or type your message",
      );
      return;
    }

    speechFinalChunks = [];
    speechRecognition.onresult = (ev) => {
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        if (ev.results[i].isFinal) {
          const t = ev.results[i][0].transcript.trim();
          if (t) speechFinalChunks.push(t);
        }
      }
    };
    speechRecognition.onerror = (ev) => {
      if (ev.error === "aborted") return;
      const msg =
        ev.error === "not-allowed"
          ? "Microphone blocked — allow access in the browser address bar"
          : `Voice error: ${ev.error}`;
      setVoiceListening(false, msg);
      speechSessionActive = false;
    };
    speechRecognition.onend = () => {
      speechSessionActive = false;
      setVoiceListening(false);
      const text = speechFinalChunks.join(" ").trim();
      speechFinalChunks = [];
      if (text && !sending && !inputEl.disabled) {
        sendToApi(text, { userBubble: true, userLabel: text, fromVoice: true });
      }
    };

    try {
      speechRecognition.start();
      speechSessionActive = true;
      setVoiceListening(true, "Listening… release when done");
    } catch {
      setVoiceListening(false, "Could not start microphone — try again");
      speechSessionActive = false;
    }
  });

  btnMic.addEventListener("pointerup", onPointerUp);
  btnMic.addEventListener("pointercancel", onPointerUp);
  btnMic.addEventListener("lostpointercapture", () => {
    if (!speechSessionActive) setVoiceListening(false);
  });
}

bindVoiceMic();

/** Phase 6: call `window.__advisorVoice?.setListening(true)` while STT is active. */
if (typeof window !== "undefined") {
  window.__advisorVoice = { setListening: setVoiceListening };
}

let lastInputWasVoice = false;
const btnSpeaker = document.getElementById("btn-speaker");

function speakText(text) {
  if (!("speechSynthesis" in window)) return;
  const cleaned = text
    .replace(/\n/g, ". ")
    .replace(/https?:\/\/\S+/g, "link")
    .replace(/[_*`]/g, "");
  const utt = new SpeechSynthesisUtterance(cleaned);
  utt.lang = SPEECH_LANG;
  utt.rate = 1.0;
  window.speechSynthesis.speak(utt);
}

function speakMessages(messages) {
  if (!messages || !messages.length) return;
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  messages.forEach((text) => speakText(text));
}

function stopSpeaking() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

if (btnSpeaker) {
  btnSpeaker.disabled = false;
  btnSpeaker.title = "Tap to replay last response aloud";
  let lastSpoken = [];
  const origAppend = null;
  btnSpeaker.addEventListener("click", () => {
    if (lastSpoken.length) speakMessages(lastSpoken);
  });
  window.__advisorVoice.setLastSpoken = (msgs) => { lastSpoken = msgs || []; };
}

function appendAssistantStagger(messages, speakAloud = false) {
  (messages || []).forEach((text, i) => {
    window.setTimeout(() => addBubble(text, "assistant", i), i * 70);
  });
  if (speakAloud && messages?.length) {
    const delay = Math.max(0, (messages.length - 1) * 70 + 50);
    window.setTimeout(() => speakMessages(messages), delay);
  }
  if (window.__advisorVoice?.setLastSpoken) {
    window.__advisorVoice.setLastSpoken(messages);
  }
}

async function sendToApi(text, { userBubble = true, userLabel, fromVoice = false } = {}) {
  if (sending) return;
  sending = true;
  sendBtn.disabled = true;
  const shouldSpeak = fromVoice || lastInputWasVoice;
  lastInputWasVoice = fromVoice;
  try {
    if (userBubble) {
      addBubble(userLabel || text, "user", 0);
    }
    const data = await apiPostTracked(text);
    applyChrome(data);
    appendAssistantStagger(data.messages, shouldSpeak);
    scheduleCompletionIfNeeded(data);
  } catch {
    addBubble("Could not reach the server. Is the API running on port 8000?", "system", 0);
  } finally {
    sending = false;
    if (!inputEl.disabled) sendBtn.disabled = false;
    if (!inputEl.disabled) inputEl.focus();
  }
}

async function onQuickReply(item) {
  if (item.action === "new_session") {
    stopSpeaking();
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
    try {
      const ack = await apiPostTracked("ok");
      applyChrome(ack);
      appendAssistantStagger(ack.messages);
      scheduleCompletionIfNeeded(ack);
      await new Promise((r) => setTimeout(r, (ack.messages?.length || 0) * 70 + 40));
      const data = await apiPostTracked(item.value);
      addBubble(item.label, "user", 0);
      applyChrome(data);
      appendAssistantStagger(data.messages);
      scheduleCompletionIfNeeded(data);
    } catch {
      addBubble("Could not reach the server.", "system", 0);
    } finally {
      sending = false;
      sendBtn.disabled = inputEl.disabled;
      if (!inputEl.disabled) inputEl.focus();
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
    appendAssistantStagger(data.messages);
    scheduleCompletionIfNeeded(data);
  } catch {
    addBubble("Could not reach the server. Start the API: uvicorn src.api.http.chat_app:app --port 8000", "system", 0);
  } finally {
    sending = false;
    sendBtn.disabled = inputEl.disabled;
    inputEl.focus();
  }
}

function resetChat() {
  sessionId = `web-${crypto.randomUUID().slice(0, 8)}`;
  lastSession = null;
  messagesEl.innerHTML = "";
  clearQuickReplies();
  starterPanel.hidden = true;
  intentPreviewEl.innerHTML = "";
  inputEl.disabled = false;
  sendBtn.disabled = false;
  updateSessionPill();
  bootstrap();
}

sendBtn.addEventListener("click", () => {
  const text = inputEl.value.trim();
  if (!text || sending || inputEl.disabled) return;
  inputEl.value = "";
  sendToApi(text, { userBubble: true });
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

btnNewChat.addEventListener("click", resetChat);

bootstrap();
