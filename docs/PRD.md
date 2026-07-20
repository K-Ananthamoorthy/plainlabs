# PlainLabs — PRD

*Private, agentic lab-report explainer that runs on a ~2B on-device model.*
Name: **PlainLabs**. Status: draft v2 — 20 Jul 2026.

---

## 1. Problem

A person gets a blood-test report: `HbA1c 6.8 · TSH 5.4 · K+ 6.9`. They don't know
what's normal, what's worrying, or what to do next. They panic-Google, or wait days
for a doctor appointment for what is often "everything is fine."

And the obvious fix — paste it into ChatGPT — fails twice:
- **Privacy:** it's health data. Many people won't (and shouldn't have to) send it to a cloud LLM.
- **Access:** rural clinics and low-income users need it free and offline.

## 2. Solution

Upload a lab report (PDF/photo) → get a plain-language report card:

- each value explained in simple words, grounded in a curated knowledge pack
- status per value: normal / borderline / abnormal / **urgent — see a doctor now**
- an "ask your doctor about these" shortlist
- runs **fully local on a 3B model** (Ollama); escalates *only* hard cases to a big model
- never diagnoses; always defers to a doctor

**One-line pitch:** health *literacy*, not diagnosis — engineered so it can't overstep.

## 3. Why now / why us (the thesis)

NVIDIA's position paper ([arXiv:2506.02153](https://arxiv.org/abs/2506.02153)) argues
SLMs are "sufficiently powerful, inherently more suitable, and necessarily more
economical" for most agent nodes, with 10–30× cost advantage; production stacks pair
an SLM with confidence-gated fallback to a big model. PlainLabs is that thesis applied
to a problem where local-first isn't a preference but a requirement (health data).

## 4. Prior art & differentiation

| Project | What it is | Gap we fill |
|---|---|---|
| GPT-wrapper analyzers (several on GitHub) | report → cloud LLM → freeform answer | privacy; no safety layer; hallucinated ranges |
| [get-based](https://github.com/elkimek/get-based) | local-first bloodwork *dashboard*, 287+ biomarkers | tracking-focused; no agentic explain flow, no guardrail engineering, no SLM cascade |
| RAG-LLM-Medical-Reports etc. | RAG over reports | cloud models; no severity gating |

**Differentiators:** (1) deterministic safety core — the model never decides what's
dangerous; (2) SLM-first heterogeneous cascade; (3) community knowledge packs (YAML);
(4) eval harness + tracing from day one.

## 5. Users

1. **Primary:** anyone holding their own lab report (India-first: printed reports with
   reference ranges included).
2. **Secondary:** caregivers reading reports for parents/children.
3. **Contributor:** open-source devs + medically-literate reviewers adding packs/translations.

## 6. Core design rule (non-negotiable)

> **The model only does language. Code does medicine.**
> Every medical judgment — what's the range, is this abnormal, is this dangerous —
> is deterministic code over curated data. SLM calls are narrow (parse, normalize,
> explain, decide-next-step) and each is validated + confidence-gated.

## 7. Scope

### v1 (2-day build)
- PDF + image upload; text via pypdf, OCR via tesseract
- Parse values → normalize names → range check → severity gate
- **Report-printed reference ranges preferred** (labs vary); pack ranges as fallback;
  conflict between the two → cautious path (borderline + doctor note)
- **Tiered compatibility — works on any routine report, refuses the serious ones:**
  - **Tier 1 — curated packs (~35 tests), the common panels:**
    - *CBC full:* Hb, RBC, HCT, MCV, MCH, MCHC, WBC + differential (neutrophils,
      lymphocytes, monocytes, eosinophils, basophils), platelets, ESR
    - *Diabetes:* fasting/PP/random glucose, HbA1c
    - *Lipid profile:* total cholesterol, LDL, HDL, triglycerides, VLDL
    - *Thyroid:* TSH, T3, T4, free T3, free T4
    - *Liver (LFT):* bilirubin (total/direct), SGPT/ALT, SGOT/AST, ALP, albumin, total protein
    - *Kidney (KFT):* creatinine, urea, BUN, uric acid
    - *Electrolytes:* sodium, potassium, chloride, calcium
    - *Vitamins & iron:* vitamin D, vitamin B12, ferritin, iron, TIBC
    - *Inflammation:* CRP
  - **Tier 2 — any other numeric test (the long tail):** agentic loop — decide →
    web_search (allowlisted medical sources) → extract range → self-check →
    explain or escalate. Report-printed range still preferred. This tier is what
    makes PlainLabs compatible with reports beyond its packs.
  - **Tier 3 — serious/specialized reports (explicit refusal, not wrong answers):**
    biopsy/histopathology, radiology narratives, genetic tests, tumor markers,
    culture & sensitivity — detected by a report-type classifier and answered with
    a canned "this report type needs your doctor to interpret" message.
    Refusing well is a feature, not a gap.
- Confidence gate: self-consistency (2 runs agree?) + schema validation; low → escalate
  to big model (Groq/Gemini free tier, config-switchable, off = fully local mode)
- Guardrails: no-diagnosis phrasing filter, mandatory disclaimer, urgent hard-stop
  (canned text, model never writes it), refuse non-lab-report uploads
- Eval harness: golden set of ~8 synthetic reports → extraction accuracy, range
  correctness (deterministic), explanation groundedness (LLM judge)
- Tracing: LangSmith (or Langfuse) on every run
- UI: Streamlit; CLI: `python -m plainlabs report.pdf`

### Non-goals v1
- No diagnosis, treatment, or medication advice — ever (not just v1)
- No trend tracking / history dashboards (get-based owns that)
- No translations yet (v1.1 — pack field already reserved)
- No FHIR/LOINC integration (packs carry optional `loinc:` field for later)
- No fine-tuning (cascade first; LoRA on parse_values is a documented future path)
- No mobile app (laptop/desktop only — dropped from scope 20 Jul 2026)
- No multimodal image-understanding of reports (model supports it; extraction stays
  deterministic for auditability — revisit behind an experiment flag)

## 8. Architecture

LangGraph `StateGraph`; SQLite checkpointer; explicit conditional edges.

```
extract_text → parse_values → [per value] normalize → lookup_range → severity
                                                                        │
                    ┌──────────────────── critical ── urgent_stop (canned)
                    ├──────────────────── known ───── explain → grade ──┬─ confident → report_card
                    │                                          ▲        └─ unsure → escalate/search ─┐
                    └─ unknown ── decide (SLM) ─┬─ SEARCH → web_search → extract_range ──────────────┘
                                                ├─ ESCALATE → big model
                                                └─ ASK → user
report_card → guardrail_filter → assemble → done
```

**SLM skills (gemma4:e2b-it-qat via Ollama — 2.3B effective, QAT 4-bit, ~3GB RAM,
native function calling; llama.cpp `llama-server` with unsloth UD-Q4_K_XL GGUF as
documented alternative; model is a config value, not an architecture decision):**
parse_values, normalize_name, decide, extract_range, explain_value, grade.
**Deterministic tools:** extract_text (pypdf/tesseract), lookup_range, severity,
guardrail_filter, source allowlist.
**Escalation model:** Groq or Gemini free tier (config), used per-node, never wholesale.

### Knowledge pack format (the contribution surface)

```yaml
# packs/hba1c.yaml
id: hba1c
aliases: [hba1c, glycated hemoglobin, glycosylated hb, a1c]
unit: "%"
fallback_ranges:
  normal: [4.0, 5.6]
  borderline: [5.7, 6.4]
  abnormal: [6.5, 15.0]
critical_above: 15.0        # → urgent hard-stop
explanation: >
  HbA1c reflects average blood sugar over ~3 months. …
sources: [https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/]
# reserved: translations: {kn: …, hi: …}, loinc: 4548-4
```

## 9. Safety requirements (the hero feature)

1. Severity thresholds and range comparisons: **code only**. Model output cannot
   change a status.
2. Critical values: model is **not called**; canned urgent message.
3. Every explanation grounded in pack text or allowlisted source; groundedness is
   an eval metric, not a hope.
4. No-diagnosis filter (regex + judge): "you have X" → rewritten or blocked.
5. Web results never override pack/report ranges; conflicts → cautious path.
6. Non-report input → polite refusal. Tier-3 report types (pathology narratives,
   tumor markers, genetic) → canned defer-to-doctor message, model not consulted.
7. Disclaimer on every output.

## 10. Evals (definition of done for v1)

| Metric | Target | Method |
|---|---|---|
| Value extraction accuracy | ≥95% on golden set | deterministic compare |
| Range/severity correctness | 100% (it's code) | unit tests |
| Explanation groundedness | ≥90% judged grounded | LLM judge |
| % handled locally | report the number | trace counts |
| No-diagnosis violations | 0 on golden set | filter + judge |

## 11. Open-source strategy

- License: MIT. Repo: `plainlabs` under K-Ananthamoorthy.
- Contribution surface: **packs** (new test YAML), **translations** (pack field),
  **golden reports** (evals), later: skills. Core stays small.
- `CONTRIBUTING.md`: "add a test pack in 10 minutes"; CI validates pack schema +
  runs evals on PRs.
- Good-first-issues seeded at launch: 5 missing packs, 2 languages, 3 golden reports.

## 12. Build plan (2 days)

**Day 1 — the trustworthy spine (no LLM until afternoon)**
1. Repo scaffold: uv, package layout, pack schema + loader + validation
2. ~35 Tier-1 packs written (panel by panel: CBC → diabetes → lipids → thyroid →
   LFT → KFT → electrolytes → vitamins/iron → CRP); `lookup_range` + `severity` +
   Tier-3 report-type detector + unit tests (100% correctness bar)
3. `extract_text` (pypdf + tesseract fallback)
4. First SLM skills: `parse_values`, `normalize_name` + validators
5. Wire linear graph: upload → report card for known tests, CLI output

**Day 2 — agency, safety, proof**
6. `decide` + `web_search` (allowlist) + `extract_range` + reflection loop
7. Confidence gate + escalation (Groq/Gemini config; `--local-only` flag)
8. Guardrail filter + urgent hard-stop + refusal path
9. Eval harness + golden set; run, record numbers in README
10. LangSmith tracing; Streamlit UI; README (architecture diagram, thesis, numbers);
    CONTRIBUTING.md + seeded issues

**Definition of done:** a stranger can `uv sync`, drop a report PDF, and get a safe
report card fully offline; evals green; traces visible; contribution path documented.

## 13. Risks

| Risk | Mitigation |
|---|---|
| OCR quality on phone photos | v1 demo leads with PDF; OCR marked experimental |
| 3B parse errors on odd layouts | schema validation → retry → escalate; measured in evals |
| Medical liability optics | literacy-not-diagnosis framing, disclaimers, no-diagnosis filter, curated sources |
| Range variance across labs | prefer report-printed ranges (design decision #1) |
| 8GB M1 memory | gemma4 E2B QAT ≈3GB resident; one model at a time; escalation is API not local |

## 14. Decisions (locked 20 Jul 2026)

1. Name: **PlainLabs** — labs in plain language.
2. SLM: **medgemma:4b** via Ollama — Google's medically-tuned Gemma 3, trained on
   lab-report extraction (HAI-DEF license; used for language only, not medical decisions).
   Model is a config value; any Ollama model works.
3. Escalation provider: **Groq** (fast, free tier), config-switchable; `--local-only` supported.
4. Tracing: **LangSmith** (hosted free tier).
5. Laptop/desktop only. Mobile is explicitly out of scope.
