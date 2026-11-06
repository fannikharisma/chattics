import type { components } from "./api-types";

export type User = components["schemas"]["UserResponse"];
export type Me = components["schemas"]["MeResponse"];
export type PublicTenant = components["schemas"]["TenantPublicResponse"];
export type Tenant = components["schemas"]["TenantResponse"];
export type Context = components["schemas"]["ContextResponse"];
export type ContextIdentity = components["schemas"]["ContextIdentity"];
export type ContextTenant = components["schemas"]["ContextTenant"];

export type ConnectionFieldOption =
  components["schemas"]["ConnectionOptionResponse"];
export type ConnectionField = components["schemas"]["ConnectionFieldResponse"];
export type ConnectionFields = components["schemas"]["ConnectionFieldsResponse"];
export type ConnectionChecklistItem =
  components["schemas"]["ChecklistItemResponse"];
export type ConnectionTableSummary =
  components["schemas"]["TableSummaryResponse"];
export type ConnectionTest = components["schemas"]["ConnectionTestResponse"];
export type DataSource = components["schemas"]["DataSourceResponse"];