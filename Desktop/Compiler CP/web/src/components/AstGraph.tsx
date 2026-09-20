import type { AstNode } from '../types';

export function AstGraph({ ast }: { ast: AstNode | null | undefined }) {
  if (!ast) {
    return <div className="empty">Compile to view the AST.</div>;
  }
  return <div className="tree">{renderNode(ast)}</div>;
}

function renderNode(node: AstNode) {
  const label = [node.type, node.kind, node.name].filter(Boolean).join(' ');
  return (
    <details open key={`${label}-${node.loc?.line ?? 0}-${node.loc?.column ?? 0}`}>
      <summary>{label}</summary>
      {node.value !== undefined && <pre>{JSON.stringify(node.value, null, 2)}</pre>}
      <div className="tree-children">{node.children?.map(renderNode)}</div>
    </details>
  );
}
