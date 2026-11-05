import { useEffect, useState } from "react";

export type PanelId =
  | "summary"
  | "approvals"
  | "drafts"
  | "agents"
  | "map"
  | "activity"
  | "tokens"
  | "guardrails"
  | "cash";
export type Theme = "system" | "light" | "dark";
export type Side = "left" | "right";

export interface PanelSetting {
  id: PanelId;
  visible: boolean;
  wide: boolean;
}

export interface Layout {
  panels: PanelSetting[];
  theme: Theme;
  side: Side;
}

export const PANEL_NAMES: Record<PanelId, string> = {
  summary: "Summary",
  approvals: "Approvals",
  drafts: "Customer draft",
  agents: "Agents",
  map: "Who's talking to whom",
  activity: "Activity",
  tokens: "Token meter",
  guardrails: "Guardrails and audit",
  cash: "Cash flow",
};

/** People need these to approve payments and close tickets, so they can move but not hide. */
export const REQUIRED_PANELS: PanelId[] = ["summary", "approvals"];

const panel = (id: PanelId, wide = true): PanelSetting => ({ id, visible: true, wide });

export const DEFAULT_LAYOUT: Layout = {
  panels: [
    panel("summary"),
    panel("approvals"),
    panel("drafts"),
    panel("agents"),
    panel("map"),
    panel("activity"),
    panel("tokens", false),
    panel("guardrails", false),
    panel("cash"),
  ],
  theme: "system",
  side: "left",
};

const STORAGE_KEY = "campus-board-layout";

function loadLayout(): Layout {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Partial<Layout> | null;
    if (!saved) return DEFAULT_LAYOUT;
    const known = (saved.panels ?? []).filter((item) => item.id in PANEL_NAMES);
    const missing = DEFAULT_LAYOUT.panels.filter((item) => !known.some((k) => k.id === item.id));
    const panels = [...known, ...missing].map((item) =>
      REQUIRED_PANELS.includes(item.id) ? { ...item, visible: true } : item,
    );
    return { ...DEFAULT_LAYOUT, ...saved, panels };
  } catch {
    return DEFAULT_LAYOUT;
  }
}

export function useLayout() {
  const [layout, setLayout] = useState<Layout>(loadLayout);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
    } catch {
      // The board still works if the browser blocks storage.
    }
  }, [layout]);

  useEffect(() => {
    const dark = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const useDark = layout.theme === "dark" || (layout.theme === "system" && dark.matches);
      document.documentElement.dataset.theme = useDark ? "dark" : "light";
    };
    apply();
    dark.addEventListener("change", apply);
    return () => dark.removeEventListener("change", apply);
  }, [layout.theme]);

  return [layout, setLayout] as const;
}
