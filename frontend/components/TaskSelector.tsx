"use client";

import { cn } from "@/lib/utils";
import type { ChatTask } from "@/lib/types";

const tasks: { id: ChatTask; label: string }[] = [
  { id: "qa", label: "Q&A" },
  { id: "summarize", label: "Summarize" },
  { id: "anomaly", label: "Anomalies" },
];

interface TaskSelectorProps {
  value: ChatTask;
  onChange: (task: ChatTask) => void;
}

export function TaskSelector({ value, onChange }: TaskSelectorProps) {
  return (
    <div
      role="tablist"
      aria-label="Analysis mode"
      className="inline-flex rounded-btn bg-charcoal p-1 shadow-inset"
    >
      {tasks.map((task) => {
        const active = value === task.id;
        return (
          <button
            key={task.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(task.id)}
            className={cn(
              "rounded-btn px-4 py-2 text-caption transition-colors duration-300",
              active
                ? "bg-ghost-ash font-medium text-midnight"
                : "text-slate hover:text-ghost-ash"
            )}
          >
            {task.label}
          </button>
        );
      })}
    </div>
  );
}
