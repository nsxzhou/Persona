import { PropsWithChildren } from "react";

import { AppShell } from "@/components/app-shell";
import { ProtectedRouteGuard } from "@/components/route-guards";

export default function WorkspaceLayout({ children }: PropsWithChildren) {
  return (
    <ProtectedRouteGuard>
      <AppShell>{children}</AppShell>
    </ProtectedRouteGuard>
  );
}

