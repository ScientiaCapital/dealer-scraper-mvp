"""
RunPod Serverless Handler
Entry point for RunPod serverless worker that processes browser automation jobs
"""

import runpod
from playwright_service import PlaywrightService

# Initialize browser service once at module level (singleton pattern)
# Browser persists across job invocations when refresh_worker=False
service = PlaywrightService()


def handler(job):
    """
    RunPod serverless handler function.
    
    Args:
        job: Dict with structure {"input": {"workflow": [...], "options": {...}}}
    
    Returns:
        Dict with results or error
    
    Example job input:
        {
            "input": {
                "workflow": [
                    {"action": "navigate", "url": "https://example.com"},
                    {"action": "click", "selector": "button"},
                    {"action": "evaluate", "script": "() => document.title"}
                ],
                "options": {}
            }
        }
    """
    try:
        job_input = job["input"]
        workflow = job_input.get("workflow", [])
        options = job_input.get("options", {})
        
        print(f"[Handler] Processing job with {len(workflow)} steps")
        result = service.execute_workflow(workflow, options)
        return result
    
    except Exception as e:
        print(f"[Handler] Error: {str(e)}")
        return {"error": str(e)}


# Start RunPod serverless worker
# refresh_worker=False keeps browser alive between jobs (CRITICAL for performance)
runpod.serverless.start({
    "handler": handler,
    "refresh_worker": False  # Reuse browser across jobs
})
