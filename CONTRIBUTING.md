# Contributing to PlainLabs

The easiest and most valuable way to help: **add a knowledge pack** for a lab test we
don't cover yet. It takes about 10 minutes and no Python.

## Add a test pack

Create `packs/<test_id>.yaml`:

```yaml
id: ferritin                 # unique, snake_case
name: Ferritin               # human-readable
panel: vitamins              # cbc | diabetes | lipid | thyroid | liver | kidney | electrolytes | vitamins
aliases: [ferritin, serum ferritin, s. ferritin]   # lowercase, how reports name it
unit: ng/mL
fallback_ranges:             # must include 'normal'; optional 'borderline', 'abnormal'
  abnormal: [0.0, 11.9]      # for tests where LOW is the concern, abnormal sits below normal
  normal: [12.0, 300.0]
critical_below: 5.0          # optional — value below this → urgent hard-stop
# critical_above: 1000.0     # optional
explanation: >
  One or two calm, factual sentences about what this test measures and what
  high/low means. No diagnosis, no treatment advice.
sources:
  - https://medlineplus.gov/lab-tests/...   # a trusted, citable source
```

Rules the loader enforces (a bad pack fails at load, never silently at answer time):
- every `id` and every `alias` must be unique across all packs
- `fallback_ranges` must include `normal`; each range is `[low, high]` with `low <= high`
- ranges use the units of real-world adult reports; the report's own printed range is
  preferred at runtime, so packs are the fallback

Validate locally:

```bash
uv run python -c "from plainlabs.packs import load_packs; print(len(load_packs()), 'packs OK')"
uv run pytest
```

## Other good contributions

- **Golden reports** — add a realistic (synthetic, no real patient data) report under
  `evals/golden/` to widen test coverage.
- **Translations** — packs reserve a `translations:` field for local-language explanations.
- **Bug fixes / roadmap items** — see the roadmap in the [README](README.md) and
  [docs/PRD.md](docs/PRD.md).

## Ground rules

- Never commit real patient data.
- Explanations must stay non-diagnostic (literacy, not diagnosis).
- Cite a trusted medical source for every reference range.
