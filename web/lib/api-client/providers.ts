import type { Requester } from "@/lib/api/requester";
import type {
  ConnectionTestResponse,
  ProviderChatTestRequest,
  ProviderChatTestResponse,
  ProviderConfig,
  ProviderConfigUpdatePayload,
  ProviderPayload,
} from "@/lib/types";

export function createProviderApiClient(request: Requester) {
  return {
    getProviderConfigs: () => request<ProviderConfig[]>("/api/v1/provider-configs"),
    createProviderConfig: (payload: ProviderPayload) =>
      request<ProviderConfig>("/api/v1/provider-configs", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateProviderConfig: (id: string, payload: ProviderConfigUpdatePayload) =>
      request<ProviderConfig>(`/api/v1/provider-configs/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    testProviderConfig: (id: string) =>
      request<ConnectionTestResponse>(`/api/v1/provider-configs/${id}/test`, {
        method: "POST",
      }),
    chatTestProviderConfig: (id: string, payload: ProviderChatTestRequest) =>
      request<ProviderChatTestResponse>(`/api/v1/provider-configs/${id}/chat-test`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    deleteProviderConfig: (id: string) =>
      request<void>(`/api/v1/provider-configs/${id}`, {
        method: "DELETE",
      }),
  };
}
