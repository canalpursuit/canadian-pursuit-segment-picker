# canadian-pursuit-segment-picker
Segment Data for Canadian Pursuit for Mental Health

## Browser smoke tests

Prerequisites: Node.js 20 or newer and npm. From this repository:

```powershell
npm ci
npx playwright install chromium
npm run test:smoke
```

The runner starts and stops a localhost server automatically. It uses one Chromium worker, no retries, real route data and Leaflet 1.9.4, a test-only parent iframe harness, synthetic registration details, and intercepted map tiles. No Wix CMS writes or emails occur. Playwright's virtual clock completes the application's startup overview timers before interaction.

Coverage: Confirmed status survives selection/deselection; registration success clears/reset selection and form and requests refreshed statuses; registration errors retain the form and allow a valid retry. The harness checks the picker message contract, not Wix backend behavior or permissions.

`npm run test:report` opens the HTML report. Failure screenshots/traces live in `test-results/`; reports, saved authentication, dependencies and local evidence under `playwright/.cache/` are ignored. Keep the npm manifest and lockfile together.

Cross-repository execution evidence and remaining real-Wix checks: `../canadian-pursuit-wix/docs/work/initial-testing.md`. Do not deploy to GitHub Pages just to run these tests; pushing this repository's main branch deploys independently of Wix.

On Windows the test configuration uses `playwright/.cache/tmp` for temporary browser profiles because this agent host could not reliably clean up profiles in the system Temp directory. This changes only the test process environment. Baseline failure evidence from the proof run is retained locally under `playwright/.cache/baseline-results/` and `playwright/.cache/baseline-report/`.

## Phone performance

Manual browsing renders up to 20 matching segments at a time in both the list and map. Use Previous segments / Next segments to browse; calendar-date and text filters search the whole province. Selections survive paging and switching provinces. Visited province data is released and selections retain metadata without geometry. Popup HTML is generated on demand and offscreen map tile retention is reduced. Source route coordinates are unchanged.

`npm run test:smoke` includes phone-sized checks for bounded map/list rendering, cross-province checkout and registration when background tiles fail. These are simulated backend tests; actual phone and Wix integration testing are still required.

## Candidate registration flow

Participants choose random virtual countryside selection or manual selection with virtual/on-site participation. Random selection requires an explicitly Available approved ID from data/random-eligible.json. Checkout requires the waiver in data/waiver.json, an acceptance checkbox and typed name; Wix validates and stores server-side evidence. Deploy with the matching Wix bridge/backend, not independently. Nine Chromium tests cover the candidate; real-member authorization remains a Wix release check.
