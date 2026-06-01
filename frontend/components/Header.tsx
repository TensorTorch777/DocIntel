"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { useUI } from "@/context/UIContext";
import { cn } from "@/lib/utils";
import { RotateCcw } from "lucide-react";
import Link from "next/link";

interface HeaderProps {
  apiOnline: boolean;
  hasDocument?: boolean;
  onStartOver?: () => void;
}

export function Header({
  apiOnline,
  hasDocument,
  onStartOver,
}: HeaderProps) {
  const { portfolioMode, togglePortfolioMode } = useUI();

  return (
    <motion.header
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="sticky top-0 z-50 border-b border-charcoal bg-midnight/90 backdrop-blur-md"
    >
      <div className="flex h-14 items-center justify-between px-6 md:px-12 lg:px-16 xl:px-24 2xl:px-32">
        <Link href="/" className="font-display text-body font-normal text-ghost-ash">
          DocIntel
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {hasDocument && (
            <Link
              href="/#workspace"
              className="text-caption text-slate transition-colors hover:text-ghost-ash"
            >
              Workspace
            </Link>
          )}
          <Link
            href="/architecture"
            className="text-caption text-slate transition-colors hover:text-ghost-ash"
          >
            Architecture
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          {hasDocument && onStartOver && (
            <button
              type="button"
              onClick={onStartOver}
              className="inline-flex items-center gap-1.5 text-caption text-slate transition-colors hover:text-ghost-ash"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Start over</span>
            </button>
          )}
          <button
            type="button"
            onClick={togglePortfolioMode}
            className={cn(
              "rounded-btn px-3 py-1.5 text-caption transition-colors",
              portfolioMode
                ? "bg-charcoal font-medium text-ghost-ash shadow-inset"
                : "text-slate hover:text-ghost-ash"
            )}
          >
            Present
          </button>
          <Badge variant={apiOnline ? "success" : "warning"}>
            {apiOnline ? "Online" : "Offline"}
          </Badge>
        </div>
      </div>
    </motion.header>
  );
}
