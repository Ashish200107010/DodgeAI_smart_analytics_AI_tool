SELECT
  edge_id,
  edge_type,
  src_node_id,
  dst_node_id,
  evidence
FROM graph.graph_edges
WHERE edge_type = ANY(CAST(:edge_type_codes AS text[]))
  AND (
    (:direction = 'out' AND src_node_id = :node_id)
    OR (:direction = 'in' AND dst_node_id = :node_id)
    OR (:direction = 'both' AND (src_node_id = :node_id OR dst_node_id = :node_id))
  )
LIMIT :limit;

