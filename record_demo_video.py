"""
Automated Screen Recording Generator for Meeting Intelligence.
Produces a professional 720p 30fps H.264 MP4 video demonstration with visible natural mouse cursor,
clicks, typing, navigation, and complete feature coverage.
"""

import os
import sys
import time
import math
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
RECORDINGS_DIR = Path("/Users/kalmin/projects/meeting_intelligence/recordings")
RAW_DIR = RECORDINGS_DIR / "raw"
FINAL_VIDEO_PATH = RECORDINGS_DIR / "meeting_intelligence_demo.mp4"

RAW_DIR.mkdir(parents=True, exist_ok=True)

# Custom Cursor & Ripple JS to inject into all pages
CURSOR_INJECTION_JS = """
(() => {
    if (document.getElementById('demo-cursor-pointer')) return;

    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor-pointer';
    cursor.style.position = 'fixed';
    cursor.style.top = '0px';
    cursor.style.left = '0px';
    cursor.style.width = '20px';
    cursor.style.height = '20px';
    cursor.style.borderRadius = '50%';
    cursor.style.backgroundColor = 'rgba(99, 102, 241, 0.9)';
    cursor.style.border = '2px solid #ffffff';
    cursor.style.boxShadow = '0 0 12px rgba(99, 102, 241, 0.8), 0 2px 6px rgba(0,0,0,0.5)';
    cursor.style.pointerEvents = 'none';
    cursor.style.zIndex = '999999';
    cursor.style.transform = 'translate(-50%, -50%)';
    cursor.style.transition = 'transform 0.08s ease, width 0.15s ease, height 0.15s ease, background-color 0.15s ease';
    document.body.appendChild(cursor);

    window.__currentMousePos = { x: 100, y: 100 };

    window.addEventListener('mousemove', (e) => {
        window.__currentMousePos = { x: e.clientX, y: e.clientY };
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });

    window.addEventListener('mousedown', (e) => {
        cursor.style.transform = 'translate(-50%, -50%) scale(0.75)';
        cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.95)';

        // Create ripple effect
        const ripple = document.createElement('div');
        ripple.style.position = 'fixed';
        ripple.style.left = e.clientX + 'px';
        ripple.style.top = e.clientY + 'px';
        ripple.style.width = '10px';
        ripple.style.height = '10px';
        ripple.style.borderRadius = '50%';
        ripple.style.border = '2px solid rgba(129, 140, 248, 0.9)';
        ripple.style.transform = 'translate(-50%, -50%) scale(1)';
        ripple.style.pointerEvents = 'none';
        ripple.style.zIndex = '999998';
        ripple.style.transition = 'transform 0.4s ease-out, opacity 0.4s ease-out';
        document.body.appendChild(ripple);

        requestAnimationFrame(() => {
            ripple.style.transform = 'translate(-50%, -50%) scale(4.5)';
            ripple.style.opacity = '0';
        });

        setTimeout(() => ripple.remove(), 450);
    });

    window.addEventListener('mouseup', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1)';
        cursor.style.backgroundColor = 'rgba(99, 102, 241, 0.9)';
    });
})();
"""


class RecordingDirector:
    def __init__(self, page):
        self.page = page
        self.current_x = 200
        self.current_y = 200

    def inject_cursor(self):
        try:
            self.page.evaluate(CURSOR_INJECTION_JS)
        except Exception:
            pass

    def ease_in_out(self, t):
        return t * t * (3.0 - 2.0 * t)

    def move_to(self, target_x, target_y, steps=20, duration=0.35):
        self.inject_cursor()
        start_x = self.current_x
        start_y = self.current_y
        step_delay = duration / steps

        for i in range(1, steps + 1):
            t = i / float(steps)
            eased_t = self.ease_in_out(t)
            curr_x = start_x + (target_x - start_x) * eased_t
            curr_y = start_y + (target_y - start_y) * eased_t
            self.page.mouse.move(curr_x, curr_y)
            time.sleep(step_delay)

        self.current_x = target_x
        self.current_y = target_y

    def hover_element(self, selector, duration=0.3):
        self.inject_cursor()
        loc = self.page.locator(selector).first
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        if box:
            target_x = box['x'] + box['width'] / 2.0
            target_y = box['y'] + box['height'] / 2.0
            self.move_to(target_x, target_y, duration=duration)
            time.sleep(0.15)

    def click_element(self, selector, pre_delay=0.15, post_delay=0.3):
        self.inject_cursor()
        loc = self.page.locator(selector).first
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        if box:
            target_x = box['x'] + box['width'] / 2.0
            target_y = box['y'] + box['height'] / 2.0
            self.move_to(target_x, target_y, duration=0.3)
            time.sleep(pre_delay)
            self.page.mouse.down()
            time.sleep(0.08)
            self.page.mouse.up()
            time.sleep(post_delay)
        else:
            loc.click()

    def type_text(self, selector, text, delay=0.03):
        self.click_element(selector)
        time.sleep(0.1)
        self.page.locator(selector).first.fill("")
        for char in text:
            self.page.keyboard.type(char)
            time.sleep(delay)
        time.sleep(0.2)

    def smooth_scroll(self, scroll_delta, steps=15, step_delay=0.02):
        delta_per_step = scroll_delta / steps
        for _ in range(steps):
            self.page.mouse.wheel(0, delta_per_step)
            time.sleep(step_delay)
        time.sleep(0.3)


def execute_recording():
    print("Initializing Playwright Screen Recording Session...")

    # First reseed database to ensure clean baseline demo state
    subprocess.run(["python", "manage.py", "seed_demo_data"], check=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": 1280, "height": 720}
        )

        page = context.new_page()
        director = RecordingDirector(page)

        page.on("load", lambda: director.inject_cursor())

        # -------------------------------------------------------------
        # Scene 1: Authentication & Quick Demo Sign In (0:00 - 0:08)
        # -------------------------------------------------------------
        print("Recording Scene 1: Authentication...")
        page.goto(f"{BASE_URL}/login/")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(0.8)

        director.hover_element("h2:has-text('Meeting Intelligence')")
        time.sleep(0.4)
        director.hover_element("button:has-text('Sign In as Sarah Lin')")
        time.sleep(0.3)
        director.click_element("button:has-text('Sign In as Sarah Lin')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        # -------------------------------------------------------------
        # Scene 2: Executive Dashboard Exploration (0:08 - 0:30)
        # -------------------------------------------------------------
        print("Recording Scene 2: Executive Dashboard...")
        director.hover_element("text=Upcoming Meetings")
        time.sleep(0.4)
        director.hover_element("text=Pending Approvals")
        time.sleep(0.4)
        director.hover_element("text=Active Tasks (Asana)")
        time.sleep(0.4)
        director.hover_element("text=Overdue Tasks")
        time.sleep(0.5)

        # Hover over Upcoming Meetings
        director.smooth_scroll(180, steps=10)
        director.hover_element("h2:has-text('Upcoming Client Meetings')")
        time.sleep(0.4)
        director.hover_element("h3:has-text('Acme HealthTech')")
        time.sleep(0.4)

        # Hover over Pending Approvals & Evidence Quote
        director.hover_element("h2:has-text('Pending Human Review')")
        time.sleep(0.4)
        director.hover_element(".bg-slate-900\\/90")
        time.sleep(0.6)

        # -------------------------------------------------------------
        # Scene 3: Calendar & Pre-Meeting Briefing Pack (0:30 - 1:00)
        # -------------------------------------------------------------
        print("Recording Scene 3: Calendar & Briefing Pack...")
        director.click_element("nav a:has-text('Calendar & Briefings')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        director.hover_element("h4:has-text('Acme HealthTech')")
        time.sleep(0.5)
        director.click_element("a:has-text('View Briefing Dossier')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.2)

        # Scroll down through the briefing dossier
        director.hover_element("h3:has-text('Executive Synthesis')")
        time.sleep(0.5)
        director.smooth_scroll(250, steps=12)
        director.hover_element("h3:has-text('Commercial & Financial Snapshot')")
        time.sleep(0.5)
        director.hover_element("h3:has-text('Key Stakeholders Dossier')")
        time.sleep(0.6)
        director.smooth_scroll(300, steps=12)
        director.hover_element("h3:has-text('Recommended Talking Points')")
        time.sleep(0.8)

        # Inspect AI Prompt & JSON Schema Modal
        director.smooth_scroll(-450, steps=12)
        director.click_element("button:has-text('Inspect AI Prompt & JSON')")
        time.sleep(1.2)
        director.hover_element("h4:has-text('Validated JSON Output Received')")
        time.sleep(0.8)
        director.click_element("button:has-text('Close Inspector')")
        time.sleep(0.6)

        # Trigger AI Regeneration with live spinner
        director.click_element("button:has-text('Regenerate Intelligence')")
        time.sleep(1.5)

        # -------------------------------------------------------------
        # Scene 4: Transcript Processing & AI Extraction (1:00 - 1:30)
        # -------------------------------------------------------------
        print("Recording Scene 4: Transcript Studio & Extraction...")
        director.click_element("nav a:has-text('Transcripts & AI Extraction')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        # Select Enterprise Sample
        director.click_element("select[name='sample_choice']")
        time.sleep(0.3)
        page.select_option("select[name='sample_choice']", "meridian_tech")
        time.sleep(0.4)
        director.click_element("button:has-text('Ingest Transcript & Open Studio')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        # Toggle raw transcript text
        director.click_element("button:has-text('Toggle Raw Transcript Text')")
        time.sleep(0.8)
        director.click_element("button:has-text('Toggle Raw Transcript Text')")
        time.sleep(0.4)

        # Run AI Extraction
        director.click_element("button:has-text('Run AI Extraction'), button:has-text('Re-Run AI Extraction')")
        time.sleep(2.0)

        director.hover_element("h3:has-text('AI Executive Synthesis')")
        time.sleep(0.6)
        director.smooth_scroll(250, steps=10)
        director.hover_element("h4:has-text('Key Strategic Decisions Ratified')")
        time.sleep(0.6)
        director.hover_element("h3:has-text('Extracted Action Items')")
        time.sleep(0.8)

        # -------------------------------------------------------------
        # Scene 5: Human-in-the-Loop Review Queue (1:30 - 1:55)
        # -------------------------------------------------------------
        print("Recording Scene 5: Human Review Queue...")
        director.click_element("nav a:has-text('Human Review Queue')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        # Approve Action Item 1
        director.hover_element("span:has-text('Confidence:')")
        time.sleep(0.4)
        director.click_element("button:has-text('Approve & Create Asana Task')")
        time.sleep(1.0)

        # Edit Action Item 2 via Modal
        director.click_element("button:has-text('Edit Details')")
        time.sleep(0.8)
        director.type_text("input[name='title']", "Conduct synthetic latency load test benchmarks")
        director.type_text("input[name='proposed_owner_name']", "David Miller")
        time.sleep(0.4)
        director.click_element("button:has-text('Save Modifications & Approve')")
        time.sleep(1.0)

        # -------------------------------------------------------------
        # Scene 6: Simulated Asana Task Manager (1:55 - 2:20)
        # -------------------------------------------------------------
        print("Recording Scene 6: Asana Task Manager...")
        director.click_element("nav a:has-text('Asana Task Manager')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        # Switch to Kanban Board View
        director.click_element("a[href*='view=board']")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.2)
        director.hover_element("h4:has-text('To Do')")
        time.sleep(0.4)
        director.hover_element("h4:has-text('In Progress')")
        time.sleep(0.4)
        director.hover_element("h4:has-text('Completed')")
        time.sleep(0.4)

        # Switch back to List View & Filter Overdue Only
        director.click_element("a[href*='view=list']")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(0.6)

        director.click_element("a:has-text('Overdue Only')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(0.8)

        # Open Task Detail Drawer & Add Discussion Comment
        director.click_element("button[title='Open Task Drawer']")
        time.sleep(0.8)
        director.smooth_scroll(200, steps=8)
        director.type_text("textarea[name='comment_text']", "Benchmark metrics exported from Grafana. 40k req/sec confirmed.")
        director.click_element("button:has-text('Post Update')")
        time.sleep(1.0)
        director.click_element("button:has-text('Close')")
        time.sleep(0.5)

        # -------------------------------------------------------------
        # Scene 7: Weekly Overdue Report & Email Delivery (2:20 - 2:40)
        # -------------------------------------------------------------
        print("Recording Scene 7: Weekly Report & Email Dispatch...")
        director.click_element("nav a:has-text('Weekly Overdue Report')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        director.hover_element("div:has-text('Overdue Commitments')")
        time.sleep(0.4)
        director.smooth_scroll(200, steps=8)
        director.hover_element("h3:has-text('Report Markdown Synthesis')")
        time.sleep(0.6)

        # Form Dispatch Simulated Email
        director.smooth_scroll(250, steps=8)
        director.click_element("button:has-text('Dispatch Simulated Weekly Report Email')")
        time.sleep(1.2)
        director.hover_element("h4:has-text('Recent Outbound Dispatch Logs')")
        time.sleep(0.6)

        # View Email Ledger
        director.click_element("nav a:has-text('Email Delivery Ledger')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        # -------------------------------------------------------------
        # Scene 8: Integrations, Audit Trail & Conclusion (2:40 - 3:00)
        # -------------------------------------------------------------
        print("Recording Scene 8: Integrations & Audit Trail...")
        director.click_element("nav a:has-text('Mock Integrations')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(0.8)
        director.click_element("button:has-text('Sync Now (Simulate)')")
        time.sleep(1.0)

        director.click_element("nav a:has-text('Audit Trail')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.0)

        director.click_element("nav a:has-text('Demo Controls & AI')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(0.8)

        # Return to Dashboard for ending frame
        director.click_element("nav a:has-text('Dashboard')")
        page.wait_for_load_state("networkidle")
        director.inject_cursor()
        time.sleep(1.5)

        # Close session
        context.close()
        browser.close()

    print("Browser recording completed. Processing raw video with FFmpeg...")

    # Find recorded video file
    raw_files = list(RAW_DIR.glob("*.webm"))
    if not raw_files:
        print("Error: No raw video file found in", RAW_DIR)
        return False

    latest_raw = max(raw_files, key=lambda f: f.stat().st_mtime)
    print(f"Converting raw video {latest_raw} to {FINAL_VIDEO_PATH} (720p 30fps H.264)...")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(latest_raw),
        "-vf", "scale=1280:720",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(FINAL_VIDEO_PATH)
    ]

    res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg encoding failed:", res.stderr)
        return False

    file_size_mb = FINAL_VIDEO_PATH.stat().st_size / (1024 * 1024)
    print(f"Successfully generated final video: {FINAL_VIDEO_PATH} ({file_size_mb:.2f} MB)")
    return True


if __name__ == "__main__":
    success = execute_recording()
    sys.exit(0 if success else 1)
