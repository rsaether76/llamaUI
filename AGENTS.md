## Repository Map

A full codemap is available at `codemap.md` in the project root.

Before working on any task, read `codemap.md` to understand:
- Project architecture and entry points
- Directory responsibilities and design patterns
- Data flow and integration points between modules

For deep work on a specific folder, also read that folder's `codemap.md`.

---

## Session State — last updated 2026-06-29

**Branch:** `feature/option-picker`  
**Working directory:** `/home/rshibley/llamaUI`  
**Remote:** `origin https://github.com/rsaether76/llamaUI.git`  
**Latest commit:** `8f2427b feat: use Qt Fusion style and remove custom input widget QSS`

### Recently completed work

1. **Option Picker Dialog** — "Add Options…" button in Advanced Groups lets users browse parsed `--help` options and add them to Main Settings or an Advanced tab. Layout persistence is in `user_options.json`; values flow through `profile.raw_args`.
2. **`--split-mode` / `--tensor-split` fix** — parser no longer breaks on commas inside value placeholders (`{none,layer,row,tensor}`); stale schema caches are invalidated via `SCHEMA_PARSER_VERSION`.
3. **Visible remove buttons** — user-added options show a 26×26 "×" in the `OptionCard` header.
4. **Hide-on-remove** — `UserOptions.hidden_flags` lets users actually remove cards from the UI; re-adding unhides them.
5. **Fusion style** — app now sets `Fusion` style and no longer custom-styles `QLineEdit`, `QComboBox`, `QSpinBox`, `QDoubleSpinBox`, so fields use Qt's standard borders/selection.

### Files most likely to need further edits

- `qt_app/app/pages/run.py` — Run page UI, option picker, remove buttons, schema injection.
- `qt_app/app/services/help_parser.py` — llama-server `--help` parser.
- `qt_app/app/services/option_schema.py` — runtime schema + cache.
- `qt_app/app/theme.py` / `qt_app/app/application.py` — styling and app bootstrap.
- `qt_app/llama_data/models.py` — `UserOptions` / `hidden_flags`.

### Known open items / things to verify on return

- The user wanted `--split-mode` / `--tensor-split` visible; they are now in **Advanced Groups → GPU / offload**. Consider whether they should be promoted to `MAIN_OPTION_IDS` for quicker access.
- The "Add Options…" dialog currently shows options already visible in Advanced Groups. Adding one of those just adds a remove button to the existing card. Decide if this is the desired UX or if already-visible options should be filtered from the picker.
- Scroll-wheel guard, resizable sections (QSplitter), light theme, and X11/xcb platform detection are in place and were not reverted.
- The user's environment: Linux Mint 22.3 Cinnamon (X11), single 3440×1440 ultrawide monitor. The `llama-swap` systemd service was disabled.

### How to run

```bash
cd /home/rshibley/llamaUI
. .venv/bin/activate
llamaui
```

### Commit/push status

Working tree is clean and all recent changes are pushed to `origin/feature/option-picker`.
