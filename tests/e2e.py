#!/usr/bin/env python3
"""Mikan Focus — E2E test (Playwright, headless Chromium).

Run:
  uv run --with playwright python tests/e2e.py

Covers: timer start/pause/tick, work-session completion (stats/growth/task pomo),
task list CRUD + persistence, week chart pixels, export download, import restore,
reload persistence, zero JS errors. Plus PWA phase (HTTP-served): manifest,
service worker registration, cache population, offline reload, install button.
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

        # 4. timer runs and counts down
        await page.click("#startBtn")
        await page.wait_for_timeout(2600)
        t1 = await page.text_content("#timeDisplay")
        await page.click("#startBtn")  # pause
        results["time_after_2_5s"] = t1
        check("countdown ticks", t1 in ("24:57", "24:58"), t1)
        results["btn_paused"] = await page.text_content("#startBtn")
        check("pause shows つづける", results["btn_paused"] == "つづける", results["btn_paused"])

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

        # 7. persistence across reload
        await page.reload()
        await page.wait_for_timeout(400)
        results["task_count_reload"] = await page.locator(".task-item").count()
        results["stat_total_reload"] = await page.text_content("#statTotal")
        check("tasks persisted", results["task_count_reload"] == 2, str(results["task_count_reload"]))
        check("stats persisted", results["stat_total_reload"] == "1", results["stat_total_reload"])

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
            check("export produced backup", backup.get("stats", {}).get("sessionsTotal") == 1, str(backup.get("stats")))
        except Exception as e:  # noqa: BLE001
            results["download_error"] = str(e)
            check("export produced backup", False, str(e))

        # 9. import restores a crafted backup
        crafted = {
            "v": 2,
            "settings": {"workMin": 50, "breakMin": 5, "longBreakMin": 15, "cyclesPerLong": 4,
                          "soundOn": False, "notifyOn": True, "autoStartNext": False},
            "stats": {"sessionsTotal": 12, "minutesTotal": 300,
                       "days": {"2026-10-14": {"sessions": 3, "minutes": 75}}},
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

        # 10. reset button
        await page.click("#resetBtn")
        results["time_after_reset"] = await page.text_content("#timeDisplay")
        check("reset -> 50:00 (imported workMin)", results["time_after_reset"] == "50:00", results["time_after_reset"])

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

            # cache populated with app shell
            cache_info = await page2.evaluate(
                """async () => {
                     const keys = await caches.keys();
                     const c = await caches.open('mikan-focus-v1.3');
                     const hit = await c.match('./index.html');
                     return {keys, indexCached: !!hit};
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
