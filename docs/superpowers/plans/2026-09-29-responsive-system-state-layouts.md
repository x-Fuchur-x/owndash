# Responsive System-State Layouts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current fixed 1:4 contain behavior with one responsive system-state compositor that preserves the accepted 480×1920 output and uses the available area on portrait, square and landscape displays.

**Architecture:** Add a focused layout module that classifies target geometry and returns target-relative zones. Keep the public renderer API intact, preserve the 480×1920 reference path, and compose all other shapes from state artwork plus renderer-owned panels and runtime text. The same production path remains authoritative for normal system states and disconnected output.

**Tech Stack:** Python 3.11+, PySide6/QPainter/QImage, Pillow resource decoding, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-29-responsive-system-state-layouts-design.md`

## Global Constraints

- Exactly one production system-state renderer path.
- Layout selection is based on `width / height`, not known resolution lists.
- Layout classes are `ultra_portrait` (< 0.38), `portrait` (>= 0.38 and < 0.78), `near_square` (>= 0.78 and <= 1.25), and `landscape` (> 1.25).
- 480×1920 remains the protected physical reference.
- Runtime state copy, language, clock, date and `OwnDash {__version__}` remain dynamic.
- No hidden fallback to retired artwork or renderer generations.
- Existing lifecycle state semantics, USB reconnect behavior, rotation contract and animation policy remain unchanged.

## Review Focus

- Exact threshold boundaries must classify deterministically, especially 0.38, 0.78 and 1.25.
- Extremely wide or tall valid targets must render inside safe margins without clipping.
- Long German/English state copy must fit without escaping its assigned zones.
- Missing clock/date must not leave a structurally broken empty panel.
- 480×1920 must not regress while non-1:4 layouts stop behaving like centered portrait strips.

---

### Task 1: Responsive layout model

**Files:**
- Create: `src/owndash/gui/system_state_layout.py`
- Create: `tests/test_system_state_responsive_layout.py`

**Interfaces:**
- Produces: `LayoutClass`, `SystemStateLayout`, `classify_layout(width: int, height: int) -> LayoutClass`, `layout_for_size(width: int, height: int) -> SystemStateLayout`.
- `SystemStateLayout` exposes target-space `QRectF` zones for art, title, detail, clock, date, accent and footer plus a safe rectangle and layout class.

- [ ] **Step 1: Write failing tests for class boundaries and representative sizes**

Assert 480×1920 is ultra portrait; 720×1280 and 800×1280 are portrait; 1024×1024 is near square; 1024×600, 1280×800, 1920×1080 and 2560×1440 are landscape. Assert exact ratios 0.38 and 0.78 enter the next class and 1.25 remains near square.

- [ ] **Step 2: Write failing structural tests for safe zones**

For each preview-matrix size, assert every returned zone lies within the target and inside the safe rectangle; assert landscape art and information zones are side-by-side; assert portrait classes are vertically ordered; assert extreme valid sizes such as 240×1920 and 3440×480 still return contained zones.

- [ ] **Step 3: Run the focused tests and confirm RED**

Run: `pytest tests/test_system_state_responsive_layout.py -q`
Expected: collection/import failure because the new layout module does not exist.

- [ ] **Step 4: Implement the layout model**

Create immutable dataclasses/enums and compute all rectangles from target size with relative coordinates plus conservative safe margins. Do not add resolution-specific branches.

- [ ] **Step 5: Run focused tests and full suite**

Run: `pytest tests/test_system_state_responsive_layout.py -q && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

Commit message: `feat: add responsive system-state layout model`

### Task 2: Responsive compositor while protecting 480×1920

**Files:**
- Modify: `src/owndash/gui/system_state_frame.py`
- Modify: `tests/test_system_state_renderer_redesign.py`
- Modify: `tests/test_system_state_pr_review_fixes.py`
- Modify: `tests/test_system_state_responsive_layout.py`

**Interfaces:**
- Consumes: `layout_for_size()` from Task 1.
- Preserves: `render_system_state_image(...) -> QImage` and `render_disconnected_status_image(...) -> QImage` signatures.

- [ ] **Step 1: Replace the obsolete landscape-contain regression with failing responsive assertions**

Assert a 1920×1080 locked frame has meaningful non-background content in both left artwork and right information regions instead of a narrow centered portrait strip. Assert exact output dimensions.

- [ ] **Step 2: Add failing tests for runtime text and optional modules across classes**

Render representative German and English frames at each class, verify output changes with localized copy/version source, and verify frames render successfully with clock/date omitted. Add a structural test that the footer zone remains inside the safe area.

- [ ] **Step 3: Confirm RED in CI/focused tests**

Run: `pytest tests/test_system_state_responsive_layout.py tests/test_system_state_pr_review_fixes.py tests/test_system_state_renderer_redesign.py -q`
Expected: responsive composition assertions fail against the current centered-contain renderer.

- [ ] **Step 4: Implement responsive composition**

Keep the accepted 480×1920 reference composition intact. For other classes, use the state artwork only as a source for its text-free HUD/symbol region, scale it with `Qt.KeepAspectRatio`, and place it in the layout art zone. Draw background, state panel, accent, clock/date and footer directly from target-space zones. Runtime strings remain authoritative and existing state-color/animation behavior remains unchanged.

- [ ] **Step 5: Add a text-wrapping helper for detail copy**

Implement a renderer-local helper that fits detail text into at most two lines inside the detail zone. Titles remain single-line with fitted font size.

- [ ] **Step 6: Verify 480×1920 reference and lifecycle animation regressions**

Run the renderer redesign, PR-review and system-state tests; confirm approved stable points and terminal-static tests remain green.

- [ ] **Step 7: Run full suite**

Run: `pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

Commit message: `feat: compose responsive system-state screens`

### Task 3: Preview matrix and visual acceptance tooling

**Files:**
- Modify: `tools/render_system_state_previews.py`
- Create or modify: `tests/test_system_state_preview_matrix.py`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Preview output root remains `preview/system-state/`.
- Produces one PNG per state per matrix size with deterministic names such as `locked-480x1920.png`.

- [ ] **Step 1: Write failing preview-matrix test**

Assert the tool declares all eight required target sizes and all six required state outputs.

- [ ] **Step 2: Confirm RED**

Run: `pytest tests/test_system_state_preview_matrix.py -q`
Expected: fail because the current tool only renders 480×1920.

- [ ] **Step 3: Expand the preview tool**

Render 480×1920, 720×1280, 800×1280, 1024×1024, 1024×600, 1280×800, 1920×1080 and 2560×1440 for locked, idle, standby, shutdown, restart and disconnected using the production renderer.

- [ ] **Step 4: Keep CI artifact upload broad enough for the matrix**

Ensure the existing preview artifact upload captures every generated PNG and update the step name from the 480×1920-specific wording.

- [ ] **Step 5: Verify tool and suite**

Run: `python tools/render_system_state_previews.py && pytest -q`
Expected: 48 PNGs produced and all tests pass.

- [ ] **Step 6: Commit**

Commit message: `test: add responsive system-state preview matrix`

### Task 4: Documentation and release-facing wording

**Files:**
- Modify: `docs/system-state-screens.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- No runtime interface changes.

- [ ] **Step 1: Update documentation after behavior is green**

Document aspect-ratio classes, responsive composition, protected 480×1920 reference, runtime-only mutable text/version data, and preview-matrix acceptance. Remove wording that says non-portrait output merely contains the 1:4 artwork.

- [ ] **Step 2: Run documentation-sensitive/source tests and full suite**

Run: `pytest -q`
Expected: all pass.

- [ ] **Step 3: Commit**

Commit message: `docs: document responsive system-state layouts`

### Task 5: Final verification and review

**Files:**
- No intended production changes unless verification exposes a defect.

**Interfaces:**
- Final branch must preserve the public renderer API and all existing lifecycle/output contracts.

- [ ] **Step 1: Run complete verification**

Run: `python -m compileall -q src tests tools && pytest -q && python tools/render_system_state_previews.py && bash -n run-owndash.sh`
Expected: success with no test failures.

- [ ] **Step 2: Verify CI and AppImage workflows on the exact branch head**

Require successful Tests and Build AppImage runs for the exact final commit.

- [ ] **Step 3: Visually inspect representative matrix outputs**

Inspect at least 480×1920, 800×1280, 1024×1024, 1280×800 and 1920×1080 across representative states. Confirm no clipping, no centered 1:4 strip on non-ultra layouts, and coherent visual hierarchy.

- [ ] **Step 4: Recheck 480×1920 on physical VSDISPLAY before merge**

Confirm the protected reference remains acceptable on the real hardware.

- [ ] **Step 5: Whole-branch review**

Review the diff against the spec for hidden alternate renderer paths, hard-coded resolutions in production behavior, mutable text embedded in newly introduced artwork, and lifecycle/output regressions.
