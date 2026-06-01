"use client";

import Link from "next/link";
import { ArchitectureDiagram } from "@/components/ArchitectureDiagram";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/Button";
import { checkHealth } from "@/lib/api";
import { useEffect, useState } from "react";

const PAGE_X =
  "px-6 md:px-12 lg:px-16 xl:px-24 2xl:px-32";

export default function ArchitecturePage() {
  const [apiOnline, setApiOnline] = useState(false);

  useEffect(() => {
    checkHealth().then(setApiOnline);
  }, []);

  return (
    <div className="min-h-screen bg-midnight">
      <Header apiOnline={apiOnline} />
      <main className={`w-full py-12 lg:py-16 ${PAGE_X}`}>
        <div className="grid w-full grid-cols-1 items-start gap-12 lg:grid-cols-12 lg:gap-16 xl:gap-24">
          <div className="lg:col-span-4">
            <h1 className="font-display text-[clamp(2rem,4vw,3.5rem)] font-normal leading-[1.05] tracking-[-0.02em] text-ghost-ash">
              RAG pipeline architecture
            </h1>
            <p className="mt-6 text-subheading font-light leading-relaxed text-slate">
              How DocIntel retrieves, gates, generates, and verifies answers.
              Use Play flow for demo-ready walkthroughs.
            </p>
            <Link href="/" className="mt-8 inline-block">
              <Button variant="ghost">Back to workspace</Button>
            </Link>
          </div>

          <div className="w-full lg:col-span-8">
            <ArchitectureDiagram />
          </div>
        </div>
      </main>
    </div>
  );
}
