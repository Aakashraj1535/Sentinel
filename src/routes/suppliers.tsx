import { createFileRoute, Outlet } from "@tanstack/react-router";

// Pathless layout, mirroring knowledge-base.tsx's pattern: this file's
// only job is to exist as the parent for suppliers.index.tsx (the list)
// and suppliers.$supplierId.tsx (the scorecard detail page). It must
// render <Outlet /> -- without it, TanStack Router still matches child
// routes correctly (the URL updates, routeTree.gen.ts has the right
// entries) but has nowhere to put the child's content, so the page
// silently looks unchanged. That was the actual bug behind "URL changes
// but nothing opens" when the supplier detail page was first added.
export const Route = createFileRoute("/suppliers")({
  component: SuppliersLayout,
});

function SuppliersLayout() {
  return <Outlet />;
}
