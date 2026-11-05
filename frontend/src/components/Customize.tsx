import { useEffect, useState } from "react";
import { DEFAULT_LAYOUT, PANEL_NAMES, REQUIRED_PANELS, type Layout, type Side, type Theme } from "../layout";

interface Props {
  layout: Layout;
  onChange: (layout: Layout) => void;
  onClose: () => void;
}

const THEMES: { id: Theme; label: string }[] = [
  { id: "system", label: "System" },
  { id: "light", label: "Light" },
  { id: "dark", label: "Dark" },
];
const SIDES: { id: Side; label: string }[] = [
  { id: "left", label: "Left" },
  { id: "right", label: "Right" },
];

function Choice<T extends string>({ label, options, value, onPick }: {
  label: string;
  options: { id: T; label: string }[];
  value: T;
  onPick: (id: T) => void;
}) {
  return (
    <div className="choice" role="group" aria-label={label}>
      <h3>{label}</h3>
      <div className="segmented">
        {options.map((option) => (
          <button key={option.id} aria-pressed={value === option.id} onClick={() => onPick(option.id)}>
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Customize({ layout, onChange, onClose }: Props) {
  const [dragging, setDragging] = useState<number | null>(null);

  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);

  const move = (from: number, to: number) => {
    if (to < 0 || to >= layout.panels.length || from === to) return;
    const panels = [...layout.panels];
    const [item] = panels.splice(from, 1);
    panels.splice(to, 0, item);
    onChange({ ...layout, panels });
  };

  const update = (index: number, change: Partial<Layout["panels"][number]>) => {
    onChange({ ...layout, panels: layout.panels.map((p, i) => (i === index ? { ...p, ...change } : p)) });
  };

  return (
    <aside className="drawer" role="dialog" aria-label="Customize board">
      <div className="drawer-head">
        <h2>Customize board</h2>
        <button onClick={onClose}>Done</button>
      </div>
      <Choice label="Theme" options={THEMES} value={layout.theme} onPick={(theme) => onChange({ ...layout, theme })} />
      <Choice label="Tickets column" options={SIDES} value={layout.side} onPick={(side) => onChange({ ...layout, side })} />
      <h3>Panels</h3>
      <p className="muted drawer-note">Drag a panel or use the arrows to change the order.</p>
      <ol className="panel-list">
        {layout.panels.map((panel, index) => {
          const required = REQUIRED_PANELS.includes(panel.id);
          return (
            <li
              key={panel.id}
              draggable
              className={dragging === index ? "dragging" : ""}
              onDragStart={() => setDragging(index)}
              onDragEnd={() => setDragging(null)}
              onDragOver={(event) => {
                event.preventDefault();
                if (dragging !== null && dragging !== index) {
                  move(dragging, index);
                  setDragging(index);
                }
              }}
            >
              <label className="panel-name">
                <input
                  type="checkbox"
                  checked={panel.visible}
                  disabled={required}
                  onChange={(event) => update(index, { visible: event.target.checked })}
                />
                <span>
                  {PANEL_NAMES[panel.id]}
                  {required && <small>Always shown</small>}
                </span>
              </label>
              <div className="panel-tools">
                <button
                  aria-pressed={!panel.wide}
                  aria-label={`Show ${PANEL_NAMES[panel.id]} at half width`}
                  onClick={() => update(index, { wide: !panel.wide })}
                >
                  Half
                </button>
                <button aria-label={`Move ${PANEL_NAMES[panel.id]} up`} disabled={index === 0} onClick={() => move(index, index - 1)}>
                  ↑
                </button>
                <button
                  aria-label={`Move ${PANEL_NAMES[panel.id]} down`}
                  disabled={index === layout.panels.length - 1}
                  onClick={() => move(index, index + 1)}
                >
                  ↓
                </button>
              </div>
            </li>
          );
        })}
      </ol>
      <button className="reset-layout" onClick={() => onChange({ ...DEFAULT_LAYOUT, theme: layout.theme })}>
        Reset layout
      </button>
      <p className="muted drawer-note">Saved in this browser.</p>
    </aside>
  );
}
