"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

const PLATFORM_COLORS: Record<string, string> = {
  tiktok: "#EC4899",
  instagram: "#8B5CF6",
  youtube: "#EF4444",
  facebook: "#0284C7",
};

const PLATFORM_LABELS: Record<string, string> = {
  tiktok: "TikTok",
  instagram: "Instagram",
  youtube: "YouTube",
  facebook: "Facebook",
};

export function PlatformDonutChart({ viewsByPlatform }: { viewsByPlatform: Record<string, number> }) {
  const total = Object.values(viewsByPlatform).reduce((sum, v) => sum + v, 0);
  const entries = Object.entries(viewsByPlatform)
    .filter(([, views]) => views > 0)
    .sort(([, a], [, b]) => b - a);

  if (total === 0 || entries.length === 0) {
    return <p className="py-16 text-center text-sm text-muted-foreground">No platform data yet.</p>;
  }

  const data = entries.map(([platform, views]) => ({
    name: PLATFORM_LABELS[platform] ?? platform,
    value: views,
    color: PLATFORM_COLORS[platform] ?? "#8B5CF6",
  }));

  return (
    <div className="flex items-center gap-6">
      <div className="h-40 w-40 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="100%" paddingAngle={2} stroke="none">
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [Number(value).toLocaleString(), String(name)]}
              contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", background: "var(--popover)" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="min-w-0 flex-1 space-y-2.5">
        {data.map((entry) => (
          <li key={entry.name} className="flex items-center justify-between gap-2 text-sm">
            <span className="flex items-center gap-2 truncate">
              <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className="truncate text-foreground">{entry.name}</span>
            </span>
            <span className="shrink-0 font-medium text-muted-foreground">
              {Math.round((entry.value / total) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
