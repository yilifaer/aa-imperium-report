# aa-imperium-report

**All-in-One Monthly Alliance Report** for [Alliance Auth](https://allianceauth.readthedocs.io/) — Imperium Edition

A Django plugin that aggregates monthly alliance activity data into a single report:
fleet attendance (AFAT + IMP CSV), ESI compliance (IGC + IMP), mining, PVE bounties, and zKillboard stats — with three permission tiers for Alliance Leaders, Corp CEOs, and regular members.

---

## Requirements

| Requirement | Minimum version | Notes |
|-------------|----------------|-------|
| Python | 3.8 | |
| Alliance Auth | 4.0 | Tested on 4.12 |
| Django | 4.0 | Included with AA |

---

## Features

- **Alliance Leader view** — full cross-corp table with all metrics, IMP ESI compliance summary, finalize/rebuild controls
- **Corp CEO view** — own corp ESI status card, member attendance breakdown, no other corps' data exposed
- **Member view** — own character attendance numbers only
- **Manual data upload** — IMP Attendance CSV and IMP ESI compliance report text
- **Auto-aggregation** from installed AA plugins: AFAT, corpstats-two, corptools, miningtaxes
- **Celery daily snapshot** for lightweight trend tracking
- **JSON API** endpoint for external tooling

---

## Compatible Plugins

All integrations are **optional** — any plugin that is not installed is skipped gracefully at runtime. Only install what your server already has.

| Plugin | Tested version | PyPI / GitHub | Data provided |
|--------|---------------|--------------|---------------|
| allianceauth-afat | >= 2.0 | [PyPI](https://pypi.org/project/allianceauth-afat/) | IGC fleet attendance (STR / PCT / Job) |
| aa-corpstats-two | >= 1.0 | [GitHub](https://github.com/pvyParts/aa-corpstats-two) | Member count + IGC ESI status |
| allianceauth-corptools | >= 2.15 | [GitHub](https://github.com/Solar-Punk-Ltd/allianceauth-corptools) | PVE bounty ISK |
| aa-miningtaxes | >= 1.0 | [GitHub](https://github.com/pvyParts/aa-miningtaxes) | Mining ISK + tax |

> **Note:** IMP attendance and IMP ESI report are uploaded manually via the UI — no extra plugin required for those.

---

## Installation

### 1. Install the package

```bash
pip install aa-imperium-report
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/yilifaer/aa-imperium-report.git
```

### 2. Add to INSTALLED_APPS

In your Alliance Auth `local.py`:

```python
INSTALLED_APPS += [
    "aa_imperium_report",
]
```

### 3. Add URL

In your main `urls.py`:

```python
from django.urls import path, include

urlpatterns += [
    path("imperium-report/", include("aa_imperium_report.urls", namespace="aa_imperium_report")),
]
```

### 4. Run migrations

```bash
python manage.py migrate aa_imperium_report
```

### 5. Assign permissions

In the AA Admin panel, assign the following permissions to the appropriate groups:

| Permission | Who gets it |
|-----------|------------|
| `aa_imperium_report.basic_access` | All alliance members (State group) |
| `aa_imperium_report.corp_access` | Corp CEOs / Co-CEOs |
| `aa_imperium_report.alliance_access` | Leadership group |
| `aa_imperium_report.upload_imp_data` | Leadership group |

### 6. (Optional) Celery schedule

To enable daily snapshots, add to your `local.py`:

```python
from celery.schedules import crontab

CELERYBEAT_SCHEDULE["aa_imperium_report.daily_snapshot"] = {
    "task":     "aa_imperium_report.tasks.daily_snapshot",
    "schedule": crontab(hour=11, minute=5),   # ~10 min after EVE downtime
}
```

---

## Usage

### Monthly workflow

1. Navigate to **Imperium Report** in the AA sidebar
2. Click **Upload IMP Attendance** → upload the monthly IMP fleet CSV
3. Click **Upload IMP ESI** → paste the monthly IMP ESI compliance report text
4. Click **Rebuild** to re-aggregate all data
5. Click **Finalize** to lock the report

### IMP ESI report format

The ESI compliance text should have one corporation per line:

```
[PASS] Example Corp (0 unregistered)
[FAIL] Bad Corp (3 unregistered: Pilot A, Pilot B, Pilot C)
[NO TOKEN] Missing Corp
```

### IMP Attendance CSV format

The CSV must include an `Account` column (character name) and the following attendance columns:

| Column | Category |
|--------|---------|
| `STRATEGIC` | IMP Strategic |
| `SIG/SQUAD Strategic` | IMP Strategic |
| `PEACETIME` | IMP Peacetime |
| `SIG/SQUAD` | IMP Peacetime |
| `Beehive` | IMP Peacetime |

---

## Permission Tiers

### Alliance Leader (`alliance_access`)
- Full IMP ESI compliance summary (all corps)
- Complete cross-corp data table
- All member attendance detail (collapsible)
- Upload / Rebuild / Finalize controls

### Corp CEO (`corp_access`)
- Own corp IMP ESI status card (PASS/FAIL/NO TOKEN + unregistered pilot list)
- Own corp monthly stats summary card
- Own corp member attendance table
- No other corps' data, no admin buttons

### Member (`basic_access`)
- Own character attendance numbers only (IGC STR/PCT, IMP STR/PCT, total)

---

## Development / Local Testing

```bash
git clone https://github.com/yilifaer/aa-imperium-report.git
cd aa-imperium-report
pip install -e ".[dev]"
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT — free to use, modify, and distribute. Credit appreciated but not required.

---

## Credits

Developed by **YiliFaer** for the **Invidia Gloriae Comes (IGC)** alliance.
Built on [Alliance Auth](https://allianceauth.readthedocs.io/) by the AA community.
