import ELK from 'elkjs/lib/elk.bundled.js';

const elk = new ELK();

export async function getLayoutedGraph(nodes: any[], edges: any[]) {
  const elkNodes = nodes.map((n) => ({
    id: n.id,
    width: 224, // Matches w-56 (224px) CustomWorkflowNode width
    height: 96,  // Matches custom node height
  }));

  const elkEdges = edges.map((e) => ({
    id: e.id,
    sources: [e.source],
    targets: [e.target],
  }));

  const graph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.layered.spacing.nodeNodeBetweenLayers': '100',
      'elk.spacing.nodeNode': '50',
    },
    children: elkNodes,
    edges: elkEdges,
  };

  try {
    const layouted = await elk.layout(graph);
    
    const layoutedNodes = nodes.map((n) => {
      const elkNode = layouted.children?.find((cn) => cn.id === n.id);
      if (elkNode && elkNode.x !== undefined && elkNode.y !== undefined) {
        return {
          ...n,
          position: {
            x: elkNode.x,
            y: elkNode.y,
          },
        };
      }
      return n;
    });

    return { nodes: layoutedNodes, edges };
  } catch (error) {
    console.error('ELK Layout error:', error);
    return { nodes, edges };
  }
}
