WITH delivered AS (
  SELECT DISTINCT
    odi.reference_sd_document AS sales_order
  FROM raw.outbound_delivery_items odi
  WHERE odi.reference_sd_document IS NOT NULL
),
billed AS (
  SELECT DISTINCT
    odi.reference_sd_document AS sales_order
  FROM raw.billing_document_items bdi
  JOIN raw.outbound_delivery_items odi
    ON odi.delivery_document = bdi.reference_sd_document
  WHERE odi.reference_sd_document IS NOT NULL
)
SELECT
  soh.sales_order AS "salesOrder",
  (d.sales_order IS NOT NULL) AS "delivered",
  (b.sales_order IS NOT NULL) AS "billed"
FROM raw.sales_order_headers soh
LEFT JOIN delivered d ON d.sales_order = soh.sales_order
LEFT JOIN billed b ON b.sales_order = soh.sales_order
WHERE
  (d.sales_order IS NOT NULL AND b.sales_order IS NULL)
  OR
  (d.sales_order IS NULL AND b.sales_order IS NOT NULL)
LIMIT :limit;

