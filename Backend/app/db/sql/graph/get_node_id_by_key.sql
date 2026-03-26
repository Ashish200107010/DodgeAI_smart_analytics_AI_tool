SELECT node_id
FROM graph.graph_nodes
WHERE node_key = :node_key
LIMIT 1;

