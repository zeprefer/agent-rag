/**
 * 管理端页面编排入口。
 * 负责页面状态、事件绑定和各业务视图渲染；HTTP 协议与通用展示函数分别位于
 * api-client.js 和 ui-utils.js，避免页面业务代码直接耦合底层实现。
 */
import { createApiClient } from "./api-client.js";
import { cssEscape, escapeHtml, formatBytes, formatDate, normalizeApiBase } from "./ui-utils.js";

const state = {
  apiBase: localStorage.getItem("agent_admin_api_base") || "http://localhost:8000/api/v1",
  token: localStorage.getItem("agent_admin_token") || "",
  user: JSON.parse(localStorage.getItem("agent_admin_user") || "null"),
  knowledgeBases: [],
  selectedKbId: localStorage.getItem("agent_admin_selected_kb") || "",
  documents: [],
  selectedDocumentId: "",
  jobs: [],
  chunks: [],
  agents: [],
  users: [],
  roles: [],
  tenantSettings: null,
  auditLogs: [],
  currentView: localStorage.getItem("agent_admin_view") || "overview",
};

const apiClient = createApiClient({
  getBaseUrl: () => state.apiBase,
  getToken: () => state.token,
});

const VIEW_META = {
  overview: { title: "运营总览", subtitle: "查看知识资产、索引与治理状态" },
  knowledge: { title: "知识库", subtitle: "创建知识域并维护内容边界" },
  documents: { title: "文档管理", subtitle: "上传文档、检查解析状态与版本详情" },
  indexing: { title: "索引与分块", subtitle: "跟踪索引任务并检查可检索内容" },
  agents: { title: "智能体", subtitle: "配置提示词、模型与知识检索策略" },
  users: { title: "用户与权限", subtitle: "管理租户成员、账号状态和角色权限" },
  audit: { title: "审计日志", subtitle: "查看关键操作、资源对象与执行结果" },
  settings: { title: "租户设置", subtitle: "维护文件、安全、检索与数据保留策略" },
};

const STATUS_LABELS = {
  active: "正常",
  archived: "已归档",
  disabled: "已停用",
  draft: "草稿",
  failed: "失败",
  indexed: "已索引",
  indexing: "索引中",
  pending: "待处理",
  processing: "处理中",
  published: "已发布",
  queued: "排队中",
  success: "成功",
  uploaded: "已上传",
  unknown: "未知",
};

const ROLE_LABELS = {
  admin: "系统管理员",
  manager: "知识管理员",
  user: "普通用户",
};

const JOB_TYPE_LABELS = {
  document_index: "文档索引",
  index_document: "文档索引",
};

const AUDIT_ACTION_LABELS = {
  create: "创建",
  update: "更新",
  delete: "删除",
  login: "登录",
  upload: "上传",
  index: "建立索引",
  publish: "发布",
  archive: "归档",
};

const RESOURCE_TYPE_LABELS = {
  agent: "智能体",
  document: "文档",
  knowledge_base: "知识库",
  tenant_settings: "租户设置",
  user: "用户",
};

const els = {
  adminNav: document.querySelector("#adminNav"),
  kbContextPanel: document.querySelector("#kbContextPanel"),
  kbSelect: document.querySelector("#kbSelect"),
  viewStack: document.querySelector("#viewStack"),
  workspaceEyebrow: document.querySelector("#workspaceEyebrow"),
  apiBaseInput: document.querySelector("#apiBaseInput"),
  loginForm: document.querySelector("#loginForm"),
  emailInput: document.querySelector("#emailInput"),
  passwordInput: document.querySelector("#passwordInput"),
  authStatus: document.querySelector("#authStatus"),
  userPanel: document.querySelector("#userPanel"),
  userEmail: document.querySelector("#userEmail"),
  logoutButton: document.querySelector("#logoutButton"),
  kbForm: document.querySelector("#kbForm"),
  kbNameInput: document.querySelector("#kbNameInput"),
  kbDescriptionInput: document.querySelector("#kbDescriptionInput"),
  kbList: document.querySelector("#kbList"),
  workspaceTitle: document.querySelector("#workspaceTitle"),
  workspaceSubtitle: document.querySelector("#workspaceSubtitle"),
  apiState: document.querySelector("#apiState"),
  refreshAllButton: document.querySelector("#refreshAllButton"),
  refreshKbButton: document.querySelector("#refreshKbButton"),
  uploadForm: document.querySelector("#uploadForm"),
  documentTitleInput: document.querySelector("#documentTitleInput"),
  documentTagsInput: document.querySelector("#documentTagsInput"),
  documentFileInput: document.querySelector("#documentFileInput"),
  fileInputLabel: document.querySelector("#fileInputLabel"),
  documentTable: document.querySelector("#documentTable"),
  documentDetail: document.querySelector("#documentDetail"),
  refreshJobsButton: document.querySelector("#refreshJobsButton"),
  jobsList: document.querySelector("#jobsList"),
  chunksList: document.querySelector("#chunksList"),
  chunksSubtitle: document.querySelector("#chunksSubtitle"),
  kbCount: document.querySelector("#kbCount"),
  documentCount: document.querySelector("#documentCount"),
  indexedCount: document.querySelector("#indexedCount"),
  jobCount: document.querySelector("#jobCount"),
  overviewKbName: document.querySelector("#overviewKbName"),
  overviewKbDescription: document.querySelector("#overviewKbDescription"),
  overviewKbStatus: document.querySelector("#overviewKbStatus"),
  overviewCoverage: document.querySelector("#overviewCoverage"),
  overviewFailedCount: document.querySelector("#overviewFailedCount"),
  overviewApiStatus: document.querySelector("#overviewApiStatus"),
  overviewRole: document.querySelector("#overviewRole"),
  agentsPanel: document.querySelector("#agentsPanel"),
  agentForm: document.querySelector("#agentForm"),
  agentNameInput: document.querySelector("#agentNameInput"),
  agentDescriptionInput: document.querySelector("#agentDescriptionInput"),
  agentPromptInput: document.querySelector("#agentPromptInput"),
  agentKbOptions: document.querySelector("#agentKbOptions"),
  agentStatusInput: document.querySelector("#agentStatusInput"),
  agentTopKInput: document.querySelector("#agentTopKInput"),
  agentTemperatureInput: document.querySelector("#agentTemperatureInput"),
  agentContextInput: document.querySelector("#agentContextInput"),
  agentMaxIterationsInput: document.querySelector("#agentMaxIterationsInput"),
  agentMemoryWindowInput: document.querySelector("#agentMemoryWindowInput"),
  agentKnowledgeSearchInput: document.querySelector("#agentKnowledgeSearchInput"),
  agentRequireCitationsInput: document.querySelector("#agentRequireCitationsInput"),
  agentModelInput: document.querySelector("#agentModelInput"),
  refreshAgentsButton: document.querySelector("#refreshAgentsButton"),
  agentsList: document.querySelector("#agentsList"),
  governancePanel: document.querySelector("#governancePanel"),
  rolesPanel: document.querySelector("#rolesPanel"),
  tenantSettingsPanel: document.querySelector("#tenantSettingsPanel"),
  auditPanel: document.querySelector("#auditPanel"),
  userForm: document.querySelector("#userForm"),
  newUserEmailInput: document.querySelector("#newUserEmailInput"),
  newUserNameInput: document.querySelector("#newUserNameInput"),
  newUserPasswordInput: document.querySelector("#newUserPasswordInput"),
  newUserRoleInput: document.querySelector("#newUserRoleInput"),
  refreshUsersButton: document.querySelector("#refreshUsersButton"),
  usersList: document.querySelector("#usersList"),
  rolesList: document.querySelector("#rolesList"),
  tenantSettingsForm: document.querySelector("#tenantSettingsForm"),
  settingExtensionsInput: document.querySelector("#settingExtensionsInput"),
  settingUploadSizeInput: document.querySelector("#settingUploadSizeInput"),
  settingAttachmentSizeInput: document.querySelector("#settingAttachmentSizeInput"),
  settingTopKInput: document.querySelector("#settingTopKInput"),
  settingTemperatureInput: document.querySelector("#settingTemperatureInput"),
  settingRetentionInput: document.querySelector("#settingRetentionInput"),
  settingAuditInput: document.querySelector("#settingAuditInput"),
  settingScanInput: document.querySelector("#settingScanInput"),
  refreshAuditButton: document.querySelector("#refreshAuditButton"),
  auditLogsList: document.querySelector("#auditLogsList"),
  toast: document.querySelector("#toast"),
};

function boot() {
  els.apiBaseInput.value = state.apiBase;
  bindEvents();
  renderAuth();
  renderAll();
  setView(state.currentView, { persist: false });
  if (state.token) {
    refreshAll().catch(showError);
  }
}

function bindEvents() {
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.viewTarget));
  });

  els.kbSelect.addEventListener("change", () => {
    selectKnowledgeBase(els.kbSelect.value).catch(showError);
  });

  els.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    state.apiBase = normalizeApiBase(els.apiBaseInput.value);
    localStorage.setItem("agent_admin_api_base", state.apiBase);
    await login();
  });

  els.logoutButton.addEventListener("click", () => {
    state.token = "";
    state.user = null;
    state.knowledgeBases = [];
    state.documents = [];
    state.jobs = [];
    state.chunks = [];
    state.agents = [];
    state.users = [];
    state.roles = [];
    state.tenantSettings = null;
    state.auditLogs = [];
    localStorage.removeItem("agent_admin_token");
    localStorage.removeItem("agent_admin_user");
    state.currentView = "overview";
    renderAuth();
    renderAll();
    toast("已退出登录");
  });

  els.kbForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await createKnowledgeBase();
  });

  els.refreshAllButton.addEventListener("click", () => refreshCurrentView().catch(showError));
  els.refreshKbButton.addEventListener("click", () => loadKnowledgeBases().catch(showError));
  els.refreshJobsButton.addEventListener("click", () => loadJobs().catch(showError));
  els.refreshAgentsButton.addEventListener("click", () => loadAgents().catch(showError));
  els.refreshUsersButton.addEventListener("click", () => loadGovernance().catch(showError));
  els.refreshAuditButton.addEventListener("click", () => loadAuditLogs().catch(showError));

  els.documentFileInput.addEventListener("change", () => {
    const file = els.documentFileInput.files[0];
    els.fileInputLabel.textContent = file ? file.name : "选择文件";
  });

  els.uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await uploadDocument();
  });

  els.userForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await createUser();
  });

  els.agentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await createAgent();
  });

  els.tenantSettingsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await saveTenantSettings();
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
  localStorage.setItem("agent_admin_token", state.token);
  localStorage.setItem("agent_admin_user", JSON.stringify(state.user));
  els.passwordInput.value = "";
  setAuthStatus("");
  renderAuth();
  await refreshAll();
  toast("登录成功");
}

async function refreshAll() {
  await loadKnowledgeBases();
  if (state.selectedKbId) {
    await loadDocuments();
  }
  await loadJobs();
  await loadAgentsIfAllowed();
  await loadGovernance();
}

async function refreshCurrentView() {
  requireAuth();
  const loaders = {
    overview: refreshAll,
    knowledge: loadKnowledgeBases,
    documents: loadDocuments,
    indexing: async () => {
      await loadJobs();
      if (state.selectedDocumentId) await loadChunks();
    },
    agents: loadAgents,
    users: async () => Promise.all([loadRoles(), loadUsers()]),
    audit: loadAuditLogs,
    settings: loadTenantSettings,
  };
  await (loaders[state.currentView] || refreshAll)();
  toast(`${VIEW_META[state.currentView]?.title || "当前页面"}已刷新`);
}

async function loadKnowledgeBases() {
  requireAuth();
  const data = await request("/admin/knowledge-bases?limit=100");
  state.knowledgeBases = data.items || [];
  if (!state.knowledgeBases.some((item) => item.id === state.selectedKbId)) {
    state.selectedKbId = state.knowledgeBases[0]?.id || "";
  }
  if (state.selectedKbId) {
    localStorage.setItem("agent_admin_selected_kb", state.selectedKbId);
  }
  renderKnowledgeBases();
  renderAgentKbOptions();
  renderMetrics();
}

async function createKnowledgeBase() {
  requireAuth();
  const payload = {
    name: els.kbNameInput.value.trim(),
    description: els.kbDescriptionInput.value.trim() || null,
    visibility: "tenant",
  };
  const created = await request("/admin/knowledge-bases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.selectedKbId = created.id;
  els.kbNameInput.value = "";
  els.kbDescriptionInput.value = "";
  await refreshAll();
  toast("知识库创建成功");
}

async function selectKnowledgeBase(id) {
  state.selectedKbId = id;
  state.selectedDocumentId = "";
  localStorage.setItem("agent_admin_selected_kb", id);
  state.chunks = [];
  renderKnowledgeBases();
  await loadDocuments();
  await loadJobs();
  renderChunks();
  updateWorkspaceHeader();
  renderOverview();
}

async function loadDocuments() {
  if (!state.selectedKbId) {
    state.documents = [];
    renderDocuments();
    renderMetrics();
    return;
  }
  const data = await request(`/admin/knowledge-bases/${state.selectedKbId}/documents?limit=100`);
  state.documents = data.items || [];
  if (!state.documents.some((item) => item.id === state.selectedDocumentId)) {
    state.selectedDocumentId = state.documents[0]?.id || "";
  }
  renderDocuments();
  renderDocumentDetail();
  renderMetrics();
}

async function uploadDocument() {
  requireAuth();
  if (!state.selectedKbId) {
    toast("请先选择知识库");
    return;
  }
  const file = els.documentFileInput.files[0];
  if (!file) {
    toast("请选择要上传的文档");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  const title = els.documentTitleInput.value.trim();
  const tags = els.documentTagsInput.value.trim();
  if (title) formData.append("title", title);
  if (tags) formData.append("tags", tags);

  const document = await request(`/admin/knowledge-bases/${state.selectedKbId}/documents`, {
    method: "POST",
    body: formData,
    isForm: true,
  });
  state.selectedDocumentId = document.id;
  els.uploadForm.reset();
  els.fileInputLabel.textContent = "选择文件";
  await loadDocuments();
  await loadAuditLogsIfAllowed();
  toast("文档上传成功");
}

async function indexDocument(id) {
  requireAuth();
  state.selectedDocumentId = id;
  renderDocuments();
  const job = await request(`/admin/documents/${id}/index`, { method: "POST" });
  await loadDocuments();
  await loadJobs();
  await loadAuditLogsIfAllowed();
  state.chunks = [];
  renderChunks();
  toast(`索引任务已提交：${statusLabel(job.status)}`);
}

async function loadJobs() {
  if (!state.token) return;
  const query = state.selectedDocumentId ? `?document_id=${state.selectedDocumentId}&limit=20` : "?limit=20";
  const data = await request(`/admin/index-jobs${query}`);
  state.jobs = data.items || [];
  renderJobs();
  renderMetrics();
}

async function loadChunks(documentId = state.selectedDocumentId) {
  if (!documentId) {
    state.chunks = [];
    renderChunks();
    return;
  }
  state.selectedDocumentId = documentId;
  const data = await request(`/admin/documents/${documentId}/chunks?limit=50`);
  state.chunks = Array.isArray(data) ? data : [];
  renderDocuments();
  renderDocumentDetail();
  renderChunks();
  setView("indexing");
}

async function loadGovernance() {
  renderGovernanceVisibility();
  if (!canManageGovernance()) {
    state.users = [];
    state.roles = [];
    state.tenantSettings = null;
    state.auditLogs = [];
    renderGovernance();
    return;
  }
  await Promise.all([loadRoles(), loadUsers(), loadTenantSettings(), loadAuditLogs()]);
}

async function loadAgentsIfAllowed() {
  renderAgentVisibility();
  if (!canManageKnowledge()) {
    state.agents = [];
    renderAgents();
    return;
  }
  await loadAgents();
}

async function loadAgents() {
  const data = await request("/admin/agents?limit=100");
  state.agents = data.items || [];
  renderAgents();
}

async function createAgent() {
  const selectedKbIds = [...els.agentKbOptions.querySelectorAll("input[type='checkbox']:checked")].map(
    (input) => input.value,
  );
  const payload = {
    name: els.agentNameInput.value.trim(),
    description: els.agentDescriptionInput.value.trim() || null,
    system_prompt: els.agentPromptInput.value.trim(),
    default_knowledge_base_ids: selectedKbIds.length ? selectedKbIds : null,
    chat_model: els.agentModelInput.value.trim() || null,
    status: els.agentStatusInput.value,
    top_k: Number(els.agentTopKInput.value),
    temperature: Number(els.agentTemperatureInput.value),
    max_context_tokens: Number(els.agentContextInput.value),
    max_iterations: Number(els.agentMaxIterationsInput.value),
    memory_window: Number(els.agentMemoryWindowInput.value),
    enabled_tools: els.agentKnowledgeSearchInput.checked ? ["knowledge_search"] : [],
    require_citations: els.agentRequireCitationsInput.checked,
  };
  await request("/admin/agents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  els.agentForm.reset();
  els.agentTopKInput.value = "8";
  els.agentTemperatureInput.value = "0.2";
  els.agentContextInput.value = "3500";
  els.agentMaxIterationsInput.value = "4";
  els.agentMemoryWindowInput.value = "12";
  els.agentKnowledgeSearchInput.checked = true;
  els.agentRequireCitationsInput.checked = true;
  await loadAgents();
  await loadAuditLogsIfAllowed();
  toast("智能体创建成功");
}

async function updateAgentStatus(agentId, status) {
  await request(`/admin/agents/${agentId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  await loadAgents();
  await loadAuditLogsIfAllowed();
  toast("智能体状态已更新");
}

async function archiveAgent(agentId) {
  await request(`/admin/agents/${agentId}`, { method: "DELETE" });
  await loadAgents();
  await loadAuditLogsIfAllowed();
  toast("智能体已归档");
}

async function loadRoles() {
  const data = await request("/admin/roles");
  state.roles = data.items || [];
  renderRoles();
}

async function loadUsers() {
  const data = await request("/admin/users?limit=100");
  state.users = data.items || [];
  renderUsers();
}

async function createUser() {
  const payload = {
    email: els.newUserEmailInput.value.trim(),
    name: els.newUserNameInput.value.trim() || null,
    password: els.newUserPasswordInput.value,
    role: els.newUserRoleInput.value,
    status: "active",
  };
  await request("/admin/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  els.userForm.reset();
  await loadUsers();
  await loadAuditLogs();
  toast("用户创建成功");
}

async function saveUser(userId) {
  const row = els.usersList.querySelector(`[data-user-id="${cssEscape(userId)}"]`);
  if (!row) return;
  const payload = {
    role: row.querySelector("[data-user-role]").value,
    status: row.querySelector("[data-user-status]").value,
  };
  await request(`/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  await loadUsers();
  await loadAuditLogs();
  toast("用户信息已更新");
}

async function disableUser(userId) {
  await request(`/admin/users/${userId}`, { method: "DELETE" });
  await loadUsers();
  await loadAuditLogs();
  toast("用户已停用");
}

async function loadTenantSettings() {
  state.tenantSettings = await request("/admin/tenant-settings");
  renderTenantSettings();
}

async function saveTenantSettings() {
  const extensions = els.settingExtensionsInput.value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const payload = {
    allowed_kb_file_extensions: extensions,
    max_upload_size_mb: Number(els.settingUploadSizeInput.value),
    max_chat_attachment_size_mb: Number(els.settingAttachmentSizeInput.value),
    rag_top_k: Number(els.settingTopKInput.value),
    rag_temperature: Number(els.settingTemperatureInput.value),
    data_retention_days: Number(els.settingRetentionInput.value),
    audit_log_enabled: els.settingAuditInput.checked,
    security_scan_enabled: els.settingScanInput.checked,
  };
  state.tenantSettings = await request("/admin/tenant-settings", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  renderTenantSettings();
  await loadAuditLogs();
  toast("租户设置已保存");
}

async function loadAuditLogs() {
  const data = await request("/admin/audit-logs?limit=30");
  state.auditLogs = data.items || [];
  renderAuditLogs();
}

async function loadAuditLogsIfAllowed() {
  if (canManageGovernance()) {
    await loadAuditLogs();
  }
}

async function request(path, options = {}) {
  return apiClient.request(path, options);
}

function renderAuth() {
  const signedIn = Boolean(state.token && state.user);
  els.loginForm.classList.toggle("hidden", signedIn);
  els.userPanel.classList.toggle("hidden", !signedIn);
  els.adminNav.classList.toggle("hidden", !signedIn);
  els.kbContextPanel.classList.toggle("hidden", !signedIn);
  els.userEmail.textContent = state.user ? `${state.user.email} · ${roleLabel(state.user.role)}` : "-";
  els.apiState.textContent = signedIn ? "已连接" : "未连接";
  els.apiState.className = `pill ${signedIn ? "good" : "neutral"}`;
  els.overviewApiStatus.textContent = signedIn ? "连接正常" : "等待登录";
  els.overviewRole.textContent = state.user ? roleLabel(state.user.role) : "-";
  syncNavigationVisibility();
  renderGovernanceVisibility();
  setView(state.currentView, { persist: false });
}

function renderAll() {
  renderKnowledgeBases();
  renderDocuments();
  renderDocumentDetail();
  renderJobs();
  renderChunks();
  renderMetrics();
  renderOverview();
  renderAgents();
  renderGovernance();
  setView(state.currentView, { persist: false });
}

function renderKnowledgeBases() {
  if (!state.knowledgeBases.length) {
    els.kbList.innerHTML = `<div class="empty-state">暂无知识库</div>`;
    els.kbSelect.innerHTML = `<option value="">暂无知识库</option>`;
    els.kbSelect.disabled = true;
    updateWorkspaceHeader();
    renderOverview();
    return;
  }
  els.kbSelect.disabled = false;
  els.kbSelect.innerHTML = state.knowledgeBases
    .map((kb) => `<option value="${escapeHtml(kb.id)}">${escapeHtml(kb.name)}</option>`)
    .join("");
  els.kbSelect.value = state.selectedKbId;
  els.kbList.innerHTML = state.knowledgeBases
    .map((kb) => {
      const active = kb.id === state.selectedKbId ? " active" : "";
      return `
        <button class="kb-item${active}" type="button" data-kb-id="${escapeHtml(kb.id)}">
          <strong>${escapeHtml(kb.name)}</strong>
          <span class="kb-meta">${escapeHtml(statusLabel(kb.status))} · ${formatDate(kb.created_at)}</span>
        </button>
      `;
    })
    .join("");
  els.kbList.querySelectorAll("[data-kb-id]").forEach((button) => {
    button.addEventListener("click", () => selectKnowledgeBase(button.dataset.kbId).catch(showError));
  });
  updateWorkspaceHeader();
  renderOverview();
}

function renderDocuments() {
  if (!state.selectedKbId) {
    els.documentTable.innerHTML = `<div class="empty-state">请先选择知识库</div>`;
    return;
  }
  if (!state.documents.length) {
    els.documentTable.innerHTML = `<div class="empty-state">暂无文档，请上传文件</div>`;
    return;
  }
  els.documentTable.innerHTML = state.documents
    .map((document) => {
      const selected = document.id === state.selectedDocumentId ? " selected" : "";
      return `
        <div class="doc-row${selected}" data-document-id="${escapeHtml(document.id)}">
          <div>
            <strong class="doc-title">${escapeHtml(document.title)}</strong>
            <div class="doc-meta">${escapeHtml(document.file_type)} / ${formatBytes(currentVersion(document)?.file_size || 0)}</div>
          </div>
          ${statusPill(document.status)}
          <div class="doc-meta">${escapeHtml(statusLabel(currentVersion(document)?.parse_status || "pending"))}</div>
          <div class="doc-actions">
            <button class="ghost-button" type="button" data-action="chunks" data-document-id="${escapeHtml(document.id)}">查看分块</button>
            <button class="secondary-button" type="button" data-action="index" data-document-id="${escapeHtml(document.id)}">建立索引</button>
          </div>
        </div>
      `;
    })
    .join("");

  els.documentTable.querySelectorAll(".doc-row").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      state.selectedDocumentId = row.dataset.documentId;
      state.chunks = [];
      renderDocuments();
      renderDocumentDetail();
      loadJobs().catch(showError);
      renderChunks();
    });
  });

  els.documentTable.querySelectorAll("[data-action='index']").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      indexDocument(button.dataset.documentId).catch(showError);
    });
  });
  els.documentTable.querySelectorAll("[data-action='chunks']").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      loadChunks(button.dataset.documentId).catch(showError);
    });
  });
}

function renderDocumentDetail() {
  const document = currentDocument();
  if (!document) {
    els.documentDetail.className = "detail-empty";
    els.documentDetail.textContent = "尚未选择文档";
    return;
  }
  const version = currentVersion(document);
  els.documentDetail.className = "";
  els.documentDetail.innerHTML = `
    <dl class="detail-list">
      <div><dt>标题</dt><dd>${escapeHtml(document.title)}</dd></div>
      <div><dt>状态</dt><dd>${statusPill(document.status)}</dd></div>
      <div><dt>文档 ID</dt><dd>${escapeHtml(document.id)}</dd></div>
      <div><dt>版本</dt><dd>${version ? `v${version.version_no}` : "-"}</dd></div>
      <div><dt>SHA256</dt><dd>${escapeHtml(version?.file_hash || "-")}</dd></div>
      <div><dt>对象存储键</dt><dd>${escapeHtml(version?.object_key || "-")}</dd></div>
      <div><dt>解析错误</dt><dd>${escapeHtml(version?.parse_error || "-")}</dd></div>
    </dl>
  `;
}

function renderJobs() {
  if (!state.jobs.length) {
    els.jobsList.innerHTML = `<div class="empty-state">暂无索引任务</div>`;
    return;
  }
  els.jobsList.innerHTML = state.jobs
    .map((job) => `
      <article class="job-item">
        <div class="job-head">
          <strong>${escapeHtml(jobTypeLabel(job.job_type))}</strong>
          ${statusPill(job.status)}
        </div>
        <div class="job-meta">${job.chunk_count || 0} 个分块 · ${formatDate(job.created_at)}</div>
        ${job.error_message ? `<p class="job-meta">${escapeHtml(job.error_message)}</p>` : ""}
      </article>
    `)
    .join("");
}

function renderChunks() {
  const document = currentDocument();
  els.chunksSubtitle.textContent = document ? document.title : "请选择已完成索引的文档";
  if (!state.chunks.length) {
    els.chunksList.innerHTML = `<div class="empty-state">暂无分块内容</div>`;
    return;
  }
  els.chunksList.innerHTML = state.chunks
    .map((chunk) => `
      <article class="chunk-item">
        <div class="chunk-head">
          <strong>#${chunk.chunk_index}</strong>
          <span class="doc-meta">${chunk.token_count} 个词元${chunk.page_number ? ` · 第 ${chunk.page_number} 页` : ""}</span>
        </div>
        ${chunk.heading_path ? `<div class="doc-meta">${escapeHtml(chunk.heading_path)}</div>` : ""}
        <p class="chunk-text">${escapeHtml(chunk.content)}</p>
      </article>
    `)
    .join("");
}

function renderGovernance() {
  renderAgentVisibility();
  renderGovernanceVisibility();
  renderUsers();
  renderRoles();
  renderTenantSettings();
  renderAuditLogs();
}

function renderAgentVisibility() {
  els.agentsPanel.classList.toggle("hidden", !canManageKnowledge());
}

function renderGovernanceVisibility() {
  const visible = canManageGovernance();
  [els.governancePanel, els.rolesPanel, els.tenantSettingsPanel, els.auditPanel].forEach((panel) => {
    panel.classList.toggle("hidden", !visible);
  });
  syncNavigationVisibility();
}

function renderAgentKbOptions() {
  if (!canManageKnowledge()) return;
  if (!state.knowledgeBases.length) {
    els.agentKbOptions.innerHTML = `<div class="empty-state compact">暂无可用知识库</div>`;
    return;
  }
  els.agentKbOptions.innerHTML = state.knowledgeBases
    .map(
      (kb) => `
        <label class="checkbox-row">
          <input type="checkbox" value="${escapeHtml(kb.id)}" />
          ${escapeHtml(kb.name)}
        </label>
      `,
    )
    .join("");
}

function renderAgents() {
  renderAgentVisibility();
  renderAgentKbOptions();
  if (!canManageKnowledge()) return;
  if (!state.agents.length) {
    els.agentsList.innerHTML = `<div class="empty-state">暂无智能体</div>`;
    return;
  }
  els.agentsList.innerHTML = state.agents
    .map((agent) => `
      <article class="governance-item">
        <div class="governance-item-head">
          <div>
            <strong>${escapeHtml(agent.name)}</strong>
            <div class="doc-meta">${escapeHtml(agent.chat_model || "默认模型")} · 召回 ${agent.top_k} 条 · 温度 ${agent.temperature}</div>
          </div>
          ${statusPill(agent.status)}
        </div>
        <p class="job-meta">${escapeHtml(agent.description || "暂无描述")}</p>
        <div class="doc-meta">知识库范围：${(agent.default_knowledge_base_ids || []).length || "全部"}</div>
        <div class="doc-meta">Agent 循环：最多 ${agent.max_iterations} 轮 · 记忆 ${agent.memory_window} 条 · 工具 ${(agent.enabled_tools || []).map(escapeHtml).join("、") || "无"}</div>
        <div class="doc-meta">证据策略：${agent.require_citations ? "企业问题强制检索" : "允许模型自主判断"}</div>
        <div class="user-controls">
          <button class="secondary-button" type="button" data-action="publish-agent" data-agent-id="${escapeHtml(agent.id)}">发布</button>
          <button class="ghost-button" type="button" data-action="draft-agent" data-agent-id="${escapeHtml(agent.id)}">转为草稿</button>
          <button class="ghost-button" type="button" data-action="archive-agent" data-agent-id="${escapeHtml(agent.id)}">归档</button>
        </div>
      </article>
    `)
    .join("");

  els.agentsList.querySelectorAll("[data-action='publish-agent']").forEach((button) => {
    button.addEventListener("click", () => updateAgentStatus(button.dataset.agentId, "published").catch(showError));
  });
  els.agentsList.querySelectorAll("[data-action='draft-agent']").forEach((button) => {
    button.addEventListener("click", () => updateAgentStatus(button.dataset.agentId, "draft").catch(showError));
  });
  els.agentsList.querySelectorAll("[data-action='archive-agent']").forEach((button) => {
    button.addEventListener("click", () => archiveAgent(button.dataset.agentId).catch(showError));
  });
}

function renderUsers() {
  if (!canManageGovernance()) return;
  if (!state.users.length) {
    els.usersList.innerHTML = `<div class="empty-state">暂无用户</div>`;
    return;
  }
  els.usersList.innerHTML = state.users
    .map((user) => `
      <article class="governance-item" data-user-id="${escapeHtml(user.id)}">
        <div class="governance-item-head">
          <div>
            <strong>${escapeHtml(user.email)}</strong>
            <div class="doc-meta">${escapeHtml(user.name || "-")} / ${formatDate(user.created_at)}</div>
          </div>
          ${statusPill(user.status)}
        </div>
        <div class="user-controls">
          <select data-user-role>
            ${["user", "manager", "admin"].map((role) => `<option value="${role}" ${role === user.role ? "selected" : ""}>${roleLabel(role)}</option>`).join("")}
          </select>
          <select data-user-status>
            ${["active", "disabled"].map((status) => `<option value="${status}" ${status === user.status ? "selected" : ""}>${statusLabel(status)}</option>`).join("")}
          </select>
          <button class="secondary-button" type="button" data-action="save-user" data-user-id="${escapeHtml(user.id)}">保存</button>
          <button class="ghost-button" type="button" data-action="disable-user" data-user-id="${escapeHtml(user.id)}">停用</button>
        </div>
      </article>
    `)
    .join("");

  els.usersList.querySelectorAll("[data-action='save-user']").forEach((button) => {
    button.addEventListener("click", () => saveUser(button.dataset.userId).catch(showError));
  });
  els.usersList.querySelectorAll("[data-action='disable-user']").forEach((button) => {
    button.addEventListener("click", () => disableUser(button.dataset.userId).catch(showError));
  });
}

function renderRoles() {
  if (!canManageGovernance()) return;
  if (!state.roles.length) {
    els.rolesList.innerHTML = `<div class="empty-state">暂无角色信息</div>`;
    return;
  }
  els.rolesList.innerHTML = state.roles
    .map((role) => `
      <article class="governance-item">
        <div class="governance-item-head">
          <strong>${escapeHtml(roleLabel(role.role))}</strong>
          <span class="pill neutral">${role.permissions.length} 项权限</span>
        </div>
        <p class="job-meta">${escapeHtml(localizeRoleDescription(role.description))}</p>
        <div class="permission-list">${role.permissions.map((permission) => `<span>${escapeHtml(permissionLabel(permission))}</span>`).join("")}</div>
      </article>
    `)
    .join("");
}

function renderTenantSettings() {
  if (!canManageGovernance()) return;
  const settings = state.tenantSettings;
  if (!settings) return;
  els.settingExtensionsInput.value = (settings.allowed_kb_file_extensions || []).join(",");
  els.settingUploadSizeInput.value = settings.max_upload_size_mb;
  els.settingAttachmentSizeInput.value = settings.max_chat_attachment_size_mb;
  els.settingTopKInput.value = settings.rag_top_k;
  els.settingTemperatureInput.value = settings.rag_temperature;
  els.settingRetentionInput.value = settings.data_retention_days;
  els.settingAuditInput.checked = Boolean(settings.audit_log_enabled);
  els.settingScanInput.checked = Boolean(settings.security_scan_enabled);
}

function renderAuditLogs() {
  if (!canManageGovernance()) return;
  if (!state.auditLogs.length) {
    els.auditLogsList.innerHTML = `<div class="empty-state">暂无审计日志</div>`;
    return;
  }
  els.auditLogsList.innerHTML = state.auditLogs
    .map((log) => `
      <article class="governance-item">
        <div class="governance-item-head">
          <strong>${escapeHtml(auditActionLabel(log.action))}</strong>
          ${statusPill(log.outcome)}
        </div>
        <div class="job-meta">${escapeHtml(resourceTypeLabel(log.resource_type))} · ${escapeHtml(log.resource_id || "-")}</div>
        <div class="job-meta">${formatDate(log.created_at)} · 操作人 ${escapeHtml(log.actor_user_id || "-")}</div>
      </article>
    `)
    .join("");
}

function renderMetrics() {
  els.kbCount.textContent = String(state.knowledgeBases.length);
  els.documentCount.textContent = String(state.documents.length);
  els.indexedCount.textContent = String(state.documents.filter((item) => item.status === "indexed").length);
  els.jobCount.textContent = String(state.jobs.length);
  renderOverview();
}

function renderOverview() {
  const knowledgeBase = currentKnowledgeBase();
  const indexedCount = state.documents.filter((item) => item.status === "indexed").length;
  const failedCount = state.documents.filter((item) => {
    const version = currentVersion(item);
    return item.status === "failed" || version?.parse_status === "failed";
  }).length;
  const coverage = state.documents.length ? Math.round((indexedCount / state.documents.length) * 100) : 0;

  els.overviewKbName.textContent = knowledgeBase?.name || "尚未选择知识库";
  els.overviewKbDescription.textContent =
    knowledgeBase?.description || "创建或选择知识库后即可管理文档与索引。";
  els.overviewKbStatus.textContent = knowledgeBase ? statusLabel(knowledgeBase.status) : "-";
  els.overviewCoverage.textContent = `${coverage}%`;
  els.overviewFailedCount.textContent = String(failedCount);
}

function setView(view, options = {}) {
  const persist = options.persist !== false;
  const target = VIEW_META[view] && canOpenView(view) ? view : "overview";
  state.currentView = target;

  els.viewStack.querySelectorAll(".admin-view").forEach((section) => {
    section.classList.toggle("active", section.dataset.view === target);
  });
  document.querySelectorAll(".nav-item[data-view-target]").forEach((button) => {
    const active = button.dataset.viewTarget === target;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
  });
  if (persist) {
    localStorage.setItem("agent_admin_view", target);
  }
  updateWorkspaceHeader();
}

function updateWorkspaceHeader() {
  const meta = VIEW_META[state.currentView] || VIEW_META.overview;
  const selected = currentKnowledgeBase();
  const contextualViews = ["documents", "indexing", "agents"];
  els.workspaceEyebrow.textContent = state.currentView === "overview" ? "管理控制台" : "管理模块";
  els.workspaceTitle.textContent = meta.title;
  els.workspaceSubtitle.textContent =
    contextualViews.includes(state.currentView) && selected
      ? `${meta.subtitle} · 当前：${selected.name}`
      : meta.subtitle;
}

function syncNavigationVisibility() {
  document.querySelectorAll("[data-requires='knowledge']").forEach((element) => {
    element.classList.toggle("hidden", !canManageKnowledge());
  });
  document.querySelectorAll("[data-requires='governance']").forEach((element) => {
    element.classList.toggle("hidden", !canManageGovernance());
  });
  if (!canOpenView(state.currentView)) {
    state.currentView = "overview";
  }
}

function canOpenView(view) {
  if (["users", "audit", "settings"].includes(view)) return canManageGovernance();
  if (["knowledge", "documents", "indexing", "agents"].includes(view)) return canManageKnowledge();
  return view === "overview";
}

function statusPill(status) {
  const normalized = String(status || "unknown");
  const css = ["success", "indexed", "active", "published"].includes(normalized)
    ? "good"
    : ["failed", "archived", "disabled"].includes(normalized)
      ? "bad"
      : ["indexing", "processing", "pending", "queued", "uploaded", "draft"].includes(normalized)
        ? "warn"
        : "neutral";
  return `<span class="pill ${css}">${escapeHtml(statusLabel(normalized))}</span>`;
}

function currentKnowledgeBase() {
  return state.knowledgeBases.find((item) => item.id === state.selectedKbId) || null;
}

function currentDocument() {
  return state.documents.find((item) => item.id === state.selectedDocumentId) || null;
}

function currentVersion(document) {
  if (!document?.versions?.length) return null;
  return document.versions.find((item) => item.id === document.current_version_id) || document.versions.at(-1);
}

function statusLabel(status) {
  const normalized = String(status || "unknown");
  return STATUS_LABELS[normalized] || normalized;
}

function roleLabel(role) {
  return ROLE_LABELS[String(role || "")] || String(role || "-");
}

function jobTypeLabel(jobType) {
  return JOB_TYPE_LABELS[String(jobType || "")] || String(jobType || "索引任务");
}

function auditActionLabel(action) {
  const normalized = String(action || "");
  return AUDIT_ACTION_LABELS[normalized] || normalized;
}

function resourceTypeLabel(resourceType) {
  const normalized = String(resourceType || "");
  return RESOURCE_TYPE_LABELS[normalized] || normalized;
}

function permissionLabel(permission) {
  const labels = {
    "audit:read": "查看审计日志",
    "chat:use": "使用知识问答",
    "knowledge:manage": "管理知识库",
    "tenant_settings:manage": "管理租户设置",
    "users:manage": "管理用户",
  };
  return labels[permission] || permission;
}

function localizeRoleDescription(description) {
  const labels = {
    "Full tenant administration, including users, settings, audit logs, and knowledge operations.":
      "拥有完整的租户管理权限，包括用户、设置、审计日志和知识库管理。",
    "Knowledge administrator who can manage knowledge bases and documents.":
      "可管理知识库、文档和智能体的知识管理员。",
    "End user who can ask questions through the user console.": "可通过知识问答端提问的普通用户。",
  };
  return labels[description] || description || "-";
}

function localizeError(message) {
  const labels = {
    "Admin role required": "需要系统管理员权限",
    "Agent not found": "未找到智能体",
    "At least one knowledge base file extension is required": "至少需要配置一种知识库文件格式",
    "Cannot disable your own account": "不能停用当前登录账号",
    "Could not validate credentials": "登录凭证已失效，请重新登录",
    "Document not found": "未找到文档",
    "Failed to fetch": "无法连接 API 服务，请检查 API 地址及服务状态",
    "Incorrect email or password": "邮箱或密码错误",
    "Knowledge base not found": "未找到知识库",
    "Knowledge base with the same name already exists": "已存在同名知识库",
    "Unsupported role": "不支持该用户角色",
    "User email already exists": "该邮箱已被使用",
    "User not found": "未找到用户",
  };
  if (labels[message]) return labels[message];
  if (message.startsWith("Permission required:")) return "当前账号没有执行此操作的权限";
  return message;
}

function canManageGovernance() {
  return state.user?.role === "admin";
}

function canManageKnowledge() {
  return state.user?.role === "admin" || state.user?.role === "manager";
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
}

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => els.toast.classList.add("hidden"), 3200);
}

boot();
