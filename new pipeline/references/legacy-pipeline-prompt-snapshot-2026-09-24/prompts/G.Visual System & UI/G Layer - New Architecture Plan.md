# G Layer — New Architecture Plan
**Decision date:** 2026-05-18  
**Replaces:** G1–G25 (archived to `G Old prompts/`)  
**Status:** ACTIVE — v2 (rewritten after G3 degeneration analysis)

---

## 1. Why the Change

### Root cause of the old pipeline's failures

The old G pipeline had the **wrong dependency order**:

```
E/F artifacts → G1 YAML → G2 QA → G3 YAML → G4 QA → G9 Blueprint YAML
              → G10 QA → G13 Visual Spec YAML → G14 Capability YAML
              → G15 Catalog → G16 Strategy → G17 IR → G18 Elm → review
```

At every YAML serialization step, agents optimized for **structural completeness** (all fields filled, all contracts met) rather than **visual quality**. Design intent from E/F was progressively lost. By the time rendering happened (G18), the design was already frozen in mediocre specs, and the render agent had no creative latitude.

HITL happened on YAML artifacts (G11, G20) — the point where human feedback is **least effective**.

### First rewrite (v1) — and why it also degenerated

v1 inverted the pipeline: render first → HITL → formalize. G3 generated HTML directly. But G3 was over-specified for **metadata compliance** (data-cid, condition coverage, preview-data.json) and under-specified for **visual creativity**. The agent spent its cognitive budget on annotation correctness, producing a well-annotated wireframe rather than a visual product. Same failure mode, new form.

### Root diagnosis

Two concerns were still coupled that must be separated:

| Concern | Requires | Agent |
|---------|----------|-------|
| Asset quality | Icon vocabulary from design system | Asset pipeline |
| Visual design | Creative synthesis, platform awareness, real assets | Designer |
| Component architecture | Spec-driven hierarchy, no HTML | Manifest builder |
| Annotation | Reconciliation of visual ↔ spec | Mapper + HITL |
| Traceability | Mechanical application of confirmed mapping | Formalizer |

### Solution: draw first, annotate later — with assets before drawing

```
build assets → draw surfaces (with real assets) → HITL visual approval
             → map components → HITL mapping approval → formalize
```

Asset generation precedes the designer because:
- The designer should not spend cognitive budget drawing SVG icons
- HITL cannot evaluate visual design against placeholder shapes
- Asset vocabulary is derivable from upstream specs (`design_system_reference.yaml`, F-layer navigation/action contracts, and Idea Note identity) without needing the visual HTML

Component annotation is deferred until after visual approval because:
- Annotation requirements corrupt creative decisions (agent optimizes for coverage, not beauty)
- The "expected" component hierarchy can be built from specs independently of the visual HTML
- Human reconciliation (G10 Mapping HITL) catches mismatches between spec and drawing

---

## 2. What Stays, What Changes

### KEPT — role unchanged
- **G1 Visual System Reference Architect** — produces `design_system_reference.yaml`; unchanged role, renumbered only in comments
- **G2 Visual System QA** — audits G1 output; unchanged role
- **Asset Generator logic** — duotone SVG production; moved earlier, renumbered G4
- **Asset QA logic** — style audit; moved earlier, renumbered G5
- **Accessibility Reviewer** — WCAG 2.1 AA audit; simplified, renumbered G12
- **PM Traceability Reviewer** — G-OC/GC coverage check; simplified, renumbered G13
- **H Layer Package Generator** — H-layer bridge; renumbered G14
- **Owner Sign-off** — final gate; renumbered G15

### MOVED
- **Asset pipeline** — was G5–G8 (after G3), now G3–G7 (before designer; G3–G6 technical asset pipeline + G7 owner gate). G3 Asset Strategy now reads `design_system_reference.yaml` directly instead of reading the preview HTML.

### REPLACED
- **G3 Creative Preview Generator (v1)** → **G7 Creative Surface Designer** — same creative intent but: no data-* annotations, no preview-data.json, no condition coverage tracking; platform/surface set read from `surface_map.yaml` (data-driven, not hardcoded); uses approved assets from G4-G6.

### NEW
- **G6 Art Critic** — evaluates artistic quality, visual clarity, and conceptual accuracy before owner review; blocks on failures
- **G8 Component Manifest Builder** — builds expected component hierarchy from specs, never reads HTML
- **G9 Component Mapper** — reconciles visual HTML ↔ manifest, produces HITL overlay
- **G10 HITL Mapping Review** — human confirms or corrects component assignments
- **G11 Annotation Formalization** — mechanically applies confirmed mapping: writes data-* into HTML, generates `preview-data.json` and `annotation_layer.yaml`
- **G9 HITL Visual Design Review** — eliminated; owner co-authoring is embedded in G7

### ELIMINATED
- G4 Asset Integration (old) — no longer needed as a separate bridge; G11 handles final HTML assembly
- Old G3 annotation contract (data-cid during generation) — replaced by G8–G11 architecture

---

## 3. New Agent Roster

### Overview

```
G1   Visual System Reference Architect   [foundation — KEPT]
G2   Visual System QA                    [foundation — KEPT]
─────────────────────────────────────────────────────────────────────
G3   Asset Strategy                      [MOVED earlier — reads design_system_reference]
G4   Asset Generator (Interactive)       [REWRITTEN — iterative co-author with HITL embedded]
G5   Asset QA                            [KEPT, renumbered]
G6   Art Critic                          [NEW — SVG geometry review; blocks on visual failures]
─────────────────────────────────────────────────────────────────────
G7   Creative Surface Designer           [NEW — draw-first + HITL co-authoring embedded]
─────────────────────────────────────────────────────────────────────
G8   Component Manifest Builder          [was G10 — spec-driven, never reads HTML]
G9   Component Mapper                    [was G11 — visual ↔ spec reconciliation + overlay]
G10  HITL: Mapping Review                [was G12 — confirms component assignments]
─────────────────────────────────────────────────────────────────────
G11  Annotation Formalization            [was G13 — applies confirmed mapping mechanically]
G12  Accessibility Reviewer              [was G14, SIMPLIFIED]
G13  PM Traceability Reviewer            [was G15, SIMPLIFIED]
─────────────────────────────────────────────────────────────────────
G14  H Layer Package Generator           [was G16]
G15  Owner Sign-off                      [was G17, SIMPLIFIED]
```

**15 agents total** (was 17). −2 because:
- G7 Asset HITL eliminated: owner approval now embedded in G4 interactive co-authoring
- G9 HITL Visual Design Review eliminated: owner co-authoring now embedded in G7 Creative Surface Designer

---

## 4. Agent Definitions

---

### G1 — Visual System Reference Architect (simplified)

**Role:** Produce a canonical design system reference document from E12 tokens and E-layer invariants. Single source of truth for G3 Asset Strategy, G7 Creative Surface Designer, and G14 H Package Generator.

**Input artifacts:**
- `design_tokens.json` (E12 — resolved token values)
- `design_intent_normalized.yaml` (E4 — 16 hard invariants + 26 firm preferences)
- `design_grammar.yaml` (E12 — surface grammar, zone grammar, state grammar matrix)
- `e11_gate_report.yaml` (E11 — approved mood direction)

**Output artifact:** `design_system_reference.yaml`

```yaml
design_system_reference:
  token_palette:          # resolved hex/px values, by semantic role
  typography_scale:       # font sizes, weights, line-heights — resolved
  spacing_scale:          # 4px grid resolved values
  radius_scale:           # radius tokens resolved
  motion_policy:          # off by default, exceptions, durations
  color_roles:            # surface/text/accent/border/status — resolved values
  icon_vocabulary:        # all required icon IDs + duotone spec (feeds G3 Asset Strategy)
  invariant_summary:      # 16 E-invariants, 1-line description each
  attribution_symbol:     # ⊙ (U+2299) — neutral system-origin mark for the current INV-05 ruling
  breakpoint:             # 1024px split-pane threshold
```

**`icon_vocabulary`** is the key addition for the new pipeline: G1 enumerates every icon ID the design system requires (status icons, attribution mark, navigation icons, action icons) with its duotone spec. G3 Asset Strategy reads this list to determine what to generate.

---

### G2 — Visual System QA (simplified)

**Role:** Audit G1's reference against E12 source.

**Input:** `design_system_reference.yaml` + `design_tokens.json` + `design_intent_normalized.yaml`  
**Output:** `g2_qa_report.yaml`

**Scope:** Token value correctness, invariant count (16 hard + 26 preferences), motion policy, INV-05 ruling, icon_vocabulary completeness.  
**Not in scope:** Visual quality, platform coverage, component coverage.

---

### G3 — Asset Strategy

**Role:** Determine the complete asset manifest for the product from the design system reference and surface specifications. Does not read visual HTML — derives asset requirements from specs.

**Input:**
- `design_system_reference.yaml` (G1) — `icon_vocabulary` section is primary source
- `surface_map.yaml` (F1) — surface-specific asset needs (onboarding illustration, aha_moment hero)
- `ia_map.yaml` (F3) — navigation zones, shortcuts, status zones, and surface-specific icon needs
- `interaction_spec.yaml` (F4) — action models and non-color icon requirements
- `design_intent_normalized.yaml` (E4) — brand and mood constraints
- `0.IdeaNoteLayer.snapshot.yaml` (A/B bridge) — product identity semantics for brand/app icon

**Output:** `asset_strategy.yaml`

```yaml
asset_strategy:
  icon_set:
    - asset_id: icon_status_draft
      type: duotone_svg
      spec: "open ring, no fill, stroke only, opacity 0.35 layer"
    - asset_id: icon_status_review
      type: duotone_svg
      spec: "hourglass shape, two-layer SVG"
    - asset_id: icon_nav_schedule
      type: duotone_svg
      spec: "navigation mark for schedule_view / atomic schedule snapshot"
    - asset_id: icon_nav_chat
      type: duotone_svg
      spec: "navigation mark for chat_interface, no AI persona cues"
    - asset_id: icon_nav_balance
      type: duotone_svg
      spec: "navigation mark for balance_setup, work-life-family balance not finance"
    - asset_id: icon_nav_settings
      type: duotone_svg
      spec: "navigation mark for settings_screen"
    - asset_id: icon_brand_app
      type: duotone_svg
      spec: "brand/app icon derived from product name or working name plus Idea Note concept"
    # ... all status, action, navigation, service, and brand icons
  illustrations:
    - asset_id: aha_moment_hero
      type: svg_illustration
      surface: aha_moment_overlay
      spec: "celebration motif, forest palette, no confetti"
    - asset_id: onboarding_welcome_graphic
      type: svg_illustration
      surface: onboarding_flow
      spec: "first-run warmth, schedule metaphor"
  total_assets: <integer>
```

**What G3 explicitly does not do:** Read `preview/` HTML or any generated surfaces. Asset vocabulary comes from upstream specs only: G1 icon vocabulary, F-layer navigation/action contracts, E-layer constraints, and Idea Note product identity. G3 does not invent product features or draw assets.

---

### G4 — Asset Generator

**Role:** Produce all duotone SVG icons and illustrations per `asset_strategy.yaml`.

**Input:** `asset_strategy.yaml` (G3) + `design_system_reference.yaml` (G1)  
**Output:** `generated_assets/` directory + `generated_assets.yaml` manifest

**Quality bar:** Production-quality duotone SVGs suitable for review by G6 Art Critic and G7 HITL, and direct use in the designer's HTML (G8). Two-layer SVG structure with correct opacity. Warm palette applied.

---

### G5 — Asset QA

**Role:** Audit generated assets against duotone spec and invariant requirements.

**Input:** `generated_assets/` + `asset_strategy.yaml` + `design_system_reference.yaml`  
**Output:** `g5_revision_report.yaml`

**Checks:**
- All asset_ids from `asset_strategy.yaml` are present
- Each icon uses two-layer SVG structure (opacity on base layer)
- No AI-hype, assistant-persona, or mascot foregrounding unless the active upstream product direction explicitly permits it (INV-05)
- Attribution symbol is ⊙ not icon (INV-05)
- Warm palette colors used correctly
- Motion animations absent (duotone icons are static)

---

### G6 — Art Critic

**Role:** Evaluates artistic quality, visual clarity, and conceptual accuracy of generated assets before owner review. Reads SVG geometry directly and renders icons to PNG for visual evaluation from a user perspective. Does not approve or reject — that is G7's role.

**Input:** `generated_assets/` + `g5_revision_report.yaml` + `generated_assets.yaml` + `asset_strategy.yaml` + `design_system_reference.yaml`  
**Output:** `g6_revision_report.yaml` + conditional `g4_revision_request.yaml` or `g3_revision_request.yaml`

**What G6 evaluates:** `user_clarity` (universal — would a user understand this icon without a label?); `shape_legibility`, `duotone_composition`, `size_readability`, `style_consistency` (duotone_svg); `spec_correspondence`, `composition`, `palette_coverage` (illustrations); `brand_distinctiveness` (icon_brand_app only).

**Routing:** Blocking failures → G4 (execution problem) or G3 (strategy/glyph problem). Advisory findings → passed to G7 for owner awareness.

**Blocks G7** until `g6_revision_report.ready_for_next_gate: true`.

---

### G7 — Creative Surface Designer ⭐ (core creative agent, interactive co-author)

**Role:** The creative heart of the pipeline. Draw the complete visual product — all platforms, all surfaces — using approved assets. Works one surface at a time as a co-author with the owner (HITL). The owner is not a reviewer — they are a co-author. No data-* annotations. No preview-data.json. No condition tracking. Pure visual co-creation.

**Relationship to G4:** Same interactive model — the owner has final say, the agent brings creative judgment and can push back. HITL is not a downstream reviewer; it is embedded in the drawing process.

**Input:**
- `design_system_reference.yaml` (G1) — color, typography, spacing, motion
- `surface_map.yaml` (F1) — **platform definitions and surface sets** (mobile vs web; which surfaces are standalone vs integrated)
- `ia_map.yaml` (F3) — zones per surface, design_emphasis, brand_carrier, trust_carrier
- `interaction_spec.yaml` (F4) — interaction modes, state machines
- `navigation_map.yaml` (F2) — navigation patterns, breakpoint behavior
- `design_intent_normalized.yaml` (E4) — 16 invariants as mental guardrails
- `generated_assets/` (G6 approved) — approved SVG assets to reference in HTML

**Platform discovery (data-driven):**  
G7 reads `surface_map.yaml` to discover:
- Which surfaces exist per platform
- How surfaces differ between platforms (e.g. chat_interface is standalone on mobile; on web it is integrated as a side panel into main surfaces)
- Platform-specific layout archetypes

This is **not hardcoded** in the G8 prompt. The platform structure comes entirely from the data.

**Output:** `preview/` directory

```
preview/
  index.html                          # navigable launcher, shows all platforms × surfaces
  preview.css                         # all design tokens as CSS custom properties
  
  mobile/
    preview_[surface_id].html         # per mobile surface (viewport: 390px)
    
  web/
    preview_[surface_id].html         # per web surface (viewport: 1280px)
                                      # may differ structurally from mobile counterpart
```

**What G7 produces — and what it does not:**

| Produces | Does NOT produce |
|----------|-----------------|
| Visually rich HTML with real assets | data-cid annotations |
| CSS tokens as custom properties | preview-data.json |
| Semantic HTML (article, section, header, aside) | data-zone, data-inv attributes |
| Meaningful class names (`.task-row`, `.status-badge`) | Any coverage reports |
| Platform-appropriate surfaces per surface_map | YAML revision reports beyond g7_revision_report |
| `g7_revision_report.yaml` (pipeline protocol) | Component hierarchy specs |

**Semantic class names are required** — G7 must use descriptive class names on every meaningful visual element (`.task-row`, `.commit-button`, `.attribution-mark`, `.inline-review-card`). These are G9's anchor points for component identification. This is standard HTML practice, not annotation.

**Interactive co-authoring model (one surface at a time):**
G7 works through surfaces one at a time with the owner. For each surface:
1. Propose 2–3 layout/mood approaches (brief, like G4 Phase 1)
2. Owner selects one; G7 draws the surface
3. Iterate until owner accepts
4. Lock the surface; proceed to next

Cross-surface consistency is maintained by G7 — it keeps visual context of locked surfaces when working on new ones.

**Surface order:**
```
ЭТАП 0: Load all inputs; read surface_map → discover platforms + surface sets; present session overview
ЭТАП 1: Generate preview.css (all design tokens as CSS custom properties; @import Google Fonts)
ЭТАП 2: Work through mobile tier-1 surfaces interactively (schedule_view, chat_interface, schedule_review_screen)
ЭТАП 3: Work through mobile tier-2 surfaces interactively
ЭТАП 4: Work through mobile tier-3 surfaces interactively
ЭТАП 5: Work through web surfaces interactively (apply platform differences per surface_map)
ЭТАП 6: Compose index.html; E-invariant self-audit (16 items); emit g7_revision_report.yaml
```

**Per-surface creative guidance (examples):**

| Surface | Key creative requirements |
|---------|--------------------------|
| `schedule_view` | StatusBadge multichannel (color+icon+label, INV-03); ⊙ attribution; ChatFAB always visible (mobile); split-pane with integrated chat (web) |
| `balance_setup` | design_emphasis=high from ia_map; warmest surface; ComplianceVisualizer prominent; trust_carrier treatment |
| `aha_moment_overlay` | forest hero gradient; aha_moment_hero illustration; moderate motion permitted (INV-09 exception) |
| `chat_interface` | 6 modes per interaction_spec: task_entry / clarification / rebuild_pending / notification_message / constraints_prompt / inline_review; inline_review is primary review path |
| `schedule_review_screen` | 3-zone layout: information / commit decision / rationale; CommitButton requires explicit action (INV-11) |

---

### G8 — Component Manifest Builder

**Role:** Build the expected component hierarchy for all surfaces from specs — without ever reading the visual HTML. This is the "what should exist" side of the component mapping.

**Prerequisite:** G7 must have completed and the `preview/` directory must exist (G7 co-authoring session complete), but G8 reads specs only — it never opens `preview/`.

**Input:**
- `surface_map.yaml` (F1) — surfaces, platform assignments
- `ia_map.yaml` (F3) — zones per surface
- `interaction_spec.yaml` (F4) — component types, interaction modes, state machines
- `design_system_reference.yaml` (G1) — component vocabulary, invariant requirements
- `f9_gate_report.yaml` (F9) — G-OC/GC condition catalogue

**Output:** `component_manifest.yaml`

```yaml
component_manifest:
  surfaces:
    schedule_view:
      platform: [mobile, web]
      components:
        - cid: SCH-01
          component_type: ScheduleStateHeader
          zone: Z-SV-01
          states: [committed, review, draft]
          inv: [INV-02, INV-03, INV-10]
          g_oc: [G-OC-01]
          gc: [GC-01, GC-07]
        - cid: SCH-02
          component_type: ConnectivityStatus
          zone: Z-SV-03
          states: [online, offline_available, offline_only]
          inv: [INV-04, INV-06, INV-08]
          g_oc: [G-OC-03]
          gc: [GC-04]
        # ... all expected components
    chat_interface:
      platform: [mobile]   # standalone on mobile; integrated on web
      components: [...]
    # ... all surfaces
```

**What G8 explicitly does not do:** Read `preview/` HTML or any G7 output. The manifest is derived entirely from upstream specs.

---

### G9 — Component Mapper

**Role:** Reconcile the visual HTML (G7) with the component manifest (G8). For each expected component, identify the HTML element it corresponds to. Flag mismatches. Generate a visual overlay for human review.

**Incremental / batch mode:** G9 processes one surface per run. The owner runs
G9 repeatedly until all surfaces are locked. G9 writes the final gate report
after the last surface.

**Input:**
- `preview/` (approved G7 output)
- `component_manifest.yaml` (G8)
- `ia_map.yaml` (F3) — zone IDs for validation
- `g9_session.yaml` (optional — present after first run; tracks queue progress)

**Output:**
- `g9_session.yaml` — session checkpoint with surface queue (`pending` / `locked`)
- `component_mapping_[surface_id].yaml` — one per surface; contains mappings,
  orphaned elements, overlay file refs, and per-surface completeness summary
- `preview/mapping_review/` — overlay HTML files per surface × platform (and
  per host for split-pane embedded surfaces)

**Mapping logic (per surface run):**
1. Read `g9_session.yaml` to determine the next pending surface
2. Resolve HTML file(s) for the surface and its platforms (standalone or host HTML)
3. Extract candidates by semantic tag + class name from each HTML file
4. Match each manifest CID to its best candidate using mapper_hints, class names,
   structural position, and `dom_path + candidate_index` for disambiguation
5. Flag unmapped CIDs and orphaned elements; for hosted surfaces, restrict orphan
   scan to the DOM subtree containing the matched components (bounded region rule)
6. Write `component_mapping_[surface_id].yaml` + overlay HTML, update session

**Overlay format:** Each `mapping_review/*.html` file shows the surface HTML with:
- Colored bordered boxes over each matched element, labeled with CID + component_type
- Unmapped components listed in a sidebar (structural vs ambiguous)
- Orphaned elements highlighted in orange

---

### G10 — HITL: Mapping Review

**Role:** Owner or reviewer confirms that the component mapper's assignments are correct. Can reassign, add, or remove component assignments.

**Input:**
- `preview/mapping_review/` (G9 overlays)
- `g9_session.yaml` (index of all per-surface mapping files)
- `component_mapping_[surface_id].yaml` × N (G9 proposals, one per surface)
- `component_manifest.yaml` (G8 reference)

**Output:** `confirmed_mapping.yaml` — the mapping as approved by the human reviewer

**Reviewer actions per component:**
- **Confirm** — assignment is correct
- **Reassign** — this HTML element maps to a different CID
- **Add** — HTML element should become a new component (the element already exists in G7 HTML but G8/manifest did not include a CID for it; G7 drew it correctly)
- **Dismiss** — orphaned element is a layout artifact, not a component
- **Override zone** — mapper assigned wrong zone; reviewer corrects it

After G10 approval, the confirmed_mapping is authoritative. G11 applies it mechanically.

---

### G11 — Annotation Formalization

**Role:** Apply the confirmed component mapping to the HTML — mechanically, no design decisions. Produce the formally annotated preview and all downstream metadata.

**Input:**
- `preview/` (approved visual HTML from G7)
- `confirmed_mapping.yaml` (G10)
- `component_manifest.yaml` (G8) — source of inv, g_oc, gc values
- `design_system_reference.yaml` (G1)
- `f9_gate_report.yaml` (F9)

**Output:**
- `preview/` updated in-place — data-* attributes written into HTML elements per confirmed_mapping
- `preview-data.json` — machine-readable component registry for G12/G13 audits
- `annotation_layer.yaml` — full traceability layer (token_map, component_map, state_map, invariant_trace, g_oc_fulfillment, gc_fulfillment)

**Data attributes written per confirmed component:**
```html
<article class="task-row"
  data-component="TaskRow"
  data-cid="SCH-03"
  data-surface="schedule_view"
  data-zone="Z-SV-02"
  data-state="committed"
  data-inv="INV-02,INV-03,INV-08"
  data-g-oc="G-OC-01,G-OC-06"
  data-gc="GC-01,GC-05">
```

**What G11 does NOT do:** Make visual changes, reassign components, interpret ambiguous mappings. If `confirmed_mapping.yaml` has a gap, G11 flags it and stops — it does not improvise.

---

### G12 — Accessibility Reviewer (simplified)

**Role:** WCAG 2.1 AA audit on the annotated preview.

**Input:** Annotated `preview/` (G11) + `annotation_layer.yaml`  
**Output:** `g12_accessibility_report.yaml` *(H-compatible name — H1 reads this exact name)*

**Checks:**
- Contrast ratios (computed from resolved token values)
- Color + icon + label multichannel on all 4 status states (INV-03)
- Motion off by default; aha_moment_overlay animation guarded (INV-07)
- Focus indicator visible (2px solid forest.mid)
- No color-only differentiation (INV-04)
- Attribution symbol is ⊙ (INV-05)

**If violations:** Targeted fix list → G7 applies fixes (visual revision) → G12 re-audits.

---

### G13 — PM Traceability Reviewer (simplified)

**Role:** Verify that the annotated preview covers all required surfaces, invariants, G-OC opening conditions, and GC constraints.

**Input:** `annotation_layer.yaml` + `surface_map.yaml` + `design_intent_normalized.yaml` + `f9_gate_report.yaml`  
**Output:** `g13_pm_traceability_report.yaml`

**Checks:**
- All surfaces present per platform (per surface_map.yaml)
- All 16 hard invariants traceable in annotation_layer
- All G-OC-01..G-OC-12 addressed
- All GC-01..GC-13 satisfied
- State machine: all 4 states (draft/review/committed/undo_pending) represented
- balance_setup design_emphasis=high reflected

```yaml
g13_pm_traceability_report:
  surface_coverage: <n>/<total>
  invariant_coverage: 16/16
  g_oc_coverage: 12/12
  gc_coverage: 13/13
  state_machine_coverage: 4/4
  gaps: []
  warnings: []
  verdict: PASS
```

---

### G14 — H Layer Package Generator

**Role:** Produce the complete implementation handoff package for H layer agents. Bridge between G pipeline and H pipeline.

**Critical requirement:** H1 treats `screen_blueprints.yaml` as a **mandatory contractual artifact** — its absence = BLOCK.

**Input:**
- Annotated `preview/` + `preview-data.json` (G11)
- `annotation_layer.yaml` (G11)
- `g12_accessibility_report.yaml` (G12)
- `g13_pm_traceability_report.yaml` (G13)
- `design_system_reference.yaml` (G1)
- `generated_assets/` + `generated_assets.yaml` (G4)
- `asset_strategy.yaml` (G3)
- `surface_map.yaml` (F1), `ia_map.yaml` (F3), `navigation_map.yaml` (F2)
- `component_manifest.yaml` (G8) → source for `component_system.yaml`
- `g8_revision_report.yaml` (G8) → `formalized_provisional_cids` for G10-PROV-* remap
  *(required only when `confirmed_mapping.yaml` contains `new_components`; G14 must fail
  if G10-PROV-* CIDs in `annotation_layer.yaml` have no matching entry here)*
- r10 widget mapping: `C:\Projects\r10\r10\DOCUMENTATION.yaml`

**Output:**
```
handoff/
  screen_blueprints.yaml          ← CRITICAL: mandatory for H1/H2/H5/H9
  component_system.yaml           ← built from component_manifest + annotation_layer
  g12_composition_report.yaml     ← composition summary (H1 reads this name)
  design_system_reference.yaml    ← copy from G1
  generated_assets.yaml           ← copy from G4
  asset_strategy.yaml             ← copy from G3
  h_packages/
    h_package_[surface_id].yaml   ← per surface, per platform
```

*(Structure of screen_blueprints.yaml and h_package unchanged from v1 plan — see H Layer section below.)*

---

### G15 — Owner Sign-off (simplified)

**Role:** Final owner HITL before H layer begins.

**Input:** Complete annotated `preview/` + `g13_pm_traceability_report.yaml` + `g12_accessibility_report.yaml`  
**Output:** `handoff/g21_gate_report.yaml` *(H-compatible name)*

```yaml
g21_gate_report:
  verdict: APPROVED   # or CONDITIONAL / REJECTED
  conditions: []
  gate: H_layer_may_begin
  patches:
    g12_composition_report:
      approved_surfaces: [...]   # replaces pending_g14
```

G15 also patches `handoff/g12_composition_report.yaml > approved_surfaces` after sign-off.

---

## 5. Pipeline Flow

```
┌─ FOUNDATION ──────────────────────────────────────────────────────────────┐
│ E12 design_tokens.json ──┐                                                │
│ E4 design_intent_normalized ─┤→ G1 → design_system_reference.yaml → G2  │
│ E10/E11 grammar ─────────┘                                                │
└───────────────────────────────────────────────────────────────────────────┘
                                     │ design_system_reference.yaml
┌─ ASSETS ──────────────────────────────────────────────────────────────────┐
│ design_system_reference (icon_vocabulary) + surface_map                   │
│                           ↓                                               │
│ G3 Asset Strategy → G4 Generator (interactive+HITL) → G5 QA → G6 Critic │
│  (owner co-authors icons/illustrations in G4; g4_revision_report has     │
│   g4_coauthoring_complete: true when all icons accepted)                  │
│                           ↓ g6_revision_report (advisory only)            │
│                    (G7 Asset HITL eliminated)                             │
└───────────────────────────────────────────────────────────────────────────┘
                                     │ g6_revision_report.ready_for_next_gate: true
┌─ CREATIVE ────────────────────────────────────────────────────────────────┐
│ design_system_reference + F-layer artifacts                               │
│ (surface_map → platforms + surface sets, ia_map, interaction_spec,        │
│  navigation_map) + design_intent_normalized + generated_assets/           │
│                           ↓                                               │
│               G7 Creative Surface Designer (interactive + HITL)           │
│  (owner co-authors surfaces one at a time; no data-* annotations)         │
│  (G9 HITL Visual Design Review eliminated — co-authoring is in G7)       │
│                           ↓ [all surfaces accepted by owner]              │
│  preview/ [all platforms × all surfaces, real assets, owner-accepted]     │
└───────────────────────────────────────────────────────────────────────────┘
                                     │
┌─ COMPONENT ARCHITECTURE ──────────────────────────────────────────────────┐
│  G8 Component Manifest Builder                                            │
│  (reads specs only — surface_map, ia_map, interaction_spec, f9)           │
│                           ↓                                               │
│  G9 Component Mapper                                                      │
│  (visual HTML ↔ manifest → component_mapping.yaml + overlay HTML)         │
│                           ↓                                               │
│  G10 HITL: Mapping Review → confirmed_mapping.yaml                        │
│  ↳ if new_components_proposed > 0: writes g8_revision_request.yaml        │
│    G8 targeted revision must run before G14 to formalize G10-PROV-* CIDs  │
│    G8 emits formalized_provisional_cids in g8_revision_report.yaml        │
└───────────────────────────────────────────────────────────────────────────┘
                                     │
┌─ FORMALIZATION ───────────────────────────────────────────────────────────┐
│  G11 Annotation Formalization  (does NOT block on G8 formalization)       │
│  → annotated preview/ (data-* written, G10-PROV-* CIDs annotated as-is)  │
│  + preview-data.json + annotation_layer.yaml                              │
│                                                                           │
│  G12 Accessibility Reviewer → g12_accessibility_report.yaml              │
│  G13 PM Traceability Reviewer → g13_pm_traceability_report.yaml          │
└───────────────────────────────────────────────────────────────────────────┘
                                     │
┌─ H HANDOFF ───────────────────────────────────────────────────────────────┐
│  G14 H Package Generator → handoff/ (screen_blueprints + packages)       │
│  G15 Owner Sign-off → handoff/g21_gate_report.yaml                       │
│                           ↓ [APPROVED]                                    │
│                     H Layer begins                                        │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 6. HITL Touchpoints

| # | Agent | What owner does | Mode |
|---|-------|----------------|------|
| 1 | **G4** Asset Generator | Co-authors icons one at a time: selects metaphors, iterates on variants, accepts each icon | Interactive co-author embedded in generation |
| 2 | **G7** Creative Surface Designer | Co-authors surfaces one at a time: selects layout approaches, iterates, accepts each surface | Interactive co-author embedded in design |
| 3 | **G10** Mapping Review | Confirms/corrects component label assignments in visual overlays | Review + correction; blocks G11 |
| 4 | G12 → G7 loop | Accessibility violations (if any) — targeted fixes | Conditional; yes if violations found |
| 5 | **G15** Owner Sign-off | Final review of annotated preview + traceability summary | Final gate; blocks H layer |

HITL is no longer a post-facto review step — it is embedded in the creative agents (G4, G7). The owner co-authors assets and surfaces with the agent from the start.

---

## 7. H Layer — Actual Structure and Input Requirements

H layer has **14 agents** (prompts exist at project root). Their structure:

| Agent | Role | Critical G inputs |
|-------|------|-----------------|
| H1 Traceability Index Builder | Normalizes all trace links | `screen_blueprints.yaml` **(MANDATORY — BLOCK if absent)**, `g21_gate_report.yaml`, `g12_accessibility_report.yaml`, `g12_composition_report.yaml`, `component_system.yaml`, `generated_assets.yaml`, `prd.index.yaml`, `surface_map.yaml`, `navigation_map.yaml` |
| H2 Traceability QA | Audits H1 index | Same G inputs as H1 |
| H3 Elm Module Architect | Module decomposition, routing | `screen_blueprints.yaml`, `g21_gate_report.yaml` |
| H4 Elm Module QA | Audits H3 | H3 output |
| H5 Elm State & Type Architect | Model structure, Msg taxonomy | `screen_blueprints.yaml`, `prd.index.yaml` |
| H6 Elm State & Type QA | Audits H5 | H5 output |
| H7 Elm Update Architect | Update branches, effects | H5 output |
| H8 Elm Update QA | Audits H7 | H7 output |
| H9 Elm View Architect | View functions per surface | `screen_blueprints.yaml` **(visual ground truth)**, `component_system.yaml` |
| H10 Elm View QA | Audits H9 | H9 output |
| H11 Elm Architecture Integrator | Cross-module assembly | All H specs |
| H12 Elm Architecture QA | Final architecture audit | H11 output |
| H13 Elm Architecture HITL | Owner HITL on architecture | H12 output |
| H14 Elm Architecture Gatekeeper | Final gate before Elm implementation | H13 sign-off |

### Before H starts: required handoff artifacts

| H1 expects | Produced by | How |
|------------|-------------|-----|
| `screen_blueprints.yaml` | G14 | Built from annotation_layer (G11) + surface_map (F1) + ia_map (F3) |
| `g21_gate_report.yaml` | G15 | Owner sign-off |
| `g13_pm_traceability_report.yaml` | G13 | PM traceability audit |
| `g12_accessibility_report.yaml` | G12 | Accessibility audit |
| `g12_composition_report.yaml` | G14 (initial) + G15 (patch) | G14 sets `approved_surfaces: pending_g15`; G15 patches |
| `component_system.yaml` | G14 (from G8 + G11) | Built from component_manifest + annotation_layer |
| `generated_assets.yaml` | G4 (via G14) | Asset manifest |
| `asset_strategy.yaml` | G3 (via G14) | Asset strategy |

---

## 8. Key Design Decisions for G7 Prompt

G7 is the most important new prompt to write.

### Must include:
- Interactive co-authoring model: same as G4 — one surface at a time, propose layout approaches, iterate, accept; HITL is co-author not reviewer
- Platform discovery instruction: "read surface_map.yaml to determine which surfaces exist per platform and how they differ structurally"
- Per-surface creative guidance (balance_setup warmth, aha_moment gradient, chat 6 modes, etc.)
- E-invariant reference (all 16, as do/don't checklist — mental guardrails, not YAML targets)
- Asset reference instruction: "use files from generated_assets/ by asset_id; g6_revision_report.ready_for_next_gate must be true before starting"
- Semantic HTML requirement: use article/section/header/aside; class names must reflect component type
- Typography scale (Plus Jakarta Sans, resolved sizes from design_system_reference)
- Surface order: mobile tier-1 first, then tier-2, tier-3, then web variants

### Must NOT include:
- data-cid, data-zone, data-inv, data-g-oc, data-gc instructions
- preview-data.json generation
- Condition coverage tracking (G-OC/GC)
- YAML output schemas (no intermediate YAML except g7_revision_report)
- Component family naming conventions (canonical CID assignment is G8's job; G9 only maps CIDs to HTML candidates)
- r10 Elm API calls

---

## 9. Prompt Authoring Order

Existing prompts G1/G2/G4/G5/G6 are current and correct (G4 was rewritten as interactive co-author).

**Priority order for new/remaining prompts:**

1. **G7 Creative Surface Designer** — critical path; interactive co-author model like G4
2. **G8 Component Manifest Builder** — needed after first G7 completion
3. **G9 Component Mapper** — needed after G8
4. **G10 HITL Mapping Review** — gate before G11
5. **G11 Annotation Formalization** — mechanical; straightforward once G8–G10 exist
6. **G3 Asset Strategy** — update: now reads design_system_reference instead of preview HTML
7. **G12 Accessibility** — renumber from G14
8. **G13 PM Traceability** — renumber from G15
9. **G14 H Package Generator** — update: new input sources (G8 component_manifest, G11 annotation_layer)
10. **G15 Owner Sign-off** — renumber from G17; update references

*Already written: G1, G2, G4 (rewritten), G5, G6.*
*Eliminated: G7 Asset HITL (absorbed into G4), G9 HITL Visual Design Review (absorbed into G7).*

---

## 10. Agent Count Summary

| Tier | Agents | v2 count | v3 count | Delta |
|------|--------|----------|----------|-------|
| Foundation | G1, G2 | 2 | 2 | — |
| Assets | G3–G6 | 5 | 4 | −1 (G7 Asset HITL absorbed into G4) |
| Creative | G7 | 2 | 1 | −1 (G9 HITL absorbed into G7) |
| Component architecture | G8–G10 | 3 | 3 | renumbered |
| Formalization | G11–G13 | 3 | 3 | renumbered |
| H Handoff | G14–G15 | 2 | 2 | renumbered |
| **Total** | | **17** | **15** | −2 net eliminated |

The −2: G7 Asset HITL and G9 HITL Visual Design Review are eliminated because HITL co-authoring is now embedded in G4 and G7 respectively. Owner participation is earlier and richer; post-hoc review stages are removed.

---

## 11. H Layer Agent Inputs — Quick Reference

Artifact names are **fixed by H-layer convention** and do not change when producer G-numbers change.

| Artifact | Produced by | Read by H agents |
|----------|-------------|-----------------|
| `screen_blueprints.yaml` | **G14** | H1 **(MANDATORY)**, H2, H3, H5, H9 |
| `g21_gate_report.yaml` | **G15** | H1, H2, H3 |
| `g13_pm_traceability_report.yaml` | **G13** | G14 (gate check), G15 (owner review) |
| `g12_accessibility_report.yaml` | **G12** | H1 |
| `g12_composition_report.yaml` | **G14** (init) + **G15** (patch) | H1 |
| `component_system.yaml` | **G14** (from G8+G11) | H1, H2, H9 |
| `generated_assets.yaml` | **G4** (via G14) | H1 |
| `asset_strategy.yaml` | **G3** (via G14) | H1 |
| `design_system_reference.yaml` | G1 | H agents (via h_packages) |
| `navigation_map.yaml` | F2 (unchanged) | H1, H3, H5, H9 |
| `surface_map.yaml` | F1 (unchanged) | H1, H2, H3, H9 |
| `prd.index.yaml` | D7 (unchanged) | H1 **(MANDATORY)**, H2, H5 |

---

*v2 — rewritten 2026-05-18. v3 — updated 2026-05-20: G4 rewritten as interactive co-author; old Creative Designer role moved to G7 Creative Surface Designer (interactive co-author); G7 Asset HITL eliminated; G9 HITL Visual Design Review eliminated; pipeline renumbered to 15 agents. Start prompt authoring with G7 (Creative Surface Designer).*
