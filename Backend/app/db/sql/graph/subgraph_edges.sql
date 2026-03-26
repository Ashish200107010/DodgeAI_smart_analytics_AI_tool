WITH RECURSIVE frontier AS (
  SELECT
    unnest(CAST(:seed_node_ids AS uuid[])) AS node_id,
    0 AS depth
  UNION ALL
  SELECT
    CASE
      WHEN e.src_node_id = f.node_id THEN e.dst_node_id
      ELSE e.src_node_id
    END AS node_id,
    f.depth + 1 AS depth
  FROM frontier f
  JOIN graph.graph_edges e
    ON (e.src_node_id = f.node_id OR e.dst_node_id = f.node_id)
  WHERE f.depth < :max_hops
    AND e.edge_type = ANY(CAST(:edge_type_codes AS text[]))
),
node_set AS (
  SELECT DISTINCT node_id FROM frontier
),
edge_set AS (
  SELECT DISTINCT
    e.edge_id,
    e.edge_type,
    e.src_node_id,
    e.dst_node_id,
    e.evidence
  FROM graph.graph_edges e
  JOIN node_set a ON a.node_id = e.src_node_id
  JOIN node_set b ON b.node_id = e.dst_node_id
  WHERE e.edge_type = ANY(CAST(:edge_type_codes AS text[]))
  LIMIT :max_edges
)
SELECT * FROM edge_set;

