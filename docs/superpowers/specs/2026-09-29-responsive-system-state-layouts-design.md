# Responsive System-State Layouts Design

## Goal

Make OwnDash system-state screens genuinely responsive across the display shapes used by the Linux dashboard community while preserving the already accepted 480×1920 VSDISPLAY presentation as a protected reference.

The current renderer scales the complete 1:4 artwork proportionally and centers it on a dark canvas. This avoids distortion but wastes substantial space on portrait, square, 16:10 and 16:9 displays. The new design keeps exactly one production renderer path and replaces the fixed 1:4 composition with a modular responsive compositor.

## Success criteria

- 480×1920 remains visually equivalent to the physically accepted VSDISPLAY layout.
- Other aspect ratios use their available area instead of displaying a narrow centered 1:4 strip.
- No content is stretched, clipped or rendered outside its safe area.
- The renderer selects behavior from aspect ratio, not a list of known resolutions.
- Status text, detail text, language, clock, date and OwnDash version remain runtime data.
- No version string, localized wording, clock or date is baked into artwork.
- Adding a future Beta, RC or stable version requires no system-state artwork change.
- Adding a future system state requires state metadata and artwork, not duplicate layouts for every display class.
- The existing lifecycle, animation, localization and output contracts remain intact.

## Architectural direction

Use a modular responsive compositor inside the existing single renderer path.

The renderer has four responsibilities:

1. classify the target geometry by aspect ratio;
2. resolve reusable state artwork and state metadata;
3. obtain the layout profile for that aspect-ratio class;
4. compose artwork and runtime text into the final target-sized image.

This does not introduce versioned renderers, hidden fallbacks, per-device renderers or a second production path.

## Layout classes

Classification uses `ratio = width / height` after validating that width and height are positive.

- `ultra_portrait`: `ratio < 0.38`
- `portrait`: `0.38 <= ratio < 0.78`
- `near_square`: `0.78 <= ratio <= 1.25`
- `landscape`: `ratio > 1.25`

These thresholds are architectural constants, not user settings. Individual pixel resolutions must not be hard-coded into renderer behavior.

Examples:

- 480×1920 → `ultra_portrait`
- 720×1280 → `portrait`
- 800×1280 → `portrait`
- 1024×1024 → `near_square`
- 1024×600 → `landscape`
- 1280×800 → `landscape`
- 1920×1080 → `landscape`
- 2560×1440 → `landscape`

## Layout behavior

### Ultra portrait

This class protects the accepted 480×1920 visual hierarchy. The composition remains vertically stacked: state HUD/symbol in the upper portion, localized state copy in the middle, optional clock/date below it and version footer near the bottom.

The 480×1920 output is the visual regression baseline. Converting its geometry to responsive coordinates must not noticeably change the accepted composition.

### Portrait

Portrait displays keep the vertical hierarchy but use their extra width. The state artwork occupies a wider upper region, the state copy follows below, and clock/date use a compact lower-middle region. The design must not simply contain the ultra-portrait composition inside unused side margins.

### Near square

Near-square displays use a balanced composition. When space allows, state artwork and information form two visual columns; compact near-square targets may use a balanced stacked arrangement. Both forms are implementations of the same near-square profile and must obey common safe-area and typography rules.

### Landscape

Landscape displays use a horizontal composition: state artwork/HUD is placed to the left and the primary information group to the right. Clock/date remain subordinate to state information. The version footer spans or aligns with the overall composition rather than being trapped inside a portrait strip.

## Relative geometry

Layout profiles use normalized or target-relative geometry. They define zones for:

- state artwork/HUD;
- state title;
- optional detail text;
- optional clock;
- optional date;
- accent treatment;
- version footer;
- safe margins.

Profiles may use minimum and maximum pixel guards where required for legibility, but those guards are typography/safety constraints rather than resolution-specific layouts.

The renderer must compute final rectangles from the target width and height each time it renders.

## Artwork model

System-state PNGs must become reusable visual assets rather than complete final screens.

Long-lived artwork may contain:

- state-specific symbol/iconography;
- HUD rings and decorative geometry;
- glow and light effects;
- non-verbal background treatment.

Artwork must not contain:

- state wording;
- translated text;
- clock values;
- dates;
- OwnDash release/version strings.

Where practical, reusable state artwork should use transparent backgrounds so the compositor can place and scale it independently from panels and text. Backgrounds, panels, accents and runtime areas should be renderer-owned where doing so improves responsive composition.

The visual identity remains:

- locked: cyan / magenta;
- idle: cyan / green;
- standby: amber / gold;
- shutdown: red;
- restart: violet / magenta;
- disconnected: cyan / magenta.

## Runtime content

The renderer receives target size plus state/runtime data and produces a final `QImage`.

Runtime content includes:

- localized title;
- localized optional detail;
- optional clock;
- optional date;
- `OwnDash {__version__}` footer;
- animation phase where supported.

The version footer is always derived from the central OwnDash version. Beta 4, Beta 5, RC, stable and later release labels must therefore update automatically without artwork edits.

Localized strings remain authoritative. Artwork must never override the current application language.

## Typography

- Titles should remain single-line whenever the available zone permits.
- Title font size is fitted to the title zone rather than blindly scaled from 480×1920.
- Detail text may wrap to at most two lines when necessary.
- Clock/date modules are optional. When absent, the surrounding layout may reclaim their space instead of reserving an empty fixed panel.
- Footer text is always visible but visually secondary.
- Minimum readable font guards prevent tiny text on small targets.
- Text must remain inside safe zones at every supported aspect ratio.

## State model and animation

All system states use the same layout-selection and composition machinery. State differences are data: artwork, colors, localized copy and whether the HUD sweep is allowed.

Existing behavior is preserved:

- `LOCKED` and `IDLE` may use the existing low-rate HUD sweep animation;
- suspend, transition, shutdown, restart and disconnected outputs remain static;
- lifecycle-state priority and event handling are outside this visual refactor and must not change.

## Rotation and output contracts

The renderer receives the logical width and height it is expected to render. Existing output/back-end rotation remains outside the responsive layout classifier unless a caller already passes rotated logical dimensions.

The responsive work must preserve exact requested output dimensions and existing USB/monitor transport behavior.

## Error handling

- Non-positive width or height raises `ValueError`.
- Unsupported state values raise `ValueError` as today.
- Missing required artwork is a visible development/runtime failure; no retired or hidden fallback artwork may be reintroduced.
- Extremely unusual but valid aspect ratios select the closest defined class through the threshold rules and must still honor safe zones and non-distortion requirements.

## Preview matrix

The preview tool must produce at least these target sizes:

- 480×1920
- 720×1280
- 800×1280
- 1024×1024
- 1024×600
- 1280×800
- 1920×1080
- 2560×1440

For each target, preview coverage includes:

- locked;
- idle;
- standby;
- shutdown;
- restart;
- disconnected.

The matrix is a visual acceptance tool and must be generated through the same production renderer path used by OwnDash.

## Automated regression coverage

Tests must cover at least:

- layout-class boundaries, including exact threshold values;
- exact output dimensions across the preview matrix;
- 480×1920 reference-class behavior;
- non-distorted artwork placement;
- runtime version rendering;
- German and English runtime text fitting;
- optional clock/date behavior;
- maximum two-line detail behavior;
- safe-area containment for all text modules;
- static terminal states;
- animation only for locked/idle;
- disconnected screen using the same responsive system;
- missing/invalid target geometry failure;
- existing USB logical-orientation contract.

Pixel-perfect tests should be used only where they protect the accepted 480×1920 reference or deterministic renderer-owned primitives. Other layout classes should prefer structural assertions so harmless antialiasing/font differences do not create brittle tests.

## Physical and release acceptance

The already completed 480×1920 Bazzite/KDE + VSDISPLAY checks remain the physical reference. After the refactor, that hardware is rechecked to ensure the protected class did not regress.

Other aspect ratios are accepted through the automated matrix plus visual review of generated previews. Real community hardware remains valuable follow-up evidence but is not required to create a responsive architecture.

The change is release-ready when:

- the complete automated suite passes;
- the AppImage build/compatibility workflow passes;
- the preview matrix is visually reviewed;
- 480×1920 remains visually accepted on the real VSDISPLAY;
- documentation states that system-state layouts are responsive rather than merely contained.

## Scope boundaries

This change does not alter:

- Linux lifecycle detection;
- idle/lock/suspend/restart/shutdown priority semantics;
- USB reconnect policy;
- software dimming;
- device capability detection;
- normal dashboard layout behavior;
- hardware brightness, Expansion Screen Mode or startup-media support.

It may split renderer responsibilities into focused modules if needed for maintainability, but unrelated GUI refactoring is out of scope.
