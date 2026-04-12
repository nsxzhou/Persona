"use server";

import { revalidatePath } from "next/cache";
import { createServerProject, updateServerProject } from "@/lib/server-api";
import type { ProjectPayload } from "@/lib/types";

export async function createProjectAction(payload: ProjectPayload) {
  const project = await createServerProject(payload);
  revalidatePath("/projects");
  return project;
}

export async function updateProjectAction(id: string, payload: Partial<ProjectPayload>) {
  const project = await updateServerProject(id, payload);
  revalidatePath("/projects");
  revalidatePath(`/projects/${id}`);
  return project;
}
