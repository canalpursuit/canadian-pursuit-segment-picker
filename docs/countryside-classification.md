# Countryside random assignment — classification protocol

Status: **Not yet classified. Random assignment must remain disabled until verified.**

Definition: A countryside segment is an entire route segment outside the built-up footprint of towns and cities. Municipal boundaries are not used as an exclusion by themselves.

Primary source: Statistics Canada 2021 census population centre boundaries (POPCTR) and designated place boundaries (DPL). These alone are not sufficient to detect all hamlets and small settlements. Supplement with settlement/built-up footprint mapping and review uncertain cases.

For each segment:
1. Use the complete segment polyline geometry, not only its endpoints.
2. Reproject the route and settlement polygons to the same coordinate reference system.
3. Exclude any segment intersecting a mapped built-up settlement polygon.
4. Review small settlements not covered by population centre polygons, and any borderline segments.
5. Mark eligible only after review. Unreviewed/uncertain segments are NOT eligible.
6. Before assignment, exclude segments with current Tentative, Confirmed or other claimed statuses. Availability must ultimately be rechecked and reserved atomically in Wix to avoid duplicate assignments.

The final approved segment ID list will be committed as `data/countryside-eligible.js`, with metadata including source date and review status. An empty list is intentional until geographic verification is complete.

References:
- https://open.canada.ca/data/en/dataset/ef70dc3b-1069-4037-9bce-61f47e628a1d
- https://www150.statcan.gc.ca/n1/pub/92-160-g/92-160-g2021002-eng.htm
