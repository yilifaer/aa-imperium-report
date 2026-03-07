# aa-imperium-report

**All-in-One Monthly Alliance Report** for [Alliance Auth](https://allianceauth.readthedocs.io/) — Imperium Edition

A Django plugin that aggregates monthly alliance activity data into a single report:
fleet attendance (AFAT + IMP CSV), ESI compliance (IGC + IMP), mining, PVE bounties, and zKillboard stats — with three permission tiers for Alliance Leaders, Corp CEOs, and regular members.

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

| Plugin | PyPI / GitHub | Purpose |
|--------|--------------|---------|
| allianceauth-afat | [PyPI](https://pypi.org/project/allianceauth-afat/) | IGC fleet attendance |
| aa-corpstats-two | [GitHub](https://github.com/pvyParts/aa-corpstats-two) | Member count + ESI status |
| allianceauth-corptools | [GitHub](https://github.com/Solar-Punk-Ltd/allianceauth-corptools) | PVE bounty data |
| aa-miningtaxes | [GitHub](https://github.com/pvyParts/aa-miningtaxes) | Mining ISK data |

All of the above are **optional** — the plugin gracefully skips any that are not installed. IMP attendance and IMP ESI report are uploaded manually.

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
| `aa_imperium_report.basic_access` | All alliance members |
| `aa_imperium_report.corp_access` | Corp CEOs / Co-CEOs |
| `aa_imperium_report.alliance_access` | Alliance leadership |
| `aa_imperium_report.upload_imp_data` | Alliance leadership / admins |

### 6. (Optional) Celery schedule

To enable daily snapshots, add to your `local.py`:

```python
from celery.schedules import crontab

CELERYBEAT_SCHEDULE["aa_imperium_report.daily_snapshot"] = {
    "task":     "aa_imperium_report.tasks.daily_snapshot",
    "schedule": crontab(hour=11, minute=5),  # ~10 min after EVE downtime
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
git clone https://github.com/YOUR_USERNAME/aa-imperium-report.git
cd aa-imperium-report
pip install -e ".[dev]"
```

---

## License

MIT — free to use, modify, and distribute. Credit appreciated but not required.

---

## Credits

Developed by **YiliFaer** for the **Invidia Gloriae Comes (IGC)** alliance.  
Built on [Alliance Auth](https://allianceauth.readthedocs.io/) by the AA community.
