# Changelog

## [0.2.0] — 2026-03

### Added
- Three-tier permission system: Alliance Leader / Corp CEO / Member views
- IMP ESI compliance report upload and parsing
- IMP Attendance CSV upload with per-corp aggregation
- Corp CEO view: own corp ESI status card + member breakdown
- Member view: own character attendance only
- Alliance view: full cross-corp data table with color-coded ESI columns
- IMP ESI compliance summary (PASS / FAIL / NO TOKEN / Unregistered totals)
- Manual Rebuild and Finalize controls (alliance only)
- Celery daily snapshot task
- JSON API endpoint for corp stats
- Manual snapshot trigger (alliance only, for testing)

### Changed
- Renamed from `igc_cn_toolbox` to `aa_imperium_report`
- All UI text changed to English
- Column ordering: Corp | Members | Total Fleets | Per Capita | IGC Fleets | IMP Fleets | IGC ESI | IMP ESI | PVE | Mining | zKill

## [0.1.0] — 2026-01

### Added
- Initial release: basic monthly report with AFAT and IMP CSV integration
