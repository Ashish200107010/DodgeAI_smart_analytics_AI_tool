SELECT
  (SELECT COUNT(*) FROM graph.graph_edges WHERE dst_node_id = :node_id) AS in_degree,
  (SELECT COUNT(*) FROM graph.graph_edges WHERE src_node_id = :node_id) AS out_degree;

