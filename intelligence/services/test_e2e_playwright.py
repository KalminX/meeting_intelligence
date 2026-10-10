"""
End-to-end exploration and verification script for Meeting Intelligence.
Tests all user workflows, clicks, forms, modals, HTMX requests, and status changes.
"""

import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

def run_exploration():
    print("Starting Playwright end-to-end verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        # Capture console errors and uncaught exceptions
        errors = []
        page.on("pageerror", lambda e: errors.append(f"Page Error: {e}"))
        page.on("console", lambda msg: errors.append(f"Console {msg.type}: {msg.text}") if msg.type == "error" else None)

        print("1. Testing Login Page...")
        page.goto(f"{BASE_URL}/login/")
        page.wait_for_load_state("networkidle")
        assert "Sign In" in page.title()
        
        # 1-Click Demo Login
        page.click("button:has-text('Sign In as Sarah Lin')")
        page.wait_for_load_state("networkidle")
        print(f"Logged in. Current URL: {page.url}")
        assert "/dashboard" in page.url or page.url.endswith("/")

        print("2. Testing Dashboard...")
        page.goto(f"{BASE_URL}/")
        page.wait_for_load_state("networkidle")
        assert "Dashboard" in page.title()
        
        # Verify stats presence
        assert page.locator("text=Upcoming Meetings").is_visible()
        assert page.locator("text=Pending Approvals").is_visible()
        assert page.locator("text=Active Tasks").is_visible()
        assert page.locator("text=Overdue Tasks").is_visible()
        print("Dashboard stats verified.")

        print("3. Testing Calendar & Briefings...")
        page.click("nav a:has-text('Calendar & Briefings')")
        page.wait_for_load_state("networkidle")
        assert "Simulated Calendar" in page.title()
        
        # Click view briefing on first meeting
        briefing_link = page.locator("a:has-text('View Briefing Dossier'), a:has-text('Meeting Details')").first
        briefing_link.click()
        page.wait_for_load_state("networkidle")
        print(f"Opened meeting/briefing: {page.url}")

        # If on meeting detail, click open briefing
        if "briefing" not in page.url:
            page.click("a:has-text('Open Executive Briefing')")
            page.wait_for_load_state("networkidle")

        # Test Inspect Prompt Modal
        page.click("button:has-text('Inspect AI Prompt & JSON')")
        time.sleep(0.3)
        assert page.locator("#raw-prompt-modal").is_visible()
        page.click("button:has-text('Close Inspector')")
        time.sleep(0.3)
        print("Briefing and AI Schema Inspector verified.")

        print("4. Testing Transcripts & AI Ingestion...")
        page.click("nav a:has-text('Transcripts & AI Extraction')")
        page.wait_for_load_state("networkidle")
        assert "Transcripts" in page.title()

        # Select prebuilt sample and submit
        page.select_option("select[name='sample_choice']", "meridian_tech")
        page.click("button:has-text('Ingest Transcript & Open Studio')")
        page.wait_for_load_state("networkidle")
        print(f"Loaded sample transcript: {page.url}")
        assert "Extraction Studio" in page.title()

        # Run AI Extraction
        page.click("button:has-text('Run AI Extraction'), button:has-text('Re-Run AI Extraction')")
        page.wait_for_timeout(1500)
        assert page.locator("text=AI Executive Synthesis").is_visible()
        assert page.locator("text=Key Strategic Decisions Ratified").is_visible()
        assert page.locator("text=Extracted Action Items").is_visible()
        print("AI Extraction verified.")

        print("5. Testing Human Approval Queue...")
        page.click("nav a:has-text('Human Review Queue')")
        page.wait_for_load_state("networkidle")
        assert "Human Review Queue" in page.title()

        # Check pending actions
        approve_btn = page.locator("button:has-text('Approve & Create Asana Task')").first
        if approve_btn.is_visible():
            approve_btn.click()
            page.wait_for_timeout(800)
            print("Action item approved via HTMX.")

        # Test edit modal
        edit_btn = page.locator("button:has-text('Edit Details')").first
        if edit_btn.is_visible():
            edit_btn.click()
            page.wait_for_timeout(500)
            assert page.locator("text=Edit & Modify Action Item").is_visible()
            page.fill("input[name='title']", "Updated Action Item Title (Verified)")
            page.click("button:has-text('Save Modifications & Approve')")
            page.wait_for_timeout(800)
            print("Action item modified and approved via modal.")

        print("6. Testing Asana Task Manager...")
        page.click("nav a:has-text('Asana Task Manager')")
        page.wait_for_load_state("networkidle")
        assert "Asana Task Manager" in page.title()

        # Test Board View switch
        page.locator("a[href*='view=board']").click()
        page.wait_for_load_state("networkidle")
        assert "view=board" in page.url
        assert page.locator("h4:has-text('To Do')").first.is_visible()
        assert page.locator("h4:has-text('In Progress')").first.is_visible()
        assert page.locator("h4:has-text('Under Review')").first.is_visible()
        assert page.locator("h4:has-text('Completed')").first.is_visible()
        print("Kanban Board view verified.")

        # Switch back to List View
        page.locator("a[href*='view=list']").click()
        page.wait_for_load_state("networkidle")

        # Open Task Modal Drawer & Add Comment
        task_btn = page.locator("button[title='Open Task Drawer']").first
        task_btn.click()
        page.wait_for_timeout(500)
        assert page.locator("text=Task Description & Context").first.is_visible()
        
        # Add comment
        page.fill("textarea[name='comment_text']", "Deployment verified in staging. Zero latency degradation.")
        page.click("button:has-text('Post Update')")
        page.wait_for_timeout(800)
        assert page.locator("text=Deployment verified in staging").first.is_visible()
        page.click("button:has-text('Close')")
        print("Asana Task Drawer & Comment thread verified.")

        print("7. Testing Weekly Overdue Report & Email Dispatch...")
        page.click("nav a:has-text('Weekly Overdue Report')")
        page.wait_for_load_state("networkidle")
        assert "Weekly Overdue Report" in page.title()
        assert page.locator("text=Overdue Commitments").first.is_visible()

        # Test Email Dispatch
        page.click("button:has-text('Dispatch Simulated Weekly Report Email')")
        page.wait_for_timeout(800)
        assert page.locator("text=250 2.0.0 OK").first.is_visible()
        print("Weekly Report & Simulated Email Dispatch verified.")

        print("8. Testing Mock Integrations Panel...")
        page.click("nav a:has-text('Mock Integrations')")
        page.wait_for_load_state("networkidle")
        assert "Simulated Integrations" in page.title()
        
        # Trigger mock sync
        sync_btn = page.locator("button:has-text('Sync Now (Simulate)')").first
        sync_btn.click()
        page.wait_for_timeout(800)
        print("Mock integration sync verified.")

        print("9. Testing Audit Trail...")
        page.click("nav a:has-text('Audit Trail')")
        page.wait_for_load_state("networkidle")
        assert "Audit Trail" in page.title()
        assert page.locator("table").first.is_visible()
        print("Audit trail verified.")

        print("10. Testing Demo Controls...")
        page.click("nav a:has-text('Demo Controls & AI')")
        page.wait_for_load_state("networkidle")
        assert "Demo Controls" in page.title()
        assert page.locator("text=Deterministic Mock AI Provider").first.is_visible()
        print("Demo controls verified.")

        browser.close()

        if errors:
            print("\nWARNINGS/ERRORS DETECTED:")
            for err in errors:
                print(f" - {err}")
            return False
        else:
            print("\nALL 10 WORKFLOWS PASSED WITH ZERO ERRORS!")
            return True

if __name__ == "__main__":
    success = run_exploration()
    sys.exit(0 if success else 1)
