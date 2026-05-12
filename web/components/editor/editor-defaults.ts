import type { ProjectBible } from "@/lib/types";

export const DEFAULT_BIBLE = {
  id: "",
  project_id: "",
  inspiration: "",
  world_building: "",
  characters_blueprint: "",
  outline_master: "",
  outline_detail: "",
  characters_status: "",
  runtime_state: "",
  runtime_threads: "",
  story_summary: "",
  created_at: "",
  updated_at: "",
} satisfies ProjectBible;
