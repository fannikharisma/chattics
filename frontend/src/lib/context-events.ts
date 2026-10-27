/**
 * Ephemeral shell messages. Selecting a Tenant happens inside a screen, but
 * the sidebar and its confirmation line belong to the shell. A DOM event keeps
 * that one-way hand-off local instead of adding a global store.
 */

export const TENANT_SELECTED_EVENT = "chattics:tenant-selected";

export type TenantSelectedDetail = { name: string };

export function announceTenantSelected(name: string): void {
  window.dispatchEvent(
    new CustomEvent<TenantSelectedDetail>(TENANT_SELECTED_EVENT, {
      detail: { name },
    }),
  );
}
