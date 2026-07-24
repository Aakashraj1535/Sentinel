import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/knowledge-base")({
  component: KnowledgeBaseLayout,
});

function KnowledgeBaseLayout() {
  return <Outlet />;
}
