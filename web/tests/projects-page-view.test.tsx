import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ProjectsPageClient } from "@/components/projects-page-view";
import { projectsQueryKeys } from "@/lib/projects-query-keys";
import type { ProjectSummary } from "@/lib/types";

const apiMock = vi.hoisted(() => ({
  getProjects: vi.fn(),
  getProviderConfigs: vi.fn(),
  getStyleProfiles: vi.fn(),
  getPlotProfiles: vi.fn(),
  archiveProject: vi.fn(),
  restoreProject: vi.fn(),
  deleteProject: vi.fn(),
}));

const localStorageMock = vi.hoisted(() => {
  const store = new Map<string, string>();
  return {
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store.set(key, value);
    }),
    removeItem: vi.fn((key: string) => {
      store.delete(key);
    }),
    clear: vi.fn(() => {
      store.clear();
    }),
  };
});

vi.mock("@/lib/api", () => ({
  api: apiMock,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

Object.defineProperty(globalThis, "localStorage", {
  value: localStorageMock,
  configurable: true,
});

const project: ProjectSummary = {
  id: "project-1",
  name: "首屏项目",
  description: "SSR hydrated project",
  status: "active",
  default_provider_id: "provider-1",
  default_model: "gpt-test",
  style_profile_id: null,
  plot_profile_id: null,
  generation_profile: null,
  length_preset: "short",
  project_origin: "normal",
  archived_at: null,
  created_at: "2026-05-07T00:00:00Z",
  updated_at: "2026-05-07T00:00:00Z",
  provider: {
    id: "provider-1",
    label: "Primary",
    base_url: "https://api.example.test/v1",
    default_model: "gpt-test",
    is_enabled: true,
  },
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderWithClient(queryClient = createTestQueryClient()) {
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectsPageClient />
    </QueryClientProvider>,
  );
}

describe("ProjectsPageClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    apiMock.getProjects.mockResolvedValue([project]);
    apiMock.getProviderConfigs.mockResolvedValue([]);
    apiMock.getStyleProfiles.mockResolvedValue([]);
    apiMock.getPlotProfiles.mockResolvedValue([]);
  });

  test("renders hydrated default project list without initial loading state", () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(projectsQueryKeys.list(false, 1), [project]);

    renderWithClient(queryClient);

    expect(screen.queryByText("正在载入 Persona...")).not.toBeInTheDocument();
    expect(screen.getByText("首屏项目")).toBeInTheDocument();
    expect(apiMock.getProjects).not.toHaveBeenCalled();
  });

  test("saved archived preference refetches archived projects after hydration", async () => {
    localStorageMock.setItem("persona_projects_include_archived", "true");
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(projectsQueryKeys.list(false, 1), [project]);

    renderWithClient(queryClient);

    expect(screen.getByText("首屏项目")).toBeInTheDocument();
    await waitFor(() => {
      expect(apiMock.getProjects).toHaveBeenCalledWith({
        includeArchived: true,
        offset: 0,
        limit: 10,
      });
    });
  });

  test("archive switch persists preference", async () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(projectsQueryKeys.list(false, 1), [project]);

    renderWithClient(queryClient);
    fireEvent.click(screen.getByLabelText("显示已归档"));

    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "persona_projects_include_archived",
      "true",
    );
  });
});
