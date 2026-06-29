# llamaUI Changes Log

## Repository
- **Fork**: `rsaether76/llamaUI` (forked from `NickPittas/llamaUI`)
- **Branch**: `feature/option-picker`
- **Working directory**: `/home/rshibley/llamaUI`

---

## Change 8: Fix `--split-mode` / `--tensor-split` Missing from UI (bugfix)

### Problem
`--split-mode` and `--tensor-split` are present in the curated catalog under the "GPU / offload" group, but they did not appear in the Advanced Groups UI.

Two root causes:
1. `_parse_option_head()` in `help_parser.py` split the option head on every comma. For `--split-mode {none,layer,row,tensor}` this produced the broken value placeholder `{none`; for `--tensor-split N0,N1,N2,...` it produced `N0`. Worse, cached schemas built by earlier parser versions were missing these options entirely (only 188 options cached vs. 231 parsed now).
2. The runtime schema cache had no parser-version field, so stale cached schemas kept being reused even after parser fixes.

### Solution
1. Rewrote `_parse_option_head()` to split on whitespace instead of commas. Flag tokens like `-sm,` have their trailing comma stripped; value placeholders like `{none,layer,row,tensor}` and `N0,N1,N2,...` stay intact.
2. Added `SCHEMA_PARSER_VERSION` and a `parser_version` field to `RuntimeSchema`. `SchemaCache.load()` now rejects cached schemas whose version doesn't match, forcing a re-parse when the parser changes.

### Files Modified

**`qt_app/app/services/help_parser.py`**
- Rewrote `_parse_option_head()`: whitespace split + trailing-comma strip on flag tokens; value placeholders preserved.

**`qt_app/app/services/option_schema.py`**
- Added `SCHEMA_PARSER_VERSION = 1` constant.
- Added `parser_version` field to `RuntimeSchema` with JSON round-trip.
- `build_runtime_schema()` stamps new schemas with `SCHEMA_PARSER_VERSION`.
- `SchemaCache.load()` returns `None` for schemas with a mismatched `parser_version`, so stale caches are discarded automatically.

**`qt_app/llama_data/llama_options.py`**
- Updated `split_mode` default from `"none"` to `"layer"` to match the binary's actual default.

**`qt_app/app/widgets/cards.py`**
- Added a header actions area to `OptionCard`.
- Added `add_header_widget()` method so callers can place action buttons in the card header.

**`qt_app/llama_data/models.py`**
- Added `hidden_flags: set[str]` to `UserOptions` with JSON round-trip.
- Added `is_hidden()`, `hide()`, `unhide()` methods.
- `UserOptions.add()` now unhides the flag so re-adding a previously hidden option works.

**`qt_app/app/pages/run.py`**
- Moved user-added option remove buttons from the card body into the card header so they are always visible.
- Styled the remove button with the `danger` variant and increased size to 26×26.
- Clicking × now hides the option via `UserOptions.hidden_flags`, so the card actually disappears from the UI.
- `_build_schema_advanced()` and `_build_catalog_advanced()` skip hidden flags.
- `_user_added_options_for_destination()` skips hidden flags.
- Reverted the over-aggressive picker filtering so the Add Options dialog again shows available schema options.
- If a user-added option is already shown by the schema, the existing card gets the remove button instead of a duplicate card.

**`qt_app/app/theme.py`**
- Added `QPushButton#UserOptionRemoveBtn` QSS rule: 26×26 square, muted default, red on hover.

---

## Change 1: Option Picker Dialog (feature)

### Problem
The curated catalog in `llama_options.py` only contained ~47 hardcoded options. The `llama-server --help` output exposes 230+ options. Users had no way to access the missing options through the UI.

### Solution
Added an "Add Options…" button to the Advanced Groups section that opens a dialog letting users browse all parsed `--help` options, select them, and assign them to either the Main Settings group or an Advanced group tab.

### Architecture
- **UI layout persistence** (which options are shown, where) is stored in `user_options.json` via `UserOptionStore`
- **Option values** (what the user sets `--mirostat` to) flow through the existing `profile.raw_args` mechanism — zero changes to `build_argv` or `_settings_from_form`
- User-added options are registered in `_schema_options_by_id` so `_load_profile_into_form` → `_load_unknown_editor` can restore their values from profiles

### Files Modified

**`qt_app/llama_data/paths.py`**
- Added `USER_OPTIONS_FILE = "user_options.json"` constant
- Added `user_options_path: Path` field to `DataPaths` dataclass
- Updated `default_paths()` to include the new path

**`qt_app/llama_data/models.py`**
- Added `UserOptionEntry` dataclass: stores `flag` (e.g. `"--mirostat"`) and `destination` (e.g. `"Sampling"` or `"main"`)
- Added `UserOptions` dataclass: collection of entries with `add()`, `remove()`, `has_flag()`, JSON serialization
- Updated `__all__` exports

**`qt_app/llama_data/stores.py`**
- Added `USER_OPTIONS_MIGRATIONS` migration chain
- Added `_USER_OPTIONS_WRITE_LOCK` threading lock
- Added `UserOptionStore` class with `load()` → `UserOptions` and `save()` using `VersionedEnvelope` pattern (consistent with `ConfigStore`, `LibraryStore`, `ProfileStore`)
- Updated `__all__` exports

**`qt_app/llama_data/__init__.py`**
- Added imports and exports for `UserOptionEntry`, `UserOptions`, `UserOptionStore`

**`qt_app/app/main_window.py`**
- Import `UserOptionStore` from `llama_data`
- Create `user_option_store = UserOptionStore.default()` alongside other stores
- Pass `user_option_store` to `RunPage` constructor

**`qt_app/app/pages/run.py`**
- Added `QDialog` import, `CollapsibleGroup` import, `UserOptionStore` import
- `RunPage.__init__`: accepts `user_option_store` parameter
- Added `_OptionPickerDialog` class: searchable dialog with collapsible category groups, checkboxes per option, destination dropdown ("Main Settings" or any Advanced group), "Add Selected" button
- Added "Add Options…" `SecondaryButton` to Advanced Groups header
- Added `_open_option_picker()`: opens dialog, captures form values, rebuilds UI, restores values
- Added `_restore_form_values()`: restores editor values after UI rebuild using a temporary `ModelProfile`
- Added `_make_user_option_remove_button()`: creates × button for removing user-added options
- Added `_remove_user_option()`: removes option from store, rebuilds UI
- Added `_user_added_options_for_destination()`: returns `RuntimeOption` list for a given destination
- Modified `_build_main_settings()`: injects user-added options with `destination == "main"` in a "User options" sub-section below the existing grid
- Modified `_build_schema_advanced()`: normalizes group keys to display names, tracks tab pages in `self._tab_pages`, calls `_inject_user_options_into_tabs()`
- Added `_inject_user_options_into_tabs()`: injects user-added options into existing tabs or creates new tabs for destinations that don't have a tab yet
- Modified `_build_catalog_advanced()`: same tab tracking and injection

---

## Change 2: Help Parser Fix for Curly-Brace Values (bugfix)

### Problem
The regex `_OPTION_RE` in `help_parser.py` didn't match options with `{value1,value2,...}` syntax like `--split-mode {none,layer,row,tensor}`. The `{` and `,` characters weren't in the value placeholder character class. This caused ~20 options to be silently dropped from the parsed schema.

### Solution
Extended the regex character class to include `{`, `}`, and `,`. Added a fallback regex `_OPTION_HEAD_ONLY_RE` for option lines with no description on the same line (description follows on subsequent indented lines).

### Files Modified

**`qt_app/app/services/help_parser.py`**
- Updated `_OPTION_RE` regex: added `\[{` and `>\]}` to handle curly-brace value placeholders
- Added `_OPTION_HEAD_ONLY_RE` regex: matches flag lines without a description
- Updated `parse_help_options()`: tries `_OPTION_HEAD_ONLY_RE` as fallback when `_OPTION_RE` doesn't match

### Options now parsed that were previously missed
`--split-mode`, `--rope-scaling`, `--pooling`, `--spec-type`, `--numa`, `--fit`, `--flash-attn`, `--log-colors`, `--reasoning`, `--mirostat`, and others using `{value1,value2}` syntax.

---

## Change 3: Deduplicate Advanced Group Tabs (bugfix)

### Problem
The help parser produces group slugs like `"gpu_offload"`, `"context_kv"`, `"server_api"` while the curated catalog uses display names like `"GPU / offload"`, `"Context / KV cache"`, `"Server / API"`. Both mapped to the same display name via `_GROUP_DISPLAY`, but `_build_schema_advanced` grouped by raw key, creating duplicate tabs with the same label.

### Solution
Normalize all group keys to display names via `_group_display()` before grouping in `_build_schema_advanced`. Also normalize the `group_order` list from the catalog.

### Files Modified

**`qt_app/app/pages/run.py`**
- In `_build_schema_advanced()`: changed `groups.setdefault(rt_opt.group, ...)` to use `_group_display(rt_opt.group)` as the key
- Changed `group_order` to normalize catalog group names via `_group_display()`

---

## Change 4: Add `tensor` to `--split-mode` Enum (enhancement)

### Problem
The `--split-mode` catalog entry only had `none`, `layer`, `row` as enum values, but the binary also supports `tensor` (experimental).

### Solution
Added `("tensor","tensor")` to the `enum_values` tuple.

### Files Modified

**`qt_app/llama_data/llama_options.py`**
- Updated `split_mode` option: added `("tensor","tensor")` to `enum_values`, updated help text

---

## Change 5: Scroll Wheel Guard (bugfix/UX)

### Problem
`QSpinBox`, `QDoubleSpinBox`, `QSlider`, and `QComboBox` widgets change values on mouse wheel hover. When scrolling the page (which is a `QScrollArea`), the cursor passing over these controls would accidentally change their values instead of scrolling.

### Solution
Added `_WheelGuardFilter` event filter that consumes all `QWheelEvent` events on these controls. Users must click/focus a control before changing its value.

### Files Modified

**`qt_app/app/widgets/slider_spin.py`**
- Added `_WheelGuardFilter(QObject)`: event filter that blocks all wheel events
- Added `_WHEEL_GUARD` singleton instance
- Added `install_wheel_guard(widget)`: installs the filter on any widget
- `SliderSpinBox.__init__`: installs guard on both `_slider` and `_spin`
- `SliderDoubleSpinBox.__init__`: installs guard on both `_slider` and `_spin`

**`qt_app/app/pages/run.py`**
- Imported `install_wheel_guard`
- `_make_editor()`: installs guard on standalone `QSpinBox`, `QDoubleSpinBox`, and `QComboBox` widgets
- `_make_schema_editor()`: installs guard on `QComboBox` widgets
- `_models_max_spin`: installs guard after creation

**`qt_app/app/pages/settings.py`**
- Imported `install_wheel_guard`
- Installed guard on all 6 standalone spinboxes (port, remote port, threads, batch, GPU layers, temp)

---

## Change 6: X11 Platform Detection (bugfix)

### Problem
On Linux Mint 22.3 with Cinnamon (X11), if `WAYLAND_DISPLAY` is set (e.g. from XWayland), Qt might select the Wayland plugin, causing input/rendering bugs. Also, `QT_ENABLE_HIGHDPI_SCALING` and `QT_AUTO_SCREEN_SCALE_FACTOR` were set unconditionally but are Wayland-specific, potentially causing blurry/oversized widgets on X11.

### Solution
Added `_configure_platform()` to force `QT_QPA_PLATFORM=xcb` on X11 sessions. Added `_configure_hidpi()` to only enable HiDPI env vars on Wayland.

### Files Modified

**`qt_app/app/application.py`**
- Added `_configure_platform()`: detects X11 via `XDG_SESSION_TYPE` or `DISPLAY`/`WAYLAND_DISPLAY`, sets `QT_QPA_PLATFORM=xcb`
- Added `_configure_hidpi()`: only sets `QT_ENABLE_HIGHDPI_SCALING` and `QT_AUTO_SCREEN_SCALE_FACTOR` on Wayland
- Called both functions at module level before `create_app()`
- Updated KDE Wayland comment

---

## Change 7: Nested Scroll Area Propagation (bugfix)

### Problem
Each page is a `QScrollArea` (`PageBase`), and each advanced-group tab is also wrapped in a `QScrollArea`. When the inner tab's content was fully scrolled, wheel events were silently consumed — the outer page wouldn't scroll.

### Solution
Added `_WheelPropagatorFilter` that monitors wheel events on inner scroll areas. When the inner area hits its scroll boundary, the event is forwarded to the outer page scroll area.

### Files Modified

**`qt_app/app/pages/base.py`**
- Added `_WheelPropagatorFilter(QObject)`: event filter that forwards wheel events to a target scroll area when the source is at its boundary
- Added `install_wheel_propagation(inner, outer)`: installs the filter
- Added `QEvent` and `QObject` imports

**`qt_app/app/pages/run.py`**
- Imported `install_wheel_propagation`
- Installed propagation on all 4 inner `QScrollArea` instances (tab containers) in `_build_schema_advanced`, `_inject_user_options_into_tabs`, and `_build_catalog_advanced`

---

## Change 8: Center Window on Primary Screen (bugfix)

### Problem
On Cinnamon/X11 with multi-monitor setups, the window was placed on a secondary monitor or off-screen. The window had no explicit position — Cinnamon's window placement decided where to put it.

### Solution
Added code to center the window on the primary screen's available geometry at startup.

### Files Modified

**`qt_app/app/main_window.py`**
- Added `QGuiApplication` import
- After `self.setMinimumSize()`: gets primary screen geometry, calculates centered position, calls `self.move()`

---

## Change 9: Resizable Sections via Splitter (UX)

### Problem
The main settings and advanced groups cards had fixed heights calculated by `_refit_advanced_panel`. Users couldn't resize the advanced groups section to see more or fewer options without scrolling.

### Solution
Wrapped both cards in a vertical `QSplitter` so users can drag the divider to resize. Removed the forced fixed-height logic.

### Files Modified

**`qt_app/app/pages/run.py`**
- Added `QSplitter` import
- Modified `_build_main_settings()`: removed `self._layout.addWidget(card)` (card stored but not added to layout directly)
- Modified `_build_advanced_groups()`: removed `self._layout.addWidget(card)`
- Added `_build_content_splitter()`: creates vertical `QSplitter` with both cards, sets initial sizes [300, 500]
- Modified `build()`: calls `_build_content_splitter()` after building both cards
- Replaced `_refit_advanced_panel()`: simplified to only reset min/max height constraints (no more forced sizing)
- Updated `_open_option_picker()` and `_remove_user_option()`: call `_build_content_splitter()` during rebuild

---

## Change 10: Light Theme with Better Contrast (UX)

### Problem
The dark theme had very low contrast — checkboxes were invisible, elements blended together, and the splitter handle was too thin to see.

### Solution
Converted to a light theme with strong contrast, visible checkboxes, and a wider splitter handle.

### Files Modified

**`qt_app/app/theme.py`**
- Changed all color tokens from dark to light:
  - `BG_APP`: `#0f1117` → `#f5f6f8`
  - `BG_SIDEBAR`: `#161922` → `#e8eaef`
  - `BG_HEADER`: `#1a1d26` → `#ffffff`
  - `BG_PANEL`: `#1e222d` → `#ffffff`
  - `FG_PRIMARY`: `#e2e4e9` → `#1a1d26`
  - `FG_SECONDARY`: `#9aa0b2` → `#4a5060`
  - (and all other tokens)
- `SPLITTER_HANDLE_WIDTH`: `3` → `6`
- Added vertical splitter handle QSS with border outline
- Added checkbox QSS: 16px indicator with 2px border, accent fill when checked
- Updated `apply_palette()`: light palette colors, white highlight text

---

## Commits (in order)

```
fa56d9d feat: add option picker dialog to Run page
a80f6f7 docs: add option picker planning docs and missing options catalog
dd1ee03 fix: resolve scroll wheel, platform, and input issues
4866525 fix: center main window on primary screen at startup
5f82eab fix: deduplicate advanced group tabs
fce4e11 fix: parse options with curly-brace value placeholders
2eb1fc6 fix: disable scroll wheel on controls, make sections resizable
937a753 fix: add missing QSplitter import
4120296 feat: light theme with better contrast and visible controls
```

---

## Key Design Decisions

1. **Values vs layout separation**: `user_options.json` stores only UI layout (which options, where). Option values flow through existing `profile.raw_args` mechanism — zero changes to `build_argv` or `_settings_from_form`.

2. **VersionedEnvelope pattern**: `UserOptionStore` follows existing store pattern for consistency.

3. **Group name normalization**: All group keys normalized to display names via `_group_display()` before grouping to prevent duplicate tabs.

4. **Wheel guard is absolute**: Wheel events are always consumed on controls, not just when unfocused. This eliminates all accidental value changes.

5. **Splitter replaces fixed heights**: The old `_refit_advanced_panel` forced card heights based on tab content. The splitter lets users control height directly.
