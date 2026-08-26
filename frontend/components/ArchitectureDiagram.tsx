"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Pause, Play, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

type StageId = "understanding" | "retrieval" | "generation" | "quality";

interface StageTheme {
  id: StageId;
  title: string;
  panel: string;
  panelBorder: string;
  node: string;
  nodeBorder: string;
  text: string;
}

interface PipelineNode {
  id: string;
  title: string;
  subtitle: string;
  stageId: StageId | "entry" | "exit";
  shape: "pill" | "box" | "diamond";
}

const STAGES: StageTheme[] = [
  {
    id: "understanding",
    title: "Query Understanding",
    panel: "bg-charcoal",
    panelBorder: "border-charcoal",
    node: "bg-midnight",
    nodeBorder: "border-charcoal",
    text: "text-ghost-ash",
  },
  {
    id: "retrieval",
    title: "Retrieval Pipeline",
    panel: "bg-charcoal",
    panelBorder: "border-charcoal",
    node: "bg-midnight",
    nodeBorder: "border-charcoal",
    text: "text-ghost-ash",
  },
  {
    id: "generation",
    title: "Grounded Generation",
    panel: "bg-charcoal",
    panelBorder: "border-charcoal",
    node: "bg-midnight",
    nodeBorder: "border-charcoal",
    text: "text-ghost-ash",
  },
  {
    id: "quality",
    title: "Quality & Output",
    panel: "bg-charcoal",
    panelBorder: "border-charcoal",
    node: "bg-midnight",
    nodeBorder: "border-charcoal",
    text: "text-ghost-ash",
  },
];

const NODES: PipelineNode[] = [
  {
    id: "query",
    title: "User Query",
    subtitle: "Natural language question",
    stageId: "entry",
    shape: "pill",
  },
  {
    id: "qe",
    title: "Query Expansion",
    subtitle: "Register aliases · entity detection",
    stageId: "understanding",
    shape: "box",
  },
  {
    id: "moe",
    title: "MoE Router",
    subtitle: "Sparse expert gating · text · vision · audio · video",
    stageId: "understanding",
    shape: "box",
  },
  {
    id: "hr",
    title: "Hybrid Retrieval",
    subtitle: "Vector + BM25 → RRF fusion",
    stageId: "retrieval",
    shape: "box",
  },
  {
    id: "rrf",
    title: "RRF Fusion",
    subtitle: "Merge ranked candidate lists",
    stageId: "retrieval",
    shape: "box",
  },
  {
    id: "rer",
    title: "Cross-Encoder Rerank",
    subtitle: "Neural relevance scoring",
    stageId: "retrieval",
    shape: "box",
  },
  {
    id: "dr",
    title: "Definition Resolution",
    subtitle: "Pin authoritative definitions",
    stageId: "retrieval",
    shape: "box",
  },
  {
    id: "eg",
    title: "Evidence Gate",
    subtitle: "Sufficiency check before generation",
    stageId: "generation",
    shape: "diamond",
  },
  {
    id: "llm",
    title: "Answer Generation",
    subtitle: "Grounded completion from context",
    stageId: "generation",
    shape: "box",
  },
  {
    id: "ver",
    title: "Verification",
    subtitle: "Claim support · hallucination risk",
    stageId: "quality",
    shape: "box",
  },
  {
    id: "ans",
    title: "Final Answer",
    subtitle: "Streamed response + citations",
    stageId: "exit",
    shape: "pill",
  },
];

const MAIN_FLOW = [
  "query",
  "qe",
  "moe",
  "hr",
  "rrf",
  "rer",
  "dr",
  "eg",
  "llm",
  "ver",
  "ans",
] as const;

const STAGE_BY_ID = Object.fromEntries(STAGES.map((s) => [s.id, s])) as Record<
  StageId,
  StageTheme
>;

function FlowArrow({ active }: { active: boolean }) {
  return (
    <div className="relative flex flex-col items-center py-1">
      <div className="relative h-10 w-px overflow-hidden bg-charcoal">
        <AnimatePresence>
          {active && (
            <motion.div
              className="absolute left-1/2 h-3 w-3 -translate-x-1/2 rounded-full bg-accent"
              initial={{ top: "-10px", opacity: 0 }}
              animate={{ top: ["-10px", "38px"], opacity: [0, 1, 1, 0] }}
              transition={{
                duration: 1.1,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          )}
        </AnimatePresence>
      </div>
      <div className="mt-0.5 h-0 w-0 border-x-[7px] border-t-[9px] border-x-transparent border-t-slate" />
    </div>
  );
}

function PipelineNodeCard({
  node,
  active,
  selected,
  onSelect,
}: {
  node: PipelineNode;
  active: boolean;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const stage = stageForNode(node);
  const isEntry = node.stageId === "entry";
  const isExit = node.stageId === "exit";

  const colorClasses = isEntry
    ? "bg-charcoal text-ghost-ash border border-ghost-ash/40"
    : isExit
      ? "bg-charcoal text-ghost-ash border border-accent/40"
      : cn(stage?.node, stage?.nodeBorder, stage?.text, "border");

  const label = (
    <>
      <p className="font-display text-sm font-semibold leading-tight">
        {node.title}
      </p>
      <p className="mt-1 text-xs leading-snug text-slate">{node.subtitle}</p>
    </>
  );

  if (node.shape === "diamond") {
    return (
      <div className="relative mx-auto w-full max-w-[280px] py-2">
        <motion.button
          type="button"
          onClick={() => onSelect(node.id)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className={cn(
            "group relative mx-auto block w-full cursor-pointer text-center",
            selected && !active && "opacity-90"
          )}
        >
          <div
            className={cn(
              "mx-auto max-w-[220px] rounded-card border px-4 py-3 transition-[border-color,box-shadow] duration-300",
              colorClasses,
              active && "border-accent/50 ring-1 ring-accent/30",
              selected && !active && "border-ghost-ash/30"
            )}
          >
            {label}
          </div>
          {active && (
            <motion.span
              className="absolute right-2 top-2 h-3 w-3 rounded-full bg-accent"
              animate={{ scale: [1, 1.35, 1], opacity: [1, 0.6, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          )}
        </motion.button>
      </div>
    );
  }

  return (
    <motion.button
      type="button"
      layout
      onClick={() => onSelect(node.id)}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      animate={
        active ? { scale: 1.03 } : selected ? { scale: 1.01 } : { scale: 1 }
      }
      className={cn(
        "relative w-full cursor-pointer text-center transition-[border-color,opacity] duration-300",
        node.shape === "pill" && "rounded-btn px-6 py-3",
        node.shape === "box" && "rounded-card px-4 py-3",
        colorClasses,
        active && "border-accent/50",
        selected && !active && "border-ghost-ash/30 opacity-90"
      )}
    >
      {label}
      {active && (
        <motion.span
          className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-accent"
          animate={{ scale: [1, 1.35, 1], opacity: [1, 0.6, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
      )}
    </motion.button>
  );
}

function stageForNode(node: PipelineNode): StageTheme | null {
  if (node.stageId === "entry" || node.stageId === "exit") return null;
  return STAGE_BY_ID[node.stageId];
}

function StagePanel({
  stage,
  children,
  highlighted,
}: {
  stage: StageTheme;
  children: ReactNode;
  highlighted: boolean;
}) {
  return (
    <motion.div
      animate={highlighted ? { scale: 1.01 } : { scale: 1 }}
      className={cn("rounded-card border p-4", stage.panel, stage.panelBorder)}
    >
      <p className={cn("mb-3 text-center font-display text-sm font-semibold", stage.text)}>
        {stage.title}
      </p>
      <div className="space-y-0">{children}</div>
    </motion.div>
  );
}

export function ArchitectureDiagram({ compact = false }: { compact?: boolean }) {
  const [selectedId, setSelectedId] = useState("query");
  const [activeFlowIndex, setActiveFlowIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const nodeById = useMemo(
    () => Object.fromEntries(NODES.map((n) => [n.id, n])),
    []
  );

  const selectedNode = nodeById[selectedId] ?? NODES[0];
  const activeNodeId = MAIN_FLOW[activeFlowIndex];
  const activeStageId = nodeById[activeNodeId]?.stageId;

  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setActiveFlowIndex((i) => (i + 1) % MAIN_FLOW.length);
    }, 1400);
    return () => clearInterval(timer);
  }, [isPlaying]);

  useEffect(() => {
    if (isPlaying) setSelectedId(activeNodeId);
  }, [activeNodeId, isPlaying]);

  const reset = useCallback(() => {
    setIsPlaying(false);
    setActiveFlowIndex(0);
    setSelectedId("query");
  }, []);

  const renderConnector = (fromId: string) => (
    <FlowArrow key={`arrow-${fromId}`} active={isPlaying && activeNodeId === fromId} />
  );

  const renderNode = (id: string) => (
    <PipelineNodeCard
      key={id}
      node={nodeById[id]}
      active={isPlaying && activeNodeId === id}
      selected={selectedId === id}
      onSelect={setSelectedId}
    />
  );

  return (
    <div className={cn("w-full", compact && "max-w-xl")}>
      <div className="mb-6 flex flex-wrap items-center justify-center gap-3">
        <Button
          variant={isPlaying ? "ghost" : "primary"}
          className="text-caption !text-midnight"
          onClick={() => setIsPlaying((p) => !p)}
        >
          {isPlaying ? (
            <>
              <Pause className="h-4 w-4" /> Pause flow
            </>
          ) : (
            <>
              <Play className="h-4 w-4" /> Play flow
            </>
          )}
        </Button>
        <Button variant="ghost" className="text-caption" onClick={reset}>
          <RotateCcw className="h-4 w-4" /> Reset
        </Button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="obsidian-glass p-6"
      >
        {renderNode("query")}
        {renderConnector("query")}

        <StagePanel
          stage={STAGE_BY_ID.understanding}
          highlighted={isPlaying && activeStageId === "understanding"}
        >
          {renderNode("qe")}
          {renderConnector("qe")}
          {renderNode("moe")}
        </StagePanel>
        {renderConnector("moe")}

        <StagePanel
          stage={STAGE_BY_ID.retrieval}
          highlighted={isPlaying && activeStageId === "retrieval"}
        >
          {renderNode("hr")}
          {renderConnector("hr")}
          {renderNode("rrf")}
          {renderConnector("rrf")}
          {renderNode("rer")}
          {renderConnector("rer")}
          {renderNode("dr")}
        </StagePanel>
        {renderConnector("dr")}

        <StagePanel
          stage={STAGE_BY_ID.generation}
          highlighted={isPlaying && activeStageId === "generation"}
        >
          {renderNode("eg")}
          {renderConnector("eg")}
          {renderNode("llm")}
        </StagePanel>
        {renderConnector("llm")}

        <StagePanel
          stage={STAGE_BY_ID.quality}
          highlighted={isPlaying && activeStageId === "quality"}
        >
          {renderNode("ver")}
        </StagePanel>
        {renderConnector("ver")}

        {renderNode("ans")}

        {selectedId === "eg" && (
          <motion.p
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="mt-4 border border-dashed border-charcoal px-3 py-2 text-center text-xs text-slate"
          >
            If evidence is insufficient, the gate skips generation and returns an
            abstention directly to Final Answer.
          </motion.p>
        )}
      </motion.div>

      <AnimatePresence mode="wait">
        <motion.div
          key={selectedNode.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="mt-6 obsidian-glass p-4 text-center"
        >
          <p className="font-display text-heading-sm font-medium text-ghost-ash">
            {selectedNode.title}
          </p>
          <p className="mt-1 text-caption text-slate">{selectedNode.subtitle}</p>
          <p className="mt-3 text-caption text-iridescent">
            Click any stage or press Play flow to animate the pipeline
          </p>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
