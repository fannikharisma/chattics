/** Menu label → route. The backend owns which labels a role gets; this only maps them. */

const ROUTES: Record<string, string> = {
  Conversations: "/conversations",
  Tenants: "/tenants",
  Datasets: "/datasets",
  Charts: "/charts",
  Dashboards: "/dashboards",
  "Data Source": "/data-source",
  "Model settings": "/model-settings",
  "Semantic Layer": "/semantic",
  Users: "/users",
  "Query Log": "/query-log",
};

export function menuHref(label: string): string | null {
  return ROUTES[label] ?? null;
}

export function roleLabel(role: string): string {
  if (role === "platform_admin") return "Platform Admin";
  if (role === "tenant_admin") return "Tenant Admin";
  if (role === "user") return "User";
  return role;
}