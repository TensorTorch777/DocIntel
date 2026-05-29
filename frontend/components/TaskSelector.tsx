"use client";

import { cn } from "@/lib/utils";
import type { ChatTask } from "@/lib/types";
import { AlertTriangle, FileSearch, MessageSquare } from "lucide-react";
import { motion } from "framer-motion";

const tasks: {
  id: ChatTask;
  label: string;
  description: string;
  icon: typeof MessageSquare;
}[] = [
  {
    id: "qa",
    label: "Q&A",
    description: "Grounded answers from retrieved chunks",
    icon: MessageSquare,
  },
  {
    id: "summarize",
    label: "Summarize",
    description: "Structured report overview",
    icon: FileSearch,
  },
  {
    id: "anomaly",
    label: "Anomalies",
    description: "Flag inconsistent parameters",
    icon: AlertTriangle,
  },
];

interface TaskSelectorProps {
  value: ChatTask;
  onChange: (task: ChatTask) => void;
}

export function TaskSelector({ value, onChange }: TaskSelectorProps) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {tasks.map((task) => {
        const Icon = task.icon;
        const active = value === task.id;
        return (
          <motion.button
            key={task.id}
            type="button"
            onClick={() => onChange(task.id)}
            whileTap={{ scale: 0.98 }}
            className={cn(
              "rounded-card border p-4 text-left transition-colors",
              active
                ? "border-electric-violet/30 bg-electric-violet/5"
                : "border-ghost-border bg-paper-white hover:bg-cloud-canvas"
            )}
          >
            <Icon
              className={cn(
                "h-4 w-4",
                active ? "text-electric-violet" : "text-muted-ash"
              )}
            />
            <p className="mt-2 text-body text-midnight-ink">{task.label}</p>
            <p className="mt-1 text-caption text-muted-ash">{task.description}</p>
          </motion.button>
        );
      })}
    </div>
  );
}
