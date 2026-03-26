SELECT
  bdi.material AS "product",
  COUNT(DISTINCT bdi.billing_document) AS "billingDocumentCount"
FROM raw.billing_document_items bdi
GROUP BY bdi.material
ORDER BY "billingDocumentCount" DESC
LIMIT :limit;

