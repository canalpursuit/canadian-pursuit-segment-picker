CANADIAN PURSUIT SEGMENT PICKER — PROTOTYPE

HOW TO OPEN
1. Extract the ZIP file.
2. Keep index.html and the data folder together.
3. Open index.html in Chrome while connected to the internet.
   Leaflet and the OpenStreetMap background tiles load from the internet.

HOW SEGMENTS ARE DEFINED
A selectable segment starts at a schedule marker whose Map Label contains the word
"Section" and runs along the GPX track to the next such marker. Day, date, segment
length and notes come from Segment data r00.xlsx.

WHAT THE PROTOTYPE DOES
- Lightweight national overview.
- Click a province/territory region to load only its detailed route.
- Filter by day, maximum distance, or text.
- Click an individual segment to zoom to it.
- Select multiple segments.
- Export selected segments to CSV.

The Manitoba/Saskatchewan source is kept as one region, as supplied.
The Alberta/British Columbia source is kept as one region, as supplied.

NEXT DEVELOPMENT STEP
Once the browsing/selection experience is approved, the selection can be connected
to a registration form/database so a participant submits name, email, phone and
selected segment IDs, and the public map can show which segments are still available.


VERSION 2 CHANGES
- Added Canadian Pursuit branded header and dedicated sponsor/partner logo area.
  Placeholder logo boxes are used until the actual logo image files are supplied to this build.
- Added prominent Nunavut, Northwest Territories and Yukon callouts on the Canada overview.
- Added START and END markers when a segment is shown or selected.
- CSV export now includes Start Latitude, Start Longitude, End Latitude and End Longitude.
- Segment status defaults to "Available".
- When selected in this prototype, status changes to "Available to run with others".
  In the future database-backed version, that status will be persistent for all visitors.


VERSION 4 — CARTO BASEMAP
- Replaced direct OpenStreetMap public tile-server access with CARTO Voyager raster basemap.
- CARTO API key is configured in index.html.
- Required OpenStreetMap + CARTO attribution remains visible.
- Added a graceful warning if background map tiles fail; route/interface data remains available.
- Leaflet and the Canadian Pursuit route/segment system are otherwise unchanged.

SECURITY NOTE
Before public launch, restrict the CARTO key to the final Canadian Pursuit website domain in the CARTO dashboard.


VERSION 5 — CHECKOUT / REGISTRATION WORKFLOW
- Added Check Out / Register after segment selection.
- Required fields: first name, last name, city of residence, email address.
- Required participation choice: On location or Virtual.
- Added optional comments/message field.
- Registration includes all selected segment IDs and route metadata.
- On-location prototype submissions mark selected segments Tentatively Taken locally.
- Virtual prototype submissions do not reserve the physical segment.
- Prototype pending registrations are stored only in the current browser (localStorage).
- Live organizer notification, shared status, approval/decline, confirmation email, and tracking-spreadsheet integration require the production backend/database connection.


VERSION 6 — ROUTE DISPLAY / STATUS COLOURS
- Canada overview route is drawn automatically when the page first opens.
- All province/territory route lines use the same red colour.
- Available segments are red.
- On-location registrations marked Tentatively Taken are yellow.
- Confirmed / Available to run with others segments are green.
- Added a red/yellow/green route-status legend.
- Confirmation remains a future backend/admin action; the interface is now prepared to render confirmed status in green.


VERSION 7 — SELECTION STATUS / COMBINED COORDINATES
- Selecting an available segment immediately changes it to yellow and displays status Tentative.
- Confirmed segments remain green.
- Deselecting restores the underlying status colour.
- CSV start latitude/longitude are combined as "latitude, longitude".
- CSV end latitude/longitude are combined as "latitude, longitude".
