export type DateFilterOption = 'all' | 'today' | 'week' | 'month';

export interface DateFilterConfig {
  id: DateFilterOption;
  label: string;
  shortLabel: string;
}

export const DATE_FILTER_OPTIONS: DateFilterConfig[] = [
  { id: 'all', label: 'All Time', shortLabel: 'All' },
  { id: 'today', label: 'Today (24h)', shortLabel: 'Today' },
  { id: 'week', label: 'Past Week (7d)', shortLabel: 'Week' },
  { id: 'month', label: 'Past Month (30d)', shortLabel: 'Month' },
];

/**
 * Checks if a published_at date string falls within the specified date filter option.
 */
export function isWithinDateFilter(
  dateStr?: string | null,
  filter: DateFilterOption = 'all'
): boolean {
  if (!filter || filter === 'all') return true;
  if (!dateStr) return false;

  try {
    const pubTime = new Date(dateStr).getTime();
    if (isNaN(pubTime)) return true;

    const now = Date.now();
    const diffMs = now - pubTime;

    // Allow future publication dates
    if (diffMs < 0) return true;

    switch (filter) {
      case 'today':
        return diffMs <= 24 * 60 * 60 * 1000;
      case 'week':
        return diffMs <= 7 * 24 * 60 * 60 * 1000;
      case 'month':
        return diffMs <= 30 * 24 * 60 * 60 * 1000;
      default:
        return true;
    }
  } catch {
    return true;
  }
}

/**
 * Formats an ISO publish date string into a clean, human-readable date.
 * Example output: "Aug 19, 2026"
 */
export function formatPublishDate(dateStr?: string | null): string {
  if (!dateStr) return '';

  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';

    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(d);
  } catch {
    return '';
  }
}
