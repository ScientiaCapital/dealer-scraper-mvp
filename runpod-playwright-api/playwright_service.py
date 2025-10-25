"""
Playwright Browser Automation Service
Manages browser lifecycle and executes workflow-based automation
"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Dict, List, Optional, Any
import time


class PlaywrightService:
    """
    Manages Playwright browser lifecycle using singleton pattern.
    Creates new context per request for clean state while reusing browser for performance.
    """
    
    def __init__(self):
        """Initialize browser once (singleton pattern for performance)"""
        self.playwright = None
        self.browser: Optional[Browser] = None
        self._initialize_browser()
    
    def _initialize_browser(self):
        """
        Initialize Playwright and launch browser.
        CRITICAL: headless=True required in Docker (no X server).
        Uses --no-sandbox and --disable-dev-shm-usage for Docker compatibility.
        """
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,  # Required in Docker environment
            args=['--no-sandbox', '--disable-dev-shm-usage']  # Docker optimization
        )
        print("[PlaywrightService] Browser initialized successfully")
    
    def execute_workflow(self, steps: List[Dict], options: Dict = None) -> Dict:
        """
        Execute a workflow of Playwright actions.
        
        Args:
            steps: List of action dicts with 'action' key and action-specific params
            options: Optional configuration dict (currently unused, reserved for future)
        
        Returns:
            Dict with status, results, and execution_time
            On error: Dict with error key
        
        Supported actions:
            - navigate: {"action": "navigate", "url": "https://..."}
            - click: {"action": "click", "selector": "button"}
            - fill: {"action": "fill", "selector": "input", "text": "value"}
            - type: {"action": "type", "selector": "input", "text": "value", "delay": 100}
            - wait_for_selector: {"action": "wait_for_selector", "selector": "div", "timeout": 5000, "state": "visible"}
            - press: {"action": "press", "key": "Enter", "selector": "input"}  # selector optional
            - wait: {"action": "wait", "timeout": 3000}
            - evaluate: {"action": "evaluate", "script": "() => {...}"}
        """
        context: BrowserContext = self.browser.new_context()  # Clean state per request
        page: Page = context.new_page()
        results = []
        start_time = time.time()
        
        try:
            for i, step in enumerate(steps):
                action = step.get("action")
                print(f"[PlaywrightService] Step {i+1}/{len(steps)}: {action}")
                
                if action == "navigate":
                    page.goto(step["url"], timeout=30000)  # 30s navigation timeout
                
                elif action == "click":
                    page.click(step["selector"], timeout=5000)  # 5s action timeout
                
                elif action == "fill":
                    page.fill(step["selector"], step["text"], timeout=5000)

                elif action == "type":
                    # Type text character by character with delay (triggers autocomplete)
                    selector = step["selector"]
                    text = step["text"]
                    delay = step.get("delay", 100)  # Default 100ms between keystrokes
                    element = page.locator(selector)
                    element.click()  # Focus first
                    page.wait_for_timeout(300)  # Short pause after focus
                    element.type(text, delay=delay)
                    print(f"[PlaywrightService] Typed '{text}' with {delay}ms delay")

                elif action == "wait_for_selector":
                    # Wait for element to appear (critical for autocomplete dropdown)
                    selector = step["selector"]
                    timeout = step.get("timeout", 10000)  # Default 10s
                    state = step.get("state", "visible")  # Default to visible
                    page.wait_for_selector(selector, state=state, timeout=timeout)
                    print(f"[PlaywrightService] Waited for selector: {selector} (state: {state})")

                elif action == "press":
                    # Press keyboard key (e.g., "Enter", "Escape", "Tab")
                    key = step["key"]
                    selector = step.get("selector", None)
                    if selector:
                        page.locator(selector).press(key)
                    else:
                        page.keyboard.press(key)
                    print(f"[PlaywrightService] Pressed key: {key}")

                elif action == "wait":
                    page.wait_for_timeout(step["timeout"])
                
                elif action == "evaluate":
                    results = page.evaluate(step["script"])
                
                else:
                    raise ValueError(f"Unknown action: {action}")
            
            execution_time = time.time() - start_time
            print(f"[PlaywrightService] Workflow completed in {execution_time:.2f}s")
            
            return {
                "status": "success",
                "results": results,
                "execution_time": execution_time
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"[PlaywrightService] Error: {str(e)}")
            return {
                "error": str(e),
                "execution_time": execution_time
            }
        
        finally:
            context.close()  # Always clean up context
    
    def __del__(self):
        """Cleanup browser resources on shutdown"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
