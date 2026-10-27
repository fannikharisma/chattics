"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";

type StatusFilter = "all" | "active" | "disabled";

function normalizeStatus(value: string | null): StatusFilter {
  return value === "active" || value === "disabled" ? value : "all";
}

export function TenantsFilters({
  initialSearch,
}: {
  initialSearch: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const currentSearch = params.get("search") ?? "";
  const currentStatus = normalizeStatus(params.get("status"));
  const [search, setSearch] = useState(initialSearch);
  const lastPushed = useRef(initialSearch);

  useEffect(() => {
    if (currentSearch !== lastPushed.current) {
      setSearch(currentSearch);
    }
  }, [currentSearch]);

  useEffect(() => {
    if (search === currentSearch) return;

    const timer = window.setTimeout(() => {
      lastPushed.current = search;
      const query = new URLSearchParams();
      if (search.trim()) query.set("search", search.trim());
      if (currentStatus !== "all") query.set("status", currentStatus);
      router.replace(
        query.toString() ? `${pathname}?${query.toString()}` : pathname,
        { scroll: false },
      );
    }, 250);

    return () => window.clearTimeout(timer);
  }, [search, currentSearch, currentStatus, pathname, router]);

  function changeStatus(status: StatusFilter) {
    const value = status;
    const query = new URLSearchParams();
    if (search.trim()) query.set("search", search.trim());
    if (value !== "all") query.set("status", value);
    lastPushed.current = search;
    router.replace(
      query.toString() ? `${pathname}?${query.toString()}` : pathname,
      { scroll: false },
    );
  }

  return (
    <div className="flex flex-wrap gap-3">
      <Input
        type="search"
        aria-label="Search by Tenant name or admin email"
        placeholder="Search by Tenant name or admin email"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        className="min-w-[220px] flex-1"
      />
      <div className="w-full sm:w-[190px]">
        <NativeSelect
          aria-label="Filter by status"
          value={currentStatus}
          onChange={(event) => changeStatus(normalizeStatus(event.target.value))}
        >
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </NativeSelect>
      </div>
    </div>
  );
}