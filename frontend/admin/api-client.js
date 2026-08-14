/**
 * 管理端 HTTP 适配器：统一拼接 API 地址、注入 Token、解析响应和标准化错误。
 * 调用方通过 getter 提供当前配置，客户端无需依赖具体页面状态结构。
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
