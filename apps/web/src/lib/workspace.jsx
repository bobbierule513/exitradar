/**
 * Workspace + thesis context from the URL (and API fallbacks), not hardcoded IDs.
 */
import { createContext, useCallback, useContext, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api } from "./api";

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [params, setParams] = useSearchParams();
  const paramWorkspace = params.get("workspace") || "";
  const paramThesis = params.get("thesis") || "";

  const { data: workspaces = [], isLoading: wsLoading, error: wsError } = useQuery({
    queryKey: ["workspaces"],
    queryFn: api.workspaces,
  });

  const workspaceId = paramWorkspace || workspaces[0]?.id || "";

  const {
    data: theses = [],
    isLoading: thesisLoading,
    error: thesisError,
  } = useQuery({
    queryKey: ["theses", workspaceId],
    queryFn: () => api.theses(workspaceId),
    enabled: Boolean(workspaceId),
  });

  const thesisId = paramThesis || theses[0]?.id || "";
  const workspace = workspaces.find((w) => w.id === workspaceId) || workspaces[0] || null;
  const thesis = theses.find((t) => t.id === thesisId) || theses[0] || null;

  useEffect(() => {
    if (!workspaceId) return;
    if (paramWorkspace === workspaceId && (!thesisId || paramThesis === thesisId)) return;
    const next = { workspace: workspaceId };
    if (thesisId) next.thesis = thesisId;
    setParams(next, { replace: true });
  }, [workspaceId, thesisId, paramWorkspace, paramThesis, setParams]);

  const setThesisId = (id) => {
    const next = { workspace: workspaceId };
    if (id) next.thesis = id;
    setParams(next);
  };

  const setWorkspaceId = (id) => {
    setParams(id ? { workspace: id } : {});
  };

  const withContext = useCallback(
    (path) => {
      const q = new URLSearchParams();
      if (workspaceId) q.set("workspace", workspaceId);
      if (thesisId) q.set("thesis", thesisId);
      const search = q.toString();
      if (!search) return path;
      return { pathname: path, search: `?${search}` };
    },
    [workspaceId, thesisId]
  );

  const value = useMemo(
    () => ({
      workspaceId,
      thesisId,
      workspace,
      thesis,
      workspaces,
      theses,
      isLoading: wsLoading || (!!workspaceId && thesisLoading),
      error: wsError || thesisError,
      setThesisId,
      setWorkspaceId,
      withContext,
    }),
    [
      workspaceId,
      thesisId,
      workspace,
      thesis,
      workspaces,
      theses,
      wsLoading,
      thesisLoading,
      wsError,
      thesisError,
      withContext,
    ]
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return ctx;
}
