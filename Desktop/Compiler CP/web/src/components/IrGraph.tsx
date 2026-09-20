import ReactFlow, { Background, Controls, type Edge, type Node } from 'reactflow';
import type { IrGraph as IrGraphType } from '../types';

export function IrGraph({ ir }: { ir: IrGraphType | null | undefined }) {
  if (!ir) {
    return <div className="empty">Compile to view the IR graph.</div>;
  }
  const nodes: Node[] = ir.nodes.map((node, index) => ({
    id: node.id,
    position: { x: (index % 2) * 280, y: Math.floor(index / 2) * 130 },
    data: { label: `${index + 1}. ${node.label}` },
    type: 'default'
  }));
  const edges: Edge[] = ir.edges.map((edge) => ({
    id: `${edge.from}-${edge.to}`,
    source: edge.from,
    target: edge.to,
    animated: true,
    label: edge.kind
  }));
  return (
    <div className="graph">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
