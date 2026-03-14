import { useCallback, useRef, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphNode, GraphEdge } from "../types/index.ts";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick: (nodeId: string) => void;
  focusNodeId?: string | null;
}

const NODE_COLORS: Record<string, string> = {
  semantic: "#3b82f6",
  episodic: "#22c55e",
  procedural: "#f97316",
};

const EDGE_COLORS: Record<string, string> = {
  relates_to: "#4b5563",
  caused_by: "#ef4444",
  depends_on: "#3b82f6",
  co_occurs: "#8b5cf6",
  contradicts: "#f59e0b",
  supersedes: "#06b6d4",
};

interface GraphInternalNode extends GraphNode {
  x?: number;
  y?: number;
}

export default function GraphView({ nodes, edges, onNodeClick, focusNodeId }: Props) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);

  useEffect(() => {
    if (focusNodeId && fgRef.current) {
      const node = nodes.find((n) => n.id === focusNodeId);
      if (node) {
        setTimeout(() => {
          fgRef.current?.centerAt(0, 0, 500);
        }, 500);
      }
    }
  }, [focusNodeId, nodes]);

  const graphData = {
    nodes: nodes.map((n) => ({ ...n })),
    links: edges.map((e) => ({ ...e })),
  };

  const nodeCanvasObject = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const gNode = node as GraphInternalNode;
      const size = Math.max(3, Math.min(12, (gNode.access_count || 1) * 2));
      const color = gNode.is_deprecated ? "#6b7280" : (NODE_COLORS[gNode.type] ?? "#6b7280");

      ctx.beginPath();
      ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      if (gNode.id === focusNodeId) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      if (globalScale > 1.5) {
        ctx.font = `${10 / globalScale}px sans-serif`;
        ctx.fillStyle = "#94a3b8";
        ctx.textAlign = "center";
        ctx.fillText(gNode.label, node.x!, node.y! + size + 8 / globalScale);
      }
    },
    [focusNodeId]
  );

  return (
    <div className="w-full h-full bg-slate-950 rounded-xl overflow-hidden">
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeCanvasObject={nodeCanvasObject}
        linkColor={(link: Record<string, unknown>) => EDGE_COLORS[(link.type as string) ?? "relates_to"] ?? "#4b5563"}
        linkWidth={(link: Record<string, unknown>) => Math.max(0.5, ((link.weight as number) ?? 0.5) * 3)}
        onNodeClick={(node: Record<string, unknown>) => onNodeClick(node.id as string)}
        backgroundColor="#020617"
        linkDirectionalParticles={0}
        cooldownTicks={100}
        nodeRelSize={4}
      />
    </div>
  );
}
