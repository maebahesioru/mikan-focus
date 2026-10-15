#!/usr/bin/env python3
"""Mikan Focus — E2E test (Playwright, headless Chromium).

Run:
  uv run --with playwright python tests/e2e.py

Covers: timer start/pause/tick, work-session completion (stats/growth/task pomo),
task list CRUD + persistence, week chart pixels, export download, import restore,
reload persistence, zero JS errors, achievement badges (v1.10: grid, unlock on
session / goal / memo, toasts, persistence, import recompute), CSV session-log
export (v1.11), v1.12: task rename (✎ inline edit), dark theme (apply / persist /
theme-color), ambient volume 0% = silent, timer state persistence (running &
paused resume across reload, away-finished session completes on load).
Plus PWA phase (HTTP-served): manifest, service worker registration, cache
population, offline reload, install button.
"""
import asyncio
import functools
import http.server
import json
import pathlib
import tempfile
import threading

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent.parent
URL = (HERE / "index.html").as_uri()

results = {}
checks = []


def check(name: str, ok: bool, detail=""):
    checks.append((name, ok, detail))


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "console",
            lambda m: errors.append(f"console.{m.type}: {m.text}")
            if m.type == "error"
            else None,
        )

        await page.goto(URL)
        await page.wait_for_timeout(400)

        # 1. initial render
        results["title"] = await page.title()
        results["time0"] = await page.text_content("#timeDisplay")
        check("initial 25:00", results["time0"] == "25:00", results["time0"])
        check("task list initially empty", await page.locator(".task-item").count() == 0)

        # 1b. v1.10: achievement badges — grid renders, none unlocked yet
        results["badge_items"] = await page.locator(".badge-item").count()
        check("badge grid has 14 badges", results["badge_items"] == 14, str(results["badge_items"]))
        results["badge_unlocked0"] = await page.locator(".badge-item.unlocked").count()
        check("no badges unlocked initially", results["badge_unlocked0"] == 0, str(results["badge_unlocked0"]))
        results["badge_count_text"] = await page.text_content("#badgeCount")
        check("badge counter starts 0/14", results["badge_count_text"] == "たっせい 0/14", results["badge_count_text"])
        results["badge_locked_progress"] = await page.locator(".badge-item").nth(1).text_content()
        check("locked badge shows progress 0/10", "0/10" in results["badge_locked_progress"], results["badge_locked_progress"])

        # 2. add tasks
        await page.fill("#taskInput", "テストタスクA")
        await page.click("#taskAddBtn")
        await page.fill("#taskInput", "テストタスクB")
        await page.press("#taskInput", "Enter")
        results["task_count"] = await page.locator(".task-item").count()
        check("2 tasks added (click + Enter)", results["task_count"] == 2, str(results["task_count"]))
        results["active_line"] = await page.text_content("#activeTaskLine")
        check("first task auto-active", "テストタスクA" in results["active_line"], results["active_line"])

        # 3. switch active task
        await page.locator(".task-item").nth(1).click()
        results["active_line2"] = await page.text_content("#activeTaskLine")
        check("switch to task B", "テストタスクB" in results["active_line2"], results["active_line2"])

        # 3b. v1.12: task rename (✎ inline edit)
        results["t_edit_btns"] = await page.locator(".t-edit").count()
        check("each task has a rename button", results["t_edit_btns"] == 2, str(results["t_edit_btns"]))
        await page.locator(".task-item").nth(0).locator(".t-edit").click()
        await page.wait_for_timeout(250)
        check("rename editor opens", await page.locator("#renameInput").count() == 1)
        results["rename_prefill"] = await page.input_value("#renameInput")
        check("rename field prefilled", results["rename_prefill"] == "テストタスクA", results["rename_prefill"])
        await page.fill("#renameInput", "やめとく")
        await page.press("#renameInput", "Escape")
        await page.wait_for_timeout(250)
        results["rename_cancel"] = await page.evaluate("data.tasks[0].name")
        check("Escape cancels rename", results["rename_cancel"] == "テストタスクA", results["rename_cancel"])
        await page.locator(".task-item").nth(0).locator(".t-edit").click()
        await page.wait_for_timeout(250)
        await page.fill("#renameInput", "テストタスクA改")
        await page.press("#renameInput", "Enter")
        await page.wait_for_timeout(250)
        results["rename_saved"] = await page.evaluate("data.tasks[0].name")
        check("Enter saves the new task name", results["rename_saved"] == "テストタスクA改", results["rename_saved"])
        results["rename_rendered"] = await page.locator(".task-item").nth(0).text_content()
        check("renamed task rendered in list", "テストタスクA改" in results["rename_rendered"], results["rename_rendered"])
        results["rename_active_kept"] = await page.text_content("#activeTaskLine")
        check("rename does not change active task", "テストタスクB" in results["rename_active_kept"], results["rename_active_kept"])

        # 4. timer runs and counts down
        await page.click("#startBtn")
        await page.wait_for_timeout(2600)
        t1 = await page.text_content("#timeDisplay")
        await page.click("#startBtn")  # pause
        results["time_after_2_5s"] = t1
        check("countdown ticks", t1 in ("24:57", "24:58"), t1)
        results["btn_paused"] = await page.text_content("#startBtn")
        check("pause shows つづける", results["btn_paused"] == "つづける", results["btn_paused"])

        # 4b. v1.5: procedural ambient sound engine (rain/waves/fire/noise)
        await page.evaluate("document.querySelector('.settings details').open = true")
        await page.wait_for_timeout(150)
        await page.select_option("#ambientSel", "rain")
        results["ambient_setting"] = await page.evaluate("data.settings.ambient")
        check("ambient setting saved", results["ambient_setting"] == "rain", results["ambient_setting"])
        await page.click("#startBtn")  # resume work timer -> ambient starts
        await page.wait_for_timeout(400)
        results["ambient_playing"] = await page.evaluate("ambient ? ambient.type : null")
        check("ambient plays on work start", results["ambient_playing"] == "rain", str(results["ambient_playing"]))
        await page.locator("#ambientVol").fill("60")
        await page.wait_for_timeout(150)
        results["ambient_vol"] = await page.evaluate("data.settings.ambientVol")
        results["ambient_vol_label"] = await page.text_content("#ambientVolLabel")
        check("volume slider saves + label", abs(results["ambient_vol"] - 0.6) < 1e-9 and results["ambient_vol_label"] == "60%",
              f"{results['ambient_vol']} / {results['ambient_vol_label']}")
        await page.click("#startBtn")  # pause -> ambient stops
        results["ambient_stopped"] = await page.evaluate("ambient === null")
        check("ambient stops on pause", results["ambient_stopped"] is True)

        # 4c. v1.12 fix: volume slider 0% = truly silent (was clamped to 1%)
        await page.locator("#ambientVol").fill("0")
        await page.wait_for_timeout(200)
        results["ambient_vol0"] = await page.evaluate("data.settings.ambientVol")
        check("volume 0% saved as 0", results["ambient_vol0"] == 0, str(results["ambient_vol0"]))
        await page.click("#startBtn")  # start work -> ambient at 0%
        await page.wait_for_timeout(800)  # rain blips fire (every 170ms) — must not throw
        results["ambient_gain0"] = await page.evaluate("ambient ? ambient.gain.gain.value : -1")
        check("ambient is silent at 0%", results["ambient_gain0"] == 0, str(results["ambient_gain0"]))
        await page.click("#startBtn")  # pause
        await page.wait_for_timeout(200)

        # 4d. v1.12: dark theme (light / dark / auto)
        results["theme_default"] = await page.evaluate("data.settings.theme")
        check("theme defaults to light", results["theme_default"] == "light", str(results["theme_default"]))
        results["bg_light"] = await page.evaluate(
            "getComputedStyle(document.querySelector('.card')).backgroundColor")
        await page.select_option("#themeSel", "dark")
        await page.wait_for_timeout(250)
        results["dark_class"] = await page.evaluate("document.body.classList.contains('dark')")
        check("dark theme applies body class", results["dark_class"] is True)
        results["bg_dark"] = await page.evaluate(
            "getComputedStyle(document.querySelector('.card')).backgroundColor")
        check("dark theme changes surfaces", results["bg_light"] != results["bg_dark"],
              f"{results['bg_light']} vs {results['bg_dark']}")
        results["meta_theme_dark"] = await page.get_attribute("meta[name='theme-color']", "content")
        check("theme-color meta switches to dark", results["meta_theme_dark"] == "#1d1a12",
              str(results["meta_theme_dark"]))
        results["theme_saved"] = await page.evaluate("data.settings.theme")
        check("theme persisted in data", results["theme_saved"] == "dark", str(results["theme_saved"]))
        await page.select_option("#themeSel", "light")
        await page.wait_for_timeout(250)
        results["dark_off"] = await page.evaluate("!document.body.classList.contains('dark')")
        check("back to light removes dark class", results["dark_off"] is True)
        results["meta_theme_light"] = await page.get_attribute("meta[name='theme-color']", "content")
        check("theme-color meta back to light", results["meta_theme_light"] == "#f5a623",
              str(results["meta_theme_light"]))

        # 5. complete a work session (fast-forward via script scope)
        await page.evaluate("state.remain = 2; state.lastTick = Date.now() - 3000; tick();")
        await page.wait_for_timeout(300)
        results["mode_after_complete"] = await page.evaluate("state.mode")
        check("mode -> break after work", results["mode_after_complete"] == "break", results["mode_after_complete"])
        results["stat_today"] = await page.text_content("#statToday")
        results["stat_minutes"] = await page.text_content("#statMinutes")
        check("today count = 1", results["stat_today"] == "1", results["stat_today"])
        check("minutes = 25", results["stat_minutes"] == "25", results["stat_minutes"])
        results["taskB_text"] = await page.locator(".task-item").nth(1).text_content()
        check("active task got pomo", "🍊×1" in results["taskB_text"], results["taskB_text"])
        results["tree_stage"] = await page.text_content("#treeStage")
        check("tree grew (sprout)", "芽" in results["tree_stage"], results["tree_stage"])

        # 5c. v1.10: first badge unlocked + toast shown
        results["badges_after_first"] = await page.evaluate("data.badges.join(',')")
        check("first badge unlocked", "first" in results["badges_after_first"], results["badges_after_first"])
        results["badge_toast"] = await page.locator(".badge-toast").count()
        check("unlock toast shown", results["badge_toast"] >= 1, str(results["badge_toast"]))
        results["badge_unlocked1"] = await page.locator(".badge-item.unlocked").count()
        check("1 badge unlocked in grid", results["badge_unlocked1"] == 1, str(results["badge_unlocked1"]))

        # 5b. v1.4: session history log + daily goal counter
        results["log_count"] = await page.locator(".log-item").count()
        check("history log shows 1 entry", results["log_count"] == 1, str(results["log_count"]))
        results["log_first"] = await page.locator(".log-item").nth(0).text_content()
        check("history entry has task B + 25分", "テストタスクB" in results["log_first"] and "25分" in results["log_first"], results["log_first"])
        results["goal_count"] = await page.text_content("#goalCount")
        check("goal counter 1/4", results["goal_count"] == "1/4", results["goal_count"])
        results["goal_streak"] = await page.text_content("#goalStreak")
        check("streak text shown", "集中できた" in results["goal_streak"], results["goal_streak"])

        # 6. week chart drawn (non-transparent pixels) + caption
        px = await page.evaluate(
            """() => { const c=document.getElementById('weekCanvas');
                 const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
                 let n=0; for(let i=3;i<d.length;i+=4){ if(d[i]>0) n++; } return n; }"""
        )
        results["week_pixels"] = px
        check("week chart painted", px > 2000, str(px))
        results["week_caption"] = await page.text_content("#weekCaption")
        check("week caption shows 25分", "25分" in results["week_caption"], results["week_caption"])

        # 6b. v1.4: reach the daily goal (4 sessions) → banner + confetti + goal bar
        await page.evaluate(
            "for (let i = 0; i < 3; i++) { state.mode = 'work'; state.totalSec = 1500; state.remain = 0; complete(); }"
        )
        await page.wait_for_timeout(350)
        results["stat_today_goal"] = await page.text_content("#statToday")
        check("today count = 4 after goal loop", results["stat_today_goal"] == "4", results["stat_today_goal"])
        results["goal_count2"] = await page.text_content("#goalCount")
        check("goal counter 4/4", results["goal_count2"] == "4/4", results["goal_count2"])
        results["goal_banner_shown"] = await page.evaluate(
            "document.getElementById('goalBanner').classList.contains('show')"
        )
        check("goal banner shown", results["goal_banner_shown"] is True)
        results["goal_fill_done"] = await page.evaluate(
            "document.getElementById('goalFill').classList.contains('done')"
        )
        check("goal bar done state", results["goal_fill_done"] is True)
        conf_px = await page.evaluate(
            """() => { const c = document.getElementById('confettiCanvas');
                 const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                 let n = 0; for (let i = 3; i < d.length; i += 4) { if (d[i] > 0) n++; } return n; }"""
        )
        results["confetti_pixels"] = conf_px
        check("confetti painted on goal", conf_px > 0, str(conf_px))
        results["log_count4"] = await page.locator(".log-item").count()
        check("history has 4 entries", results["log_count4"] == 4, str(results["log_count4"]))

        # 6b-2. v1.10: badges unlocked by the goal loop (goal + bloom at growth 50)
        results["badges_after_goal"] = await page.evaluate("data.badges.join(',')")
        check("goal badge unlocked", "goal" in results["badges_after_goal"], results["badges_after_goal"])
        check("bloom badge unlocked (growth 50)", "bloom" in results["badges_after_goal"], results["badges_after_goal"])
        results["badge_unlocked_goal"] = await page.locator(".badge-item.unlocked").count()
        check("3 badges unlocked after goal", results["badge_unlocked_goal"] == 3, str(results["badge_unlocked_goal"]))

        # 6c. v1.6: focus heatmap (15-week calendar)
        hpx = await page.evaluate(
            """() => { const c=document.getElementById('heatCanvas');
                 const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
                 let n=0; for(let i=3;i<d.length;i+=4){ if(d[i]>0) n++; } return n; }"""
        )
        results["heat_pixels"] = hpx
        check("heatmap painted", hpx > 5000, str(hpx))
        results["heat_cells"] = await page.evaluate("heatCells().length")
        check("heatmap covers ~105 days", 100 <= results["heat_cells"] <= 105, str(results["heat_cells"]))
        last_key = await page.evaluate("heatCells().slice(-1)[0].key")
        today_key = await page.evaluate("dayKey()")
        check("heatmap last cell = today", last_key == today_key, f"{last_key} vs {today_key}")
        today_min = await page.evaluate(
            "heatCells().find(c => c.key === dayKey()).minutes"
        )
        check("today cell = 100 min (4 sessions)", today_min == 100, str(today_min))
        results["heat_caption"] = await page.text_content("#heatCaption")
        check("heat caption shows summary", "15週間の合計" in results["heat_caption"], results["heat_caption"])
        # hover: scroll into view, hover a cell -> day detail; leave -> summary back
        await page.evaluate("document.getElementById('heatCanvas').scrollIntoView({block:'center'})")
        await page.wait_for_timeout(300)
        hbox = await page.locator("#heatCanvas").bounding_box()
        hsx = hbox["width"] / 440
        hsy = hbox["height"] / 212
        # cell (col 2, row 3) center in canvas coords: (30+2*24+10, 24+3*24+10) = (88, 106)
        await page.mouse.move(hbox["x"] + 88 * hsx, hbox["y"] + 106 * hsy)
        await page.wait_for_timeout(300)
        results["heat_hover"] = await page.text_content("#heatCaption")
        check("heatmap hover shows a day", "分 / みかん" in (results["heat_hover"] or ""), results["heat_hover"])
        await page.mouse.move(hbox["x"] - 120, hbox["y"] - 120)
        await page.wait_for_timeout(300)
        results["heat_hover_out"] = await page.text_content("#heatCaption")
        check("heatmap hover-out restores summary", "15週間の合計" in (results["heat_hover_out"] or ""), results["heat_hover_out"])

        # 6d. v1.7: zen mode (集中モード)
        check("zen off by default", await page.evaluate("!document.body.classList.contains('zen')"))
        await page.click("#zenBtn")
        await page.wait_for_timeout(250)
        check("zen toggles on via button", await page.evaluate("document.body.classList.contains('zen')"))
        hidden = await page.evaluate(
            """() => ['.task-card', '.stats', '.goal-card', '.badge-card', '.log-card', '.settings']
                 .map(s => { const el = document.querySelector(s);
                             return s + '=' + (el ? getComputedStyle(el).display === 'none' : 'missing'); })
                 .join(',')"""
        )
        check("zen hides side cards", all(p.endswith("=true") for p in hidden.split(",")), hidden)
        results["zen_btn_label"] = await page.text_content("#zenBtn")
        check("zen button label flips", "終了" in results["zen_btn_label"], results["zen_btn_label"])
        await page.keyboard.press("z")
        await page.wait_for_timeout(250)
        check("zen toggles off via Z key", await page.evaluate("!document.body.classList.contains('zen')"))
        await page.click("#zenBtn")
        await page.wait_for_timeout(150)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(250)
        check("Escape exits zen", await page.evaluate("!document.body.classList.contains('zen')"))

        # 6e. v1.8: +5 min extend
        r0 = await page.evaluate("state.remain")
        s0 = await page.evaluate("state.totalSec")
        await page.click("#extendBtn")
        await page.wait_for_timeout(250)
        r1 = await page.evaluate("state.remain")
        s1 = await page.evaluate("state.totalSec")
        check("extend adds 300s to remain+total", r1 == r0 + 300 and s1 == s0 + 300, f"{r0}->{r1} / {s0}->{s1}")
        d0 = await page.text_content("#timeDisplay")
        await page.keyboard.press("+")
        await page.wait_for_timeout(250)
        r2 = await page.evaluate("state.remain")
        d1 = await page.text_content("#timeDisplay")
        check("extend via + key", r2 == r1 + 300, f"{r1} -> {r2}")
        check("display updated after extends", d0 != d1, f"{d0} -> {d1}")

        # 6f. v1.9: focus presets + session notes
        await page.evaluate("document.querySelector('.settings details').open = true")
        await page.wait_for_timeout(150)
        await page.evaluate("state.running = false; setMode('work')")
        await page.wait_for_timeout(150)
        results["preset_count"] = await page.locator(".preset-btn").count()
        check("4 preset buttons", results["preset_count"] == 4, str(results["preset_count"]))
        await page.click(".preset-btn[data-min='15']")
        await page.wait_for_timeout(250)
        results["preset_workMin"] = await page.input_value("#workMin")
        results["preset_pressed"] = await page.get_attribute(".preset-btn[data-min='15']", "aria-pressed")
        results["preset_display"] = await page.text_content("#timeDisplay")
        check("preset 15 sets workMin", results["preset_workMin"] == "15", results["preset_workMin"])
        check("preset 15 aria-pressed", results["preset_pressed"] == "true", str(results["preset_pressed"]))
        check("display follows preset (15:00)", results["preset_display"] == "15:00", results["preset_display"])
        await page.click(".preset-btn[data-min='25']")
        await page.wait_for_timeout(250)
        results["preset_workMin2"] = await page.input_value("#workMin")
        results["preset_pressed2"] = await page.get_attribute(".preset-btn[data-min='15']", "aria-pressed")
        check("preset back to 25", results["preset_workMin2"] == "25", results["preset_workMin2"])
        check("aria-pressed clears from 15", results["preset_pressed2"] == "false", str(results["preset_pressed2"]))
        # notes: every entry offers +メモ; save persists to data.history[0]
        results["note_add_btns"] = await page.locator(".log-note-add").count()
        check("entries offer +メモ button", results["note_add_btns"] == 4, str(results["note_add_btns"]))
        await page.locator(".log-note-add").first.click()
        await page.wait_for_timeout(250)
        check("note editor opens", await page.locator("#noteInput").count() == 1)
        await page.fill("#noteInput", "E2Eテストのメモ")
        await page.click("#noteSaveBtn")
        await page.wait_for_timeout(250)
        results["note_saved"] = await page.evaluate("data.history[0].note")
        check("note saved to history[0]", results["note_saved"] == "E2Eテストのメモ", str(results["note_saved"]))
        # v1.10: saving a memo unlocks the note badge (+ toast)
        results["badge_note"] = await page.evaluate("data.badges.includes('note')")
        check("note badge unlocked after memo", results["badge_note"] is True)
        results["badge_toast_note"] = await page.locator(".badge-toast").count()
        check("toast shown for note badge", results["badge_toast_note"] >= 1, str(results["badge_toast_note"]))
        results["note_text"] = await page.locator(".log-note").first.text_content()
        check("note rendered with 📝", "📝 E2Eテストのメモ" in (results["note_text"] or ""), str(results["note_text"]))
        await page.locator(".log-note").first.click()
        await page.wait_for_timeout(250)
        results["note_reopen"] = await page.input_value("#noteInput")
        check("edit reopens with existing note", results["note_reopen"] == "E2Eテストのメモ", str(results["note_reopen"]))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(250)
        results["note_escape"] = await page.evaluate("data.history[0].note")
        check("escape keeps note intact", results["note_escape"] == "E2Eテストのメモ", str(results["note_escape"]))

        # 7. persistence across reload
        await page.reload()
        await page.wait_for_timeout(400)
        results["task_count_reload"] = await page.locator(".task-item").count()
        results["stat_total_reload"] = await page.text_content("#statTotal")
        check("tasks persisted", results["task_count_reload"] == 2, str(results["task_count_reload"]))
        check("stats persisted", results["stat_total_reload"] == "4", results["stat_total_reload"])
        results["log_count_reload"] = await page.locator(".log-item").count()
        check("history persisted (4 entries)", results["log_count_reload"] == 4, str(results["log_count_reload"]))
        results["goal_count_reload"] = await page.text_content("#goalCount")
        check("goal persisted 4/4", results["goal_count_reload"] == "4/4", results["goal_count_reload"])
        results["note_reload"] = await page.evaluate("data.history[0] && data.history[0].note")
        check("note persisted after reload", results["note_reload"] == "E2Eテストのメモ", str(results["note_reload"]))
        results["note_render_reload"] = await page.locator(".log-note").count()
        check("note rendered after reload", results["note_render_reload"] >= 1, str(results["note_render_reload"]))
        # v1.10: badges persisted across reload
        results["badges_reload"] = await page.evaluate("data.badges.length")
        check("badges persisted after reload (4)", results["badges_reload"] == 4, str(results["badges_reload"]))
        results["badge_count_reload"] = await page.text_content("#badgeCount")
        check("badge counter persisted 4/14", results["badge_count_reload"] == "たっせい 4/14", results["badge_count_reload"])
        results["rename_reload"] = await page.locator(".task-item").nth(0).text_content()
        check("renamed task persisted after reload", "テストタスクA改" in results["rename_reload"], results["rename_reload"])

        # 8. export download (settings <details> must be open first)
        await page.evaluate("document.querySelector('.settings details').open = true")
        await page.wait_for_timeout(150)
        try:
            async with page.expect_download(timeout=5000) as dl_info:
                await page.click("#exportBtn")
            dl = await dl_info.value
            results["download_name"] = dl.suggested_filename
            path = await dl.path()
            backup = json.loads(pathlib.Path(path).read_text())
            results["backup_tasks"] = len(backup.get("tasks", []))
            check("export produced backup", backup.get("stats", {}).get("sessionsTotal") == 4, str(backup.get("stats")))
            results["backup_history"] = len(backup.get("history", []))
            check("export includes history", results["backup_history"] == 4, str(results["backup_history"]))
            results["backup_note"] = (backup.get("history") or [{}])[0].get("note")
            check("export includes note", results["backup_note"] == "E2Eテストのメモ", str(results["backup_note"]))
        except Exception as e:  # noqa: BLE001
            results["download_error"] = str(e)
            check("export produced backup", False, str(e))

        # 8b. v1.11: CSV export of the session log
        try:
            async with page.expect_download(timeout=5000) as dl2_info:
                await page.click("#csvBtn")
            dl2 = await dl2_info.value
            results["csv_name"] = dl2.suggested_filename
            csv_path = await dl2.path()
            csv_text = pathlib.Path(csv_path).read_text(encoding="utf-8-sig")
            csv_lines = [l for l in csv_text.splitlines() if l.strip()]
            results["csv_lines"] = len(csv_lines)
            check("CSV download named mikan-focus-log-*.csv",
                  results["csv_name"].startswith("mikan-focus-log-") and results["csv_name"].endswith(".csv"),
                  str(results["csv_name"]))
            check("CSV has header + 4 session rows", results["csv_lines"] == 5, str(results["csv_lines"]))
            check("CSV header row", csv_lines[0] == "date,time,minutes,task,note", csv_lines[0] if csv_lines else "empty")
            check("CSV row carries task B + 25 min",
                  any("テストタスクB" in l and ",25," in l for l in csv_lines[1:]), str(csv_lines[1:3]))
            check("CSV row carries the note", any("E2Eテストのメモ" in l for l in csv_lines[1:]), str(csv_lines[1:2]))
        except Exception as e:  # noqa: BLE001
            results["csv_error"] = str(e)
            check("CSV download works", False, str(e)[:120])

        # 9. import restores a crafted backup (v2 → v3 migration path)
        today_key = await page.evaluate("dayKey()")
        crafted = {
            "v": 2,
            "settings": {"workMin": 50, "breakMin": 5, "longBreakMin": 15, "cyclesPerLong": 4,
                          "soundOn": False, "notifyOn": True, "autoStartNext": False},
            "stats": {"sessionsTotal": 12, "minutesTotal": 300,
                       "days": {today_key: {"sessions": 3, "minutes": 75}}},
            "cycleCount": 3, "growth": 37.5,
            "tasks": [{"id": "x1", "name": "復元タスク", "pomos": 5}],
            "activeTaskId": "x1",
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(crafted, f)
            tmp = f.name
        await page.set_input_files("#importFile", tmp)
        await page.wait_for_timeout(700)
        results["import_workMin"] = await page.input_value("#workMin")
        results["import_statTotal"] = await page.text_content("#statTotal")
        results["import_task"] = await page.locator(".task-item").nth(0).text_content()
        check("import restored settings", results["import_workMin"] == "50", results["import_workMin"])
        check("import restored stats", results["import_statTotal"] == "12", results["import_statTotal"])
        check("import restored tasks", "復元タスク" in results["import_task"], results["import_task"])
        results["log_empty_after_import"] = await page.evaluate(
            "document.getElementById('logEmpty').style.display !== 'none'"
        )
        check("log empty after v2 import (no history)", results["log_empty_after_import"] is True)
        results["goal_count_import"] = await page.text_content("#goalCount")
        check("goal counter from imported day 3/4", results["goal_count_import"] == "3/4", results["goal_count_import"])
        # v1.10: import recomputes badges from imported stats (quietly, no toasts)
        results["badges_import"] = await page.evaluate("data.badges.slice().sort().join(',')")
        check("import recomputed badges (first,s10)", results["badges_import"] == "first,s10", results["badges_import"])
        results["badge_count_import"] = await page.text_content("#badgeCount")
        check("import badge counter 2/14", results["badge_count_import"] == "たっせい 2/14", results["badge_count_import"])

        # 10. reset button
        await page.click("#resetBtn")
        results["time_after_reset"] = await page.text_content("#timeDisplay")
        check("reset -> 50:00 (imported workMin)", results["time_after_reset"] == "50:00", results["time_after_reset"])

        # 11. v1.12: timer state persistence (reload resumes the session)
        await page.click("#startBtn")
        await page.wait_for_timeout(1300)
        results["run_before_reload"] = await page.evaluate("state.running")
        r_before = await page.evaluate("state.remain")
        check("timer running before reload", results["run_before_reload"] is True)
        await page.reload()
        await page.wait_for_timeout(500)
        results["run_after_reload"] = await page.evaluate("state.running")
        check("timer still running after reload", results["run_after_reload"] is True)
        r_after = await page.evaluate("state.remain")
        results["remain_continuity"] = [r_before, r_after]
        check("remaining time continued (no reset to 50:00)",
              r_after <= r_before and r_after >= r_before - 4, f"{r_before} -> {r_after}")
        results["btn_after_reload"] = await page.text_content("#startBtn")
        check("start button shows 一時停止 after resume", results["btn_after_reload"] == "一時停止",
              results["btn_after_reload"])
        # paused state also survives a reload
        await page.click("#startBtn")
        await page.wait_for_timeout(300)
        r_paused = await page.evaluate("state.remain")
        await page.reload()
        await page.wait_for_timeout(500)
        results["run_after_pause_reload"] = await page.evaluate("state.running")
        r_after_pause = await page.evaluate("state.remain")
        check("paused state stays paused after reload", results["run_after_pause_reload"] is False)
        check("paused remaining time kept", r_after_pause == r_paused, f"{r_paused} -> {r_after_pause}")
        results["paused_btn"] = await page.text_content("#startBtn")
        check("start button shows つづける when restored paused", results["paused_btn"] == "つづける",
              results["paused_btn"])
        # 11b. phase that finished while away is completed on load (mikan awarded)
        await page.evaluate(
            "data.timer = { mode: 'work', remain: 1, totalSec: 1500, running: true, at: Date.now() - 6000 };"
            " saveData();"
        )
        await page.reload()
        await page.wait_for_timeout(600)
        results["away_stat"] = await page.text_content("#statTotal")
        check("away-finished session awarded (12 -> 13)", results["away_stat"] == "13", results["away_stat"])
        results["away_mode"] = await page.evaluate("state.mode")
        check("phase advanced after away-complete (cycle 4 -> long break)", results["away_mode"] == "long",
              results["away_mode"])
        results["away_log"] = await page.locator(".log-item").nth(0).text_content()
        check("log entry for away-completed session", "復元タスク" in results["away_log"] and "+25分" in results["away_log"],
              results["away_log"])
        results["away_goal"] = await page.text_content("#goalCount")
        check("away-complete counted toward the daily goal (4/4)", results["away_goal"] == "4/4", results["away_goal"])
        # 11c. theme choice persists across reload
        await page.evaluate("document.querySelector('.settings details').open = true")
        await page.select_option("#themeSel", "dark")
        await page.wait_for_timeout(200)
        await page.reload()
        await page.wait_for_timeout(500)
        results["dark_reload"] = await page.evaluate("document.body.classList.contains('dark')")
        check("dark theme persisted after reload", results["dark_reload"] is True)
        results["dark_reload_bg"] = await page.evaluate(
            "getComputedStyle(document.querySelector('.card')).backgroundColor")
        check("dark surface applied on load", results["dark_reload_bg"] == "rgb(42, 37, 27)", results["dark_reload_bg"])

        results["js_errors"] = errors
        check("no JS errors", len(errors) == 0, "; ".join(errors[:3]))

        # ===== PWA phase (HTTP-served) =====
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE))
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 3971), handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            ctx2 = await browser.new_context()
            page2 = await ctx2.new_page()
            errors2 = []
            page2.on("pageerror", lambda e: errors2.append(str(e)))
            await page2.goto("http://127.0.0.1:3971/index.html")
            await page2.wait_for_timeout(600)

            # manifest tag + fetch
            check("manifest link tag present", await page2.locator('link[rel="manifest"]').count() == 1)
            man = await page2.evaluate(
                "fetch('manifest.json').then(r => r.ok ? r.json() : null).catch(() => null)"
            )
            results["manifest_name"] = (man or {}).get("name", "")
            check("manifest fetchable + named", bool(man and "みかん" in man.get("name", "")), str(man and man.get("name")))

            # service worker registration (ready resolves => active)
            sw_state = await page2.evaluate(
                "navigator.serviceWorker.ready.then(r => r.active ? 'active' : 'inactive').catch(e => 'err:' + e)"
            )
            results["sw_state"] = sw_state
            check("service worker active", sw_state == "active", str(sw_state))

            # cache populated with app shell (version-agnostic: newest mikan-focus-* cache)
            cache_info = await page2.evaluate(
                """async () => {
                     const keys = await caches.keys();
                     const key = keys.filter((k) => k.startsWith('mikan-focus-')).sort().pop();
                     const c = key ? await caches.open(key) : null;
                     const hit = c ? await c.match('./index.html') : null;
                     return {keys, key, indexCached: !!hit};
                   }"""
            )
            results["cache_keys"] = cache_info["keys"]
            check("cache populated (index.html)", cache_info["indexCached"], str(cache_info))

            # install button present but hidden (no beforeinstallprompt in headless)
            check("install button hidden by default", await page2.locator("#installBtn").count() == 1
                  and await page2.locator("#installBtn").is_hidden())

            # offline reload served from SW cache
            await ctx2.set_offline(True)
            try:
                await page2.reload(timeout=8000)
                await page2.wait_for_timeout(500)
                title_off = await page2.title()
                time_off = await page2.text_content("#timeDisplay")
                results["offline_title"] = title_off
                check("offline reload works (SW cache)", "みかん" in title_off and time_off == "25:00",
                      f"{title_off} / {time_off}")
            except Exception as e:  # noqa: BLE001
                check("offline reload works (SW cache)", False, str(e)[:120])
            finally:
                await ctx2.set_offline(False)
            await ctx2.close()
        finally:
            httpd.shutdown()

        await browser.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))
    print()
    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if not ok else ""))
    print(f"\n{passed}/{len(checks)} passed")
    raise SystemExit(0 if passed == len(checks) else 1)


asyncio.run(main())
