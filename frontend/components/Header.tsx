"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { FileText, Upload } from "lucide-react";
import Link from "next/link";

interface HeaderProps {
  apiOnline: boolean;
  onUploadClick?: () => void;
}

export function Header({ apiOnline, onUploadClick }: HeaderProps) {
  return (
    <motion.header
      initial={{ y: -12, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="sticky top-0 z-50 border-b border-ghost-border bg-paper-white/90 backdrop-blur-md"
    >
      <div className="mx-auto flex max-w-page items-center justify-between px-6 py-4 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-card bg-electric-violet">
            <FileText className="h-4 w-4 text-paper-white" />
          </div>
          <div>
            <p className="font-display text-heading-sm font-bold tracking-tight text-midnight-ink">
              DocIntel
            </p>
            <p className="text-caption text-muted-ash">Document Intelligence</p>
          </div>
        </div>

        <nav className="hidden items-center gap-2 md:flex">
          <Link href="#workspace">
            <Button variant="outline" className="px-4 py-1.5 text-caption">
              Workspace
            </Button>
          </Link>
          <Link href="#features">
            <Button variant="ghost" className="px-4 py-1.5 text-caption">
              Features
            </Button>
          </Link>
          <Badge variant={apiOnline ? "success" : "warning"}>
            {apiOnline ? "API Online" : "API Offline"}
          </Badge>
        </nav>

        <Button onClick={onUploadClick} className="text-caption md:text-body">
          <Upload className="h-4 w-4" />
          Upload PDF
        </Button>
      </div>
    </motion.header>
  );
}
