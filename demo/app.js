/**
 * Laplace — Chat App Logic v2
 *
 * 对话式交互：发送消息 → 调用后端 API → 渲染 AI 响应 + 从者卡片
 */

const API_URL = "http://localhost:8000/api/chat";

// === Class Display Names ===
const CLASS_NAMES = {
  saber: "Saber", archer: "Archer", lancer: "Lancer",
  rider: "Rider", caster: "Caster", assassin: "Assassin",
  berserker: "Berserker", ruler: "Ruler", avenger: "Avenger",
  moonCancer: "Moon Cancer", alterEgo: "Alter Ego",
  foreigner: "Foreigner", pretender: "Pretender",
  shielder: "Shielder", beast: "Beast",
};

// === DOM ===
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const modelName = document.getElementById("model-name");
const chatContainer = document.getElementById("chat-container");

// === State ===
let isProcessing = false;

// === Send Message ===
async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text || isProcessing) return;

  isProcessing = true;
  sendBtn.disabled = true;
  chatInput.value = "";

  // Render user message
  appendMessage("user", text);

  // Show typing indicator
  const typingEl = appendTypingIndicator();

  try {
    const resp = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!resp.ok) throw new Error(`服务器错误 (${resp.status})`);

    const data = await resp.json();

    // Remove typing indicator
    typingEl.remove();

    // Update model badge
    if (data.model && data.model !== "error") {
      modelName.textContent = data.model;
    }

    // Render assistant response
    appendAssistantResponse(data);

  } catch (err) {
    typingEl.remove();
    appendMessage("assistant", `⚠️ 请求失败: ${err.message}\n\n请确保后端服务已启动 (uvicorn server.main:app)`, true);
  } finally {
    isProcessing = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// === Append User/Assistant Message ===
function appendMessage(role, text, isError = false) {
  const msg = document.createElement("div");
  msg.className = `message ${role}-message`;

  const avatar = role === "user" ? "👤" : "⧫";

  msg.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-content">
      <div class="message-bubble ${isError ? 'error-bubble' : ''}">
        <p>${escapeHtml(text)}</p>
      </div>
    </div>
  `;

  chatMessages.appendChild(msg);
  scrollToBottom();
}

// === Append Assistant Response with Cards ===
function appendAssistantResponse(data) {
  const msg = document.createElement("div");
  msg.className = "message assistant-message";

  let cardsHtml = "";
  if (data.servants && data.servants.length > 0) {
    cardsHtml = `<div class="chat-cards-grid">
      ${data.servants.map((s, i) => createCardHtml(s, i)).join("")}
    </div>`;
  }

  // 如果引入了 marked，则解析 Markdown，否则兜底安全转义
  const replyHtml = typeof marked !== 'undefined' ? marked.parse(data.reply) : `<p>${escapeHtml(data.reply)}</p>`;

  msg.innerHTML = `
    <div class="message-avatar">⧫</div>
    <div class="message-content">
      <div class="message-bubble">
        <div class="markdown-body">${replyHtml}</div>
        ${cardsHtml}
      </div>
    </div>
  `;

  chatMessages.appendChild(msg);
  scrollToBottom();
}

// === Create Card HTML ===
function createCardHtml(servant, index) {
  const stars = getStars(servant.rarity);
  const className = CLASS_NAMES[servant.className] || servant.className;

  // 获取最大自充值显示
  let chargeDisplay = "";
  if (servant.npCharges && servant.npCharges.length > 0) {
    const charges = servant.npCharges.map(c => `${c.chargePercent}%`).join("+");
    chargeDisplay = charges;
  } else if (servant.maxSelfCharge) {
    chargeDisplay = `${servant.maxSelfCharge}%`;
  }

  return `
    <div class="chat-card rarity-${servant.rarity}" style="animation-delay: ${Math.min(index * 20, 400)}ms">
      <div class="chat-card-face">
        <img src="${servant.faceUrl}" alt="${servant.name}" loading="lazy"
             onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 42 42%22><rect fill=%22%23191c3a%22 width=%2242%22 height=%2242%22/><text x=%2221%22 y=%2225%22 text-anchor=%22middle%22 fill=%22%235c5a6e%22 font-size=%2212%22>?</text></svg>'">
        <div class="chat-card-face-border"></div>
      </div>
      <div class="chat-card-info">
        <div class="chat-card-name" title="${servant.aliasCN || servant.name}">${servant.aliasCN || servant.name}</div>
        <div class="chat-card-meta">
          <span class="chat-card-stars">${stars}</span>
          <span>${className}</span>
        </div>
      </div>
      ${chargeDisplay ? `<div class="chat-card-charge">${chargeDisplay}</div>` : ""}
    </div>
  `;
}

// === Typing Indicator ===
function appendTypingIndicator() {
  const msg = document.createElement("div");
  msg.className = "message assistant-message";
  msg.innerHTML = `
    <div class="message-avatar">⧫</div>
    <div class="message-content">
      <div class="message-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>
  `;
  chatMessages.appendChild(msg);
  scrollToBottom();
  return msg;
}

// === Helpers ===
function getStars(rarity) {
  if (rarity === 0) return "☆";
  return "★".repeat(rarity);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  });
}

// === Event Listeners ===
sendBtn.addEventListener("click", sendMessage);

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Suggestion chips
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("chip")) {
    chatInput.value = e.target.dataset.query;
    sendMessage();
  }
});

// Focus input on load
document.addEventListener("DOMContentLoaded", () => {
  chatInput.focus();
});
