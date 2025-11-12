import axios from "axios";

// Use relative path when NEXT_PUBLIC_API_URL is not set, so requests
// pass through Next.js rewrites to backend and avoid CORS issues.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export const api = axios.create({
  baseURL: API_URL || undefined,
  headers: {
    "Content-Type": "application/json",
  },
});

// Standardize error handling: extract meaningful message from server responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const data = error?.response?.data;
    let message = "Request failed";
    if (typeof data === "string") {
      message = data;
    } else if (data?.detail) {
      if (Array.isArray(data.detail)) {
        message = data.detail.map((d: any) => d?.msg || d).join("; ");
      } else {
        message = data.detail;
      }
    } else if (data?.error) {
      message = data.error;
    } else if (data?.message) {
      message = data.message;
    } else if (error?.message) {
      message = error.message;
    }
    const prefix = status ? `${status} ` : "";
    return Promise.reject(new Error(`${prefix}${message}`.trim()));
  }
);

// Document APIs
export const documentApi = {
  upload: async (file: File, fundId?: number) => {
    const formData = new FormData();
    formData.append("file", file);
    if (fundId) {
      formData.append("fund_id", fundId.toString());
    }

    const response = await api.post("/api/documents/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  getStatus: async (documentId: number) => {
    const response = await api.get(`/api/documents/${documentId}/status`);
    return response.data;
  },

  list: async (fundId?: number) => {
    const params = fundId ? { fund_id: fundId } : {};
    const response = await api.get("/api/documents/", { params });
    return response.data;
  },

  delete: async (documentId: number) => {
    const response = await api.delete(`/api/documents/${documentId}`);
    return response.data;
  },
};

// Fund APIs
export const fundApi = {
  list: async () => {
    const response = await api.get("/api/funds/");
    return response.data;
  },

  get: async (fundId: number) => {
    const response = await api.get(`/api/funds/${fundId}`);
    return response.data;
  },

  create: async (fund: any) => {
    const response = await api.post("/api/funds/", fund);
    return response.data;
  },

  getTransactions: async (
    fundId: number,
    type: string,
    page: number = 1,
    limit: number = 50
  ) => {
    const response = await api.get(`/api/funds/${fundId}/transactions`, {
      params: { transaction_type: type, page, limit },
    });
    return response.data;
  },

  getMetrics: async (fundId: number) => {
    const response = await api.get(`/api/funds/${fundId}/metrics`);
    return response.data;
  },

  exportExcel: async (
    fundId: number,
    include: "all" | "transactions" | "metrics" = "all"
  ) => {
    const response = await api.get(`/api/funds/${fundId}/export.xlsx`, {
      params: { include },
      responseType: "blob",
    });
    return response.data as Blob;
  },
};

// Chat APIs
export const chatApi = {
  query: async (
    query: string,
    fundId?: number,
    conversationId?: string,
    documentIds?: number[],
    weights?: { dense?: number; lexical?: number; pattern?: number }
  ) => {
    const response = await api.post("/api/chat/query", {
      query,
      fund_id: fundId,
      document_ids: documentIds,
      conversation_id: conversationId,
      weights,
    });
    return response.data;
  },

  createConversation: async (fundId?: number) => {
    const response = await api.post("/api/chat/conversations", {
      fund_id: fundId,
    });
    return response.data;
  },

  getConversation: async (conversationId: string) => {
    const response = await api.get(`/api/chat/conversations/${conversationId}`);
    return response.data;
  },

  listConversations: async (fundId?: number, q?: string) => {
    const params: any = {};
    if (fundId) params.fund_id = fundId;
    if (q) params.q = q;
    const response = await api.get("/api/chat/conversations", { params });
    return response.data;
  },

  deleteConversation: async (conversationId: string) => {
    const response = await api.delete(
      `/api/chat/conversations/${conversationId}`
    );
    return response.data;
  },
};

// Metrics APIs
export const metricsApi = {
  getFundMetrics: async (fundId: number, metric?: string) => {
    const params = metric ? { metric } : {};
    const response = await api.get(`/api/metrics/funds/${fundId}/metrics`, {
      params,
    });
    return response.data;
  },
};
