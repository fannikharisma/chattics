import type { components } from "./api-types";

export type User = components["schemas"]["UserResponse"];
export type Me = components["schemas"]["MeResponse"];
export type PublicTenant = components["schemas"]["TenantPublicResponse"];
export type Tenant = components["schemas"]["TenantResponse"];
export type Context = components["schemas"]["ContextResponse"];
export type ContextIdentity = components["schemas"]["ContextIdentity"];
export type ContextTenant = components["schemas"]["ContextTenant"];