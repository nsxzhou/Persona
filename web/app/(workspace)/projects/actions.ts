"use server";

import { revalidatePath } from "next/cache";
import { getServerApi } from "@/lib/server-api";
import type { ProjectPayload, ProjectUpdatePayload } from "@/lib/types";

export async function createProjectAction(payload: ProjectPayload) {
  const api = await getServerApi();
  const project = await api.createProject(payload);
  revalidatePath("/projects");
  return project;
}

export async function updateProjectAction(id: string, payload: Partial<ProjectUpdatePayload>) {
  const api = await getServerApi();
  const project = await api.updateProject(id, payload);
  revalidatePath("/projects");
  revalidatePath(`/projects/${id}`);
  return project;
}
