# Integrate the TPFI demonstration guides
Target: SoPerez1/tpfi_is2 main at 0ec7f403b327d2b8a0a9ee88083cdb9ac8a83954; source: bedc0a04ad2dc762dc97665451a0131026aee5d1.
Strategy: feature-branch-chain; docs/tpfi-demo <- docs/tpfi-demo-local <- docs/tpfi-demo-aws. Verification: structural guide checks and hosted CI/Documentation. Engram unavailable; mirror pending.

## Specs
S1. User requested: "subime todos los cambios".
S2. User asked: "para que todos mis compañeros vean los cambios en git hay que hacer pr?" and accepted the proposal to open, review and merge a PR into main with: "okey quiero hacer eso".
S3. User selected: "Cadena con rama de integración"; option description: "Revisar dos PR pequeños y llevar el conjunto a main al final."

## Tasks
T1 | S1-S3 | inline remote preflight | done | commit: source bedc0a0; target 0ec7f40 | Clean source branch and exact remote heads confirmed; source CI40881721274 and Documentation40881721149 completed success; Pages flag absent; no existing open source-to-main PR.
T2 | S1-S3 | inline documentation slicing | in_progress | commit: pending | Create a draft tracker and two child slices without rewriting existing history; preserve source bytes and application/workflow files. Forecast: local guide 233 lines plus README/tracking, AWS guide 267 lines plus README; each child under the advisory 400-line review budget.
T3 | S2-S3 | parent PR publication and hosted verification | pending | commit: pending | Draft tracker -> main, local -> tracker, AWS -> local. Follow target template; no invented issue/labels, no AWS operation or Pages deployment. Check exact head identities and hosted results before merging.
T4 | S2-S3 | parent pinned integration and readback | pending | commit: pending | Merge AWS into local, local into tracker, then ready/merge tracker into main after passing checks; no admin bypass, force-push or branch deletion. Confirm final main content and hosted checks.

## Log
L1. Original implementation request: "podes armar un archivo .txt o un .md en donde esten todos los comandos necesarios para poder mostrar el tp".
L2. AWS guide request: "dejalo en un md tambien". Publication request: "subime todos los cambios". Both guides, README links and existing delivery evidence were committed by the user as 18ac5f3; normal merge bedc0a0 integrated remote history, resolved only the old delivery tracker and passed 8 focused tests. Remote source hash was confirmed after push.
L3. Current integration request: "okey quiero hacer eso" in response to opening, reviewing and merging a PR into main. Delivery choice: "Cadena con rama de integración". This is delivery-only: preserve guide bytes and existing application, tests, dependencies and workflow configuration. No meaningful RED applies to passive document slicing; structural checks and existing/public hosted checks are applicable.
L4. Source native review target 4ef79c95b176475387c27ce8c75e6b25f33d0d36b1baeba3b3e8dea209aabd72 was classified low; acknowledgement for review-fda9157b7218a949 completed and authority burned. This evidence is not approval for a different candidate. Initial lens request was rejected without starting; later candidate-view cleanup error reconciled to approved through bound STATUS, then acknowledgement succeeded.
L5. Read-only GitHub preflight confirmed main=0ec7f40, source=bedc0a0, push permission and normal merge support, no auto-delete and no DOCS_DEPLOYMENT_ENABLED variable. Existing source push CI and Documentation both completed success. Target CONTRIBUTING/template require relevant checks and provenance, with optional issue linkage; Gentle-specific issue/type-label requirements do not apply. A registered same-clone worktree holds the new chain; primary source branch remains intact.
