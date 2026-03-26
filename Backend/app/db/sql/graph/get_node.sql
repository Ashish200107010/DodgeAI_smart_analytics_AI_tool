SELECT
  node_id,
  node_key,
  node_type,
  label,
  attrs
FROM graph.graph_nodes
WHERE node_id = :node_id
LIMIT 1;

