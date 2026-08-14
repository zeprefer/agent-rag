/**
 * 用户端 HTTP 适配器：集中处理认证头、响应解析和 API 错误，保持聊天流程只
 * 关注业务动作。
 */
export class ApiError extends Error {
  constructor(message, { status, detail } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function createApiClient({ getBaseUrl, getToken }) {
  return {
    async request(path, options = {}) {
      const headers = new Headers(options.headers || {});
      if (!options.isForm) headers.set("Content-Type", "application/json");

      const token = getToken();
      if (!options.skipAuth && token) headers.set("Authorization", `Bearer ${token}`);

      const response = await fetch(`${getBaseUrl()}${path}`, {
        method: options.method || "GET",
        headers,
        body: options.body,
      });
      const text = await response.text();
      const data = text ? JSON.parse(text) : null;
      if (!response.ok) {
        const detail = data?.detail || response.statusText;
        const message = typeof detail === "string" ? detail : JSON.stringify(detail);
        throw new ApiError(message, { status: response.status, detail });
      }
      return data;
    },
  };
}
