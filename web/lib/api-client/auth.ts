import type { Requester } from "@/lib/api/requester";
import type {
  LoginPayload,
  SetupPayload,
  SetupResponse,
  SetupStatusResponse,
  User,
} from "@/lib/types";

export function createAuthApiClient(request: Requester) {
  return {
    getSetupStatus: () => request<SetupStatusResponse>("/api/v1/setup/status"),
    setup: (payload: SetupPayload) =>
      request<SetupResponse>("/api/v1/setup", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    login: (payload: LoginPayload) =>
      request<User>("/api/v1/login", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    logout: () =>
      request<void>("/api/v1/logout", {
        method: "POST",
      }),
    deleteAccount: () =>
      request<void>("/api/v1/account", {
        method: "DELETE",
      }),
    getCurrentUser: () => request<User>("/api/v1/me"),
  };
}
