const MONTH_YEAR = new Intl.DateTimeFormat("en-GB", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function monthYear(iso: string): string {
  return MONTH_YEAR.format(new Date(iso));
}