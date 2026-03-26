SELECT
  node_id,
  node_key,
  node_type,
  label,
  attrs
FROM graph.graph_nodes
WHERE node_id = ANY(CAST(:node_ids AS uuid[]));

