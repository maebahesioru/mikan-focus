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
- 🌧 Ambient sounds — procedural rain / waves / campfire / brown noise (Web Audio, zero audio files) with a volume slider; plays during focus sessions
- 🎯 Daily goal — set a mikan target for the day, watch the progress bar fill (streak counter 🔥 included)
- 📖 Session log — every finished focus session is recorded (time, task, minutes)
- 📋 Task list — each focus session adds a 🍊 to the active task (saved locally)
- 🌳 Pixel-art mikan tree drawn on canvas — 6 growth stages
- 📊 Stats: sessions today / total / focus minutes + 7-day bar chart (canvas)
- 💾 Backup export / import (JSON) — your data stays yours
- 🔔 Chime (Web Audio, no files) + desktop notifications
- 🎉 Pixel confetti when you hit your daily goal or the tree is fully grown
- 📲 PWA: installable (own icon + manifest) and works fully offline via a service worker
- ⌨️ Keyboard shortcuts: Space = start/pause, R = reset, S = skip
- ♿ Accessibility: `role="timer"`, `aria-live` mode/stage announcements
- 📱 Responsive, works offline
- 📄 Single HTML file — no build, no dependencies

## Run it

Open `index.html` in a browser, or:

```bash
python3 -m http.server 3964
```

## Test

E2E suite (Playwright, headless Chromium) — 47 checks covering timer, tasks, chart, persistence, export/import, daily goal + confetti, session log, ambient sound engine, PWA (manifest, service worker, offline reload):

```bash
uv run --with playwright python tests/e2e.py
```

## Notes

- All data stays in your browser (localStorage).
- The tree growth is cumulative — 8 sessions = fully grown.
- Task 🍊 counts start from when you create the task (sessions before v1.2 had no task).

Made for [Hack Club Embassy](https://embassy.hackclub.com/).

## Changelog

- **v1.8** — セッション延長: a ＋5分 button (and `+` key) extends the current phase by five minutes — the recorded session minutes include the extension; E2E suite extended to 63 checks
- **v1.7** — 集中モード（Zen mode）: one click (or `Z`) hides the tasks, stats, charts, log and settings so only the timer and the tree stay on screen; `Esc` exits; E2E suite extended to 60 checks
- **v1.6** — きろくカレンダー: a 15-week focus heatmap (GitHub-contribution style) with per-day color levels, month labels, today outline, and hover details (day → minutes / mikans); E2E suite extended to 54 checks
- **v1.5** — procedural ambient sounds: rain / waves / campfire / brown noise generated entirely in Web Audio (no audio files), volume slider, plays while a focus session runs; E2E suite extended to 47 checks
- **v1.4** — daily goal (configurable target + progress bar + 🔥 streak), session log (recent focus sessions with task names), pixel confetti celebration when the goal is reached or the tree is fully grown; storage v3 (with v2 backup import migration); E2E suite extended to 43 checks
- **v1.3** — PWA: installable app (manifest + generated icons via `tools/make_icons.py`), offline support with a service worker (cache-first app shell), install button; E2E suite extended to 28 checks (incl. offline reload)
- **v1.2** — task list with per-task mikan counts, 7-day focus chart, backup export/import, a11y improvements, E2E tests
- **v1.1** — long-break cycles, keyboard shortcuts, tab title countdown, expanded settings, v1→v2 storage migration
- **v1.0** — initial release
