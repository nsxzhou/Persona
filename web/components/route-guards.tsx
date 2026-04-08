"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { PropsWithChildren, useEffect } from "react";

import { api } from "@/lib/api";
import { PageLoading } from "@/components/page-state";

export function PublicRouteGuard({ children }: PropsWithChildren) {
  const router = useRouter();
  const pathname = usePathname();
  const setupQuery = useQuery({
    queryKey: ["setup-status"],
    queryFn: api.getSetupStatus,
  });
  const meQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: api.getCurrentUser,
    retry: false,
  });

  useEffect(() => {
    if (!setupQuery.data) {
      return;
    }

    if (!setupQuery.data.initialized) {
      if (pathname !== "/setup") {
        router.replace("/setup");
      }
      return;
    }

    if (meQuery.data && !meQuery.isError) {
      router.replace("/projects");
      return;
    }

    if (pathname === "/setup") {
      router.replace("/login");
    }
  }, [meQuery.data, meQuery.isError, pathname, router, setupQuery.data]);

  if (setupQuery.isLoading || (setupQuery.data?.initialized && meQuery.isLoading)) {
    return <PageLoading title="正在检查 Persona 状态..." />;
  }

  return <>{children}</>;
}

export function ProtectedRouteGuard({ children }: PropsWithChildren) {
  const router = useRouter();
  const setupQuery = useQuery({
    queryKey: ["setup-status"],
    queryFn: api.getSetupStatus,
  });
  const meQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: api.getCurrentUser,
    retry: false,
  });

  useEffect(() => {
    if (!setupQuery.data) {
      return;
    }
    if (!setupQuery.data.initialized) {
      router.replace("/setup");
      return;
    }
    if (meQuery.isError) {
      router.replace("/login");
    }
  }, [meQuery.isError, router, setupQuery.data]);

  if (setupQuery.isLoading || meQuery.isLoading || !meQuery.data || meQuery.isError) {
    return <PageLoading title="正在进入工作台..." />;
  }

  return <>{children}</>;
}

