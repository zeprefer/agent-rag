/**
 * 用户端聊天页面编排入口。
 * 负责 Agent、会话、消息和附件状态；网络访问与通用格式化逻辑放在独立模块中。
 */
import { createApiClient } from "./api-client.js";
import { escapeHtml, formatDate, normalizeApiBase } from "./ui-utils.js";

const state = {
  apiBase: localStorage.getItem("agent_user_api_base") || "http://localhost:8000/api/v1",
  token: localStorage.getItem("agent_user_token") || "",
  user: JSON.parse(localStorage.getItem("agent_user_profile") || "null"),
  agents: [],
  selectedAgentId: localStorage.getItem("agent_user_selected_agent") || "",
  sessions: [],
  selectedSessionId: localStorage.getItem("agent_user_selected_session") || "",
  messages: [],
  pendingFiles: [],
  sending: false,
};

const apiClient = createApiClient({
  getBaseUrl: () => state.apiBase,
  getToken: () => state.token,
});

const els = {
  apiBaseInput: document.querySelector("#apiBaseInput"),
  loginForm: document.querySelector("#loginForm"),
  emailInput: document.querySelector("#emailInput"),
  passwordInput: document.querySelector("#passwordInput"),
  authStatus: document.querySelector("#authStatus"),
  userPanel: document.querySelector("#userPanel"),
  userEmail: document.querySelector("#userEmail"),
  logoutButton: document.querySelector("#logoutButton"),
  agentSelect: document.querySelector("#agentSelect"),
  newSessionButton: document.querySelector("#newSessionButton"),
  refreshSessionsButton: document.querySelector("#refreshSessionsButton"),
  sessionList: document.querySelector("#sessionList"),
  sessionTitle: document.querySelector("#sessionTitle"),
  apiState: document.querySelector("#apiState"),
  messages: document.querySelector("#messages"),
  messageForm: document.querySelector("#messageForm"),
  messageInput: document.querySelector("#messageInput"),
  attachmentInput: document.querySelector("#attachmentInput"),
  pendingAttachments: document.querySelector("#pendingAttachments"),
  composerStatus: document.querySelector("#composerStatus"),
  sendButton: document.querySelector("#sendButton"),
  toast: document.querySelector("#toast"),
};

function boot() {
  els.apiBaseInput.value = state.apiBase;
  bindEvents();
  renderAuth();
  renderAgents();
  renderSessions();
  renderMessages();
  if (state.token) {
    loadAgents().then(loadSessions).catch(showError);
  }
}

function bindEvents() {
  els.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    state.apiBase = normalizeApiBase(els.apiBaseInput.value);
    localStorage.setItem("agent_user_api_base", state.apiBase);
    await login();
  });

  els.logoutButton.addEventListener("click", () => {
    state.token = "";
    state.user = null;
    state.agents = [];
    state.selectedAgentId = "";
    state.sessions = [];
    state.messages = [];
    state.pendingFiles = [];
    state.selectedSessionId = "";
    localStorage.removeItem("agent_user_token");
    localStorage.removeItem("agent_user_profile");
    localStorage.removeItem("agent_user_selected_session");
    localStorage.removeItem("agent_user_selected_agent");
    renderAuth();
    renderAgents();
    renderSessions();
    renderMessages();
    renderPendingAttachments();
    toast("已退出登录");
  });

  els.newSessionButton.addEventListener("click", () => createSession().catch(showError));
  els.refreshSessionsButton.addEventListener("click", () => loadSessions().catch(showError));

  els.agentSelect.addEventListener("change", () => {
    state.selectedAgentId = els.agentSelect.value;
    localStorage.setItem("agent_user_selected_agent", state.selectedAgentId);
  });

  els.messageForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await sendMessage().catch(showError);
  });

  els.messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      sendMessage().catch(showError);
    }
  });

  els.attachmentInput.addEventListener("change", () => {
    state.pendingFiles = [...state.pendingFiles, ...Array.from(els.attachmentInput.files || [])];
    els.attachmentInput.value = "";
    renderPendingAttachments();
  });
}

async function login() {
  setAuthStatus("正在登录…");
  const payload = {
    email: els.emailInput.value.trim(),
    password: els.passwordInput.value,
  };
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
  state.token = data.access_token;
  state.user = data.user;
  localStorage.setItem("agent_user_token", state.token);
  localStorage.setItem("agent_user_profile", JSON.stringify(state.user));
  els.passwordInput.value = "";
  setAuthStatus("");
  renderAuth();
  await loadAgents();
  await loadSessions();
  toast("登录成功");
}

async function loadAgents() {
  requireAuth();
  const data = await request("/agents?limit=100");
  state.agents = data.items || [];
  if (state.selectedAgentId && !state.agents.some((agent) => agent.id === state.selectedAgentId)) {
    state.selectedAgentId = "";
    localStorage.removeItem("agent_user_selected_agent");
  }
  renderAgents();
}

async function loadSessions() {
  requireAuth();
  const data = await request("/chat/sessions?limit=100");
  state.sessions = data.items || [];
  if (!state.sessions.some((session) => session.id === state.selectedSessionId)) {
    state.selectedSessionId = state.sessions[0]?.id || "";
  }
  if (state.selectedSessionId) {
    localStorage.setItem("agent_user_selected_session", state.selectedSessionId);
    await loadMessages(state.selectedSessionId);
  } else {
    state.messages = [];
  }
  renderSessions();
  renderMessages();
}

async function createSession(title = "知识问答") {
  requireAuth();
  const payload = { title };
  if (state.selectedAgentId) {
    payload.agent_id = state.selectedAgentId;
  }
  const session = await request("/chat/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.selectedSessionId = session.id;
  localStorage.setItem("agent_user_selected_session", session.id);
  await loadSessions();
  toast("新对话已创建");
  els.messageInput.focus();
}

async function selectSession(id) {
  state.selectedSessionId = id;
  localStorage.setItem("agent_user_selected_session", id);
  await loadMessages(id);
  renderSessions();
}

async function deleteSession(id, title) {
  requireAuth();
  if (state.sending && id === state.selectedSessionId) {
    toast("请等待当前回答完成后再删除对话");
    return;
  }
  const confirmed = window.confirm(`确定删除对话“${title}”吗？消息和附件将一并删除，此操作无法撤销。`);
  if (!confirmed) return;

  await request(`/chat/sessions/${id}`, { method: "DELETE" });
  if (id === state.selectedSessionId) {
    state.selectedSessionId = "";
    state.messages = [];
    localStorage.removeItem("agent_user_selected_session");
  }
  await loadSessions();
  toast("对话已删除");
}

async function loadMessages(sessionId) {
  if (!sessionId) {
    state.messages = [];
    renderMessages();
    return;
  }
  const data = await request(`/chat/sessions/${sessionId}/messages`);
  state.messages = data.items || [];
  renderMessages();
}

async function sendMessage() {
  requireAuth();
  const content = els.messageInput.value.trim();
  if (!content || state.sending) return;

  if (!state.selectedSessionId) {
    await createSession(content.slice(0, 80));
  }

  state.sending = true;
  renderSending();
  const filesToUpload = [...state.pendingFiles];
  const attachmentNames = filesToUpload.map((file) => file.name);
  const optimisticUserMessage = {
    id: `local-${Date.now()}`,
    role: "user",
    content,
    citations: [],
    extra_metadata: attachmentNames.length
      ? { attachments: attachmentNames.map((filename) => ({ filename, attachment_type: "pending" })) }
      : null,
    created_at: new Date().toISOString(),
  };
  state.messages = [...state.messages, optimisticUserMessage];
  els.messageInput.value = "";
  state.pendingFiles = [];
  renderPendingAttachments();
  renderMessages();

  try {
    const attachmentIds = [];
    for (const file of filesToUpload) {
      const attachment = await uploadAttachment(file);
      attachmentIds.push(attachment.id);
    }
    const response = await request(`/chat/sessions/${state.selectedSessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, attachment_ids: attachmentIds.length ? attachmentIds : null }),
    });
    state.messages = state.messages.filter((message) => message.id !== optimisticUserMessage.id);
    state.messages.push(response.user_message, response.assistant_message);
    await loadSessions();
    renderMessages();
  } catch (error) {
    state.messages = state.messages.filter((message) => message.id !== optimisticUserMessage.id);
    state.pendingFiles = filesToUpload;
    renderPendingAttachments();
    renderMessages();
    throw error;
  } finally {
    state.sending = false;
    renderSending();
  }
}

async function uploadAttachment(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request(`/chat/sessions/${state.selectedSessionId}/attachments`, {
    method: "POST",
    body: formData,
    isForm: true,
  });
}

async function request(path, options = {}) {
  return apiClient.request(path, options);
}

function renderAuth() {
  const signedIn = Boolean(state.token && state.user);
  els.userPanel.classList.toggle("hidden", !signedIn);
  els.userEmail.textContent = state.user?.email || "-";
  els.apiState.textContent = signedIn ? "已连接" : "未连接";
  els.apiState.className = `pill ${signedIn ? "good" : "neutral"}`;
}

function renderAgents() {
  const selected = state.selectedAgentId || "";
  els.agentSelect.innerHTML = `
    <option value="">默认助手</option>
    ${state.agents
      .map(
        (agent) => `
          <option value="${escapeHtml(agent.id)}" ${agent.id === selected ? "selected" : ""}>
            ${escapeHtml(agent.name)}
          </option>
        `,
      )
      .join("")}
  `;
}

function renderSessions() {
  if (!state.sessions.length) {
    els.sessionList.innerHTML = `<div class="empty-state">暂无对话，点击“新建对话”开始</div>`;
    els.sessionTitle.textContent = "企业知识助手";
    return;
  }
  els.sessionList.innerHTML = state.sessions
    .map((session) => {
      const active = session.id === state.selectedSessionId ? " active" : "";
      return `
        <div class="session-item${active}">
          <button class="session-select" type="button" data-select-session="${escapeHtml(session.id)}">
            <strong>${escapeHtml(session.title)}</strong>
            <span class="session-meta">${escapeHtml(agentName(session.agent_id))} / ${formatDate(session.updated_at)}</span>
          </button>
          <button
            class="session-delete"
            type="button"
            data-delete-session="${escapeHtml(session.id)}"
            data-session-title="${escapeHtml(session.title)}"
            title="删除对话"
            aria-label="删除对话：${escapeHtml(session.title)}"
          >删除</button>
        </div>
      `;
    })
    .join("");
  els.sessionList.querySelectorAll("[data-select-session]").forEach((button) => {
    button.addEventListener("click", () => selectSession(button.dataset.selectSession).catch(showError));
  });
  els.sessionList.querySelectorAll("[data-delete-session]").forEach((button) => {
    button.addEventListener("click", () => {
      deleteSession(button.dataset.deleteSession, button.dataset.sessionTitle).catch(showError);
    });
  });
  els.sessionTitle.textContent = currentSession()?.title || "企业知识助手";
}

function renderMessages() {
  if (!state.messages.length) {
    els.messages.innerHTML = `<div class="empty-state">开始提问吧，我会根据企业知识库为你解答</div>`;
    return;
  }
  els.messages.innerHTML = state.messages.map(renderMessage).join("");
  els.messages.scrollTop = els.messages.scrollHeight;
}

function renderMessage(message) {
  const roleLabel = message.role === "assistant" ? "知识助手" : "你";
  const citations = message.citations?.length ? renderCitations(message.citations) : "";
  const attachmentBadges = renderAttachmentBadges(message.extra_metadata?.attachments || []);
  const agentRun = message.role === "assistant" ? renderAgentRun(message.extra_metadata?.agent_run) : "";
  return `
    <article class="message ${escapeHtml(message.role)}">
      <span class="message-role">${roleLabel}</span>
      <div class="bubble">${escapeHtml(message.content)}</div>
      ${attachmentBadges}
      ${agentRun}
      ${citations}
    </article>
  `;
}

function renderAgentRun(agentRun) {
  if (!agentRun) return "";
  const calls = agentRun.tool_calls || [];
  const summary = `${agentRun.iterations || 1} 轮推理 · ${calls.length} 次工具调用`;
  return `
    <details class="agent-trace">
      <summary>Agent 执行轨迹 · ${escapeHtml(summary)}</summary>
      <div class="agent-trace-body">
        ${calls.length
          ? calls
              .map((call, index) => `
                <div class="agent-trace-step">
                  <strong>${index + 1}. ${escapeHtml(call.tool || "tool")}</strong>
                  <span>${escapeHtml(call.query || call.arguments?.query || "")}</span>
                  <small>${call.success ? "成功" : "失败"} · 命中 ${call.hit_count || 0} 条 · ${call.duration_ms || 0} ms</small>
                </div>
              `)
              .join("")
          : `<span class="citation-meta">本次回答未调用外部工具</span>`}
      </div>
    </details>
  `;
}

function renderAttachmentBadges(attachments) {
  if (!attachments.length) return "";
  return `
    <div class="attachment-badges">
      ${attachments
        .map((attachment) => `
          <span class="attachment-chip">
            <span>${escapeHtml(attachment.filename || "附件")}</span>
          </span>
        `)
        .join("")}
    </div>
  `;
}

function renderPendingAttachments() {
  if (!state.pendingFiles.length) {
    els.pendingAttachments.innerHTML = "";
    return;
  }
  els.pendingAttachments.innerHTML = state.pendingFiles
    .map((file, index) => `
      <span class="attachment-chip">
        <span>${escapeHtml(file.name)}</span>
        <button type="button" data-remove-file="${index}" title="移除附件" aria-label="移除附件">×</button>
      </span>
    `)
    .join("");
  els.pendingAttachments.querySelectorAll("[data-remove-file]").forEach((button) => {
    button.addEventListener("click", () => {
      state.pendingFiles.splice(Number(button.dataset.removeFile), 1);
      renderPendingAttachments();
    });
  });
}

function renderCitations(citations) {
  return `
    <div class="citations">
      ${citations
        .map((citation, index) => {
          const page = citation.page_number ? ` · 第 ${citation.page_number} 页` : "";
          const heading = citation.heading_path ? ` · ${escapeHtml(citation.heading_path)}` : "";
          return `
            <section class="citation">
              <div class="citation-head">
                <button type="button">参考来源 ${index + 1}</button>
                <span class="citation-meta">${Number(citation.score || 0).toFixed(3)}</span>
              </div>
              <div class="citation-meta">${escapeHtml(citation.document_title)}${page}${heading}</div>
              <blockquote>${escapeHtml(citation.quote)}</blockquote>
            </section>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderSending() {
  els.sendButton.disabled = state.sending;
  els.sendButton.textContent = state.sending ? "发送中…" : "发送";
  els.composerStatus.textContent = state.sending ? "正在上传附件并生成回答，请稍候…" : "";
}

function currentSession() {
  return state.sessions.find((session) => session.id === state.selectedSessionId) || null;
}

function agentName(agentId) {
  if (!agentId) return "默认助手";
  return state.agents.find((agent) => agent.id === agentId)?.name || "智能体";
}

function requireAuth() {
  if (!state.token) {
    throw new Error("请先登录");
  }
}

function setAuthStatus(message) {
  els.authStatus.textContent = message;
}

function showError(error) {
  const rawMessage = error instanceof Error ? error.message : String(error);
  const message = localizeError(rawMessage);
  setAuthStatus(message);
  toast(message);
  state.sending = false;
  renderSending();
}

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => els.toast.classList.add("hidden"), 3200);
}

function localizeError(message) {
  const labels = {
    "Agent not found": "未找到智能体",
    "Chat session not found": "未找到该对话",
    "Could not validate credentials": "登录凭证已失效，请重新登录",
    "Failed to fetch": "无法连接 API 服务，请检查 API 地址及服务状态",
    "Incorrect email or password": "邮箱或密码错误",
  };
  if (labels[message]) return labels[message];
  if (message.startsWith("Permission required:")) return "当前账号没有执行此操作的权限";
  return message;
}

boot();
