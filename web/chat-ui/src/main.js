const apiBase = import.meta.env.VITE_CHAT_API_URL || "";

const app = document.getElementById("app");
app.innerHTML = `
  <main style="max-width:42rem;margin:1.5rem auto;font-family:system-ui,sans-serif;">
    <h1 style="font-size:1.25rem;">Advisor pre-booking (text)</h1>
    <p style="color:#444;font-size:0.9rem;">Phase 5 UI — same runtime as pytest. Voice controls land here in Phase 6.</p>
    <div id="thread" style="border:1px solid #ddd;border-radius:8px;padding:1rem;min-height:12rem;background:#fafafa;white-space:pre-wrap;"></div>
    <form id="f" style="margin-top:0.75rem;display:flex;gap:0.5rem;">
      <input id="text" type="text" autocomplete="off" placeholder="Type a message…" style="flex:1;padding:0.5rem 0.65rem;" />
      <button type="submit">Send</button>
    </form>
    <p id="state" style="margin-top:0.5rem;font-size:0.8rem;color:#666;"></p>
  </main>
`;

const thread = document.getElementById("thread");
const stateEl = document.getElementById("state");
const form = document.getElementById("f");
const input = document.getElementById("text");

const sessionId = `web-${Math.random().toString(36).slice(2, 10)}`;

function append(role, text) {
  const prefix = role === "user" ? "You: " : "Assistant:\n";
  thread.textContent += (thread.textContent ? "\n\n" : "") + prefix + text;
  thread.scrollTop = thread.scrollHeight;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  append("user", text);
  input.value = "";

  const url = apiBase ? `${apiBase.replace(/\/$/, "")}/api/chat/message` : "/api/chat/message";
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, text }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || res.statusText);
    }
    const data = await res.json();
    stateEl.textContent = `state: ${data.state}`;
    for (const m of data.messages || []) {
      append("assistant", m);
    }
  } catch (err) {
    append("assistant", `[Error] ${err instanceof Error ? err.message : String(err)}`);
  }
});

append("assistant", "Send “hello” to start. (Ensure the Python API is running on port 8000 or set VITE_CHAT_API_URL.)");
