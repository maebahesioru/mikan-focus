# Mikan Focus 🍊⏱️

**集中するたび、みかんの木が育つ。**
*Focus, and watch your mikan tree grow.*

A tiny pomodoro timer with a pixel-art mikan tree that grows as you complete focus sessions. Built for **Hack Club Embassy**.

![screenshot](screenshot.png)

## How it works

- **25分の集中タイム** → 完了すると「みかんが実る」（セッション数カウント）
- **5分の休憩タイム** → 自動で切り替え
- 集中セッションを重ねるごとに、みかんの木が成長する（種 → 芽 → 若木 → 花 → 実 → 鈴なり）
- 8セッションで木が満開になる
- 完了時は Web Audio のやさしいチャイム + 通知

## Features

- 🍅 Pomodoro timer (work/break/long-break, lengths configurable, 4-cycle long break)
- ⏱ Sticky timer — the running (or paused) phase is saved, so a reload or a closed tab resumes exactly where it left off; a phase that finished while you were away completes on load
- 🌧 Ambient sounds — procedural rain / waves / campfire / brown noise (Web Audio, zero audio files) with a volume slider; plays during focus sessions
- 🎯 Daily goal — set a mikan target for the day, watch the progress bar fill (streak counter 🔥 included)
- 📖 Session log — every finished focus session is recorded (time, task, minutes)
- 📝 Session notes — attach a one-line memo to any session in the log (edit inline, saved with your data, included in backups)
- 🔍 Log filter — narrow the session log down to a single task (or「タスクなし」) with the dropdown in the log card
- 🔎 Log search — a search box narrows the log by task name or memo text (case-insensitive substring, combines with the task filter)
- 🧮 Log summary — the log card shows the entry count and total focus minutes the current filter + search covers
- ↕️ Task reorder — move tasks up / down with ↑/↓ buttons (disabled at the ends, order is saved)
- 📷 Tree PNG export — save your mikan tree as a 2x pixel-perfect PNG (caption: total sessions / today's mikans / date)
- ⌨️ Shortcut help — press `?` (or the ⌨ button) for an overlay of every keyboard shortcut; `Esc` / backdrop / とじる closes it
- 🏅 Achievement badges — 14 badges to collect (sessions, total minutes, streaks, tree growth, daily goal, memos, night/morning focus); locked ones show live progress, and unlocking pops a toast; saved with your data
- ⚡ Focus presets — 15/25/45/60分 quick buttons to set the focus length in one tap
- 📋 Task list — each focus session adds a 🍊 to the active task (saved locally); rename any task in place with ✎
- 🌳 Pixel-art mikan tree drawn on canvas — 6 growth stages
- 🎨 Theme — light / dark / auto (follows your OS), remembered with your data
- 📊 Stats: sessions today / total / focus minutes + 7-day bar chart (canvas)
- 💾 Backup export / import (JSON) — your data stays yours
- 📊 CSV export — write the whole session log (date, time, minutes, task, note) out as a spreadsheet-friendly CSV (BOM, Excel-safe)
- 🔔 Chime (Web Audio, no files) + desktop notifications
- 🎉 Pixel confetti when you hit your daily goal or the tree is fully grown
- 📲 PWA: installable (own icon + manifest) and works fully offline via a service worker
- ⌨️ Keyboard shortcuts: Space = start/pause, R = reset, S = skip, Z = zen mode, ＋ = extend 5min, ? = shortcut help
- ♿ Accessibility: `role="timer"`, `aria-live` mode/stage announcements
- 📱 Responsive, works offline
- 📄 Single HTML file — no build, no dependencies

## Run it

Open `index.html` in a browser, or:

```bash
python3 -m http.server 3964
```

## Test

E2E suite (Playwright, headless Chromium) — 165 checks covering timer, tasks (incl. rename), chart, persistence, export/import, daily goal + confetti, session log, session notes, focus presets, achievement badges (grid, unlocks, toasts, persistence, import recompute), CSV session-log export, ambient sound engine (incl. 0% = silent), dark theme (apply / persist / theme-color), timer-state persistence (running & paused resume across reload, away-finished session completes on load), shortcut help overlay (? key / button / Esc / input guard), log filter by task (options, per-task, no-task, empty hint), tree PNG export (download / signature / dimensions), log search (task/note, case-insensitive, filter combo, query hint, clear button), log summary line, task reorder (edge states, persistence, active task kept), PWA (manifest, service worker, offline reload):

```bash
uv run --with playwright python tests/e2e.py
```

## Notes

- All data stays in your browser (localStorage).
- The tree growth is cumulative — 8 sessions = fully grown.
- Task 🍊 counts start from when you create the task (sessions before v1.2 had no task).

Made for [Hack Club Embassy](https://embassy.hackclub.com/).

## Changelog

- **v1.14** — きろく検索 + きろくサマリー + タスク並べ替え: the session log gains a search box that filters by task name or memo (case-insensitive substring; combines with the task-filter dropdown; a no-match query shows its own hint, and ✕ / Esc clears it); the log card now reports how many entries and total minutes the current filter + search covers (しぼりこみ中 / ぜんぶで); tasks can be reordered with ↑/↓ buttons (disabled at the ends, order persists, the active task is untouched); E2E suite extended to 165 checks
- **v1.13** — きろくフィルタ + ショートカットヘルプ + 木のPNG保存: the session log can be filtered down to a single task (or「タスクなし」) from a dropdown (options track your tasks + history, with a hint when a task has no sessions yet); press `?` or the ⌨ button for a keyboard-shortcut help overlay (closed by `Esc`, a backdrop click, or とじる); the mikan tree can be saved as a 2x pixel-perfect PNG with a caption (total sessions / today's mikans / date); test suite hardened — the 朝/深夜 badges depend on the wall-clock hour, so the E2E expectations now account for it; E2E suite extended to 148 checks
- **v1.12** — タイマー復元 + タスク名変更 + ダークテーマ: the running (or paused) timer now survives a reload — it resumes where it left off, and a phase that finished while you were away completes on load (mikan awarded); tasks can be renamed in place with the ✎ button; a theme picker adds light / dark / auto (follows your OS); two fixes — countdown seconds no longer drift over long sessions, and the ambient volume slider at 0% is truly silent (it used to keep playing at 1%); E2E suite extended to 129 checks
- **v1.11** — きろくCSV書き出し: export the full session log as a CSV (date / time / minutes / task / note — BOM'd for Excel, quotes escaped), straight from the settings panel; E2E suite extended to 99 checks
- **v1.10** — 実績バッジ: 14 collectible badges (first mikan / 10 / 50 / 100 sessions, 500 / 1000 total minutes, 3 / 7-day streaks, tree bloom + full bloom, daily goal, first memo, night owl + early bird) derived from your stats with live progress on locked ones and a toast when one unlocks; persisted in your data and recomputed on import; E2E suite extended to 94 checks
- **v1.9** — セッションメモ + 集中時間プリセット: every session-log entry can carry a one-line note (📝 — add / edit inline, saved with your data and included in backups), and quick preset buttons (15/25/45/60分) set the focus length in one tap; E2E suite extended to 78 checks
- **v1.8** — セッション延長: a ＋5分 button (and `+` key) extends the current phase by five minutes — the recorded session minutes include the extension; E2E suite extended to 63 checks
- **v1.7** — 集中モード（Zen mode）: one click (or `Z`) hides the tasks, stats, charts, log and settings so only the timer and the tree stay on screen; `Esc` exits; E2E suite extended to 60 checks
- **v1.6** — きろくカレンダー: a 15-week focus heatmap (GitHub-contribution style) with per-day color levels, month labels, today outline, and hover details (day → minutes / mikans); E2E suite extended to 54 checks
- **v1.5** — procedural ambient sounds: rain / waves / campfire / brown noise generated entirely in Web Audio (no audio files), volume slider, plays while a focus session runs; E2E suite extended to 47 checks
- **v1.4** — daily goal (configurable target + progress bar + 🔥 streak), session log (recent focus sessions with task names), pixel confetti celebration when the goal is reached or the tree is fully grown; storage v3 (with v2 backup import migration); E2E suite extended to 43 checks
- **v1.3** — PWA: installable app (manifest + generated icons via `tools/make_icons.py`), offline support with a service worker (cache-first app shell), install button; E2E suite extended to 28 checks (incl. offline reload)
- **v1.2** — task list with per-task mikan counts, 7-day focus chart, backup export/import, a11y improvements, E2E tests
- **v1.1** — long-break cycles, keyboard shortcuts, tab title countdown, expanded settings, v1→v2 storage migration
- **v1.0** — initial release
