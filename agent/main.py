#!/usr/bin/env python3
"""
Coperniq Lead Generation Orchestration Agent
Entry point for the Claude Agent SDK-powered lead generation assistant
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API key is set
if not os.getenv("ANTHROPIC_API_KEY"):
    print("❌ Error: ANTHROPIC_API_KEY not found in environment variables")
    print("💡 Add your API key to the .env file")
    sys.exit(1)

# Import Claude Agent SDK
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        create_sdk_mcp_server
    )
except ImportError:
    print("❌ Error: claude-agent-sdk not installed")
    print("💡 Install with: pip install claude-agent-sdk")
    sys.exit(1)

# Import custom tools
from tools.scraper_tools import (
    list_available_scrapers,
    get_srec_states,
    run_scraper
)
from tools.analysis_tools import (
    analyze_multi_oem_contractors,
    get_latest_scraped_data
)
from tools.scoring_tools import (
    score_leads,
    filter_srec_states
)
from tools.pipeline_tools import (
    get_pipeline_stats,
    export_top_prospects
)


def load_system_prompt() -> str:
    """Load the system prompt from file."""
    prompt_file = Path(__file__).parent / "prompts" / "system_prompt.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


async def main():
    """Main entry point for the agent."""
    print("🚀 Initializing Coperniq Lead Generation Orchestration Agent...\n")

    # Create MCP server with all custom tools
    lead_gen_server = create_sdk_mcp_server(
        name="lead_generation",
        version="1.0.0",
        tools=[
            # Scraping tools
            list_available_scrapers,
            get_srec_states,
            run_scraper,
            # Analysis tools
            analyze_multi_oem_contractors,
            get_latest_scraped_data,
            # Scoring tools
            score_leads,
            filter_srec_states,
            # Pipeline tools
            get_pipeline_stats,
            export_top_prospects
        ]
    )

    # Load system prompt
    system_prompt = load_system_prompt()

    # Configure agent options
    options = ClaudeAgentOptions(
        mcp_servers={"lead_gen": lead_gen_server},
        allowed_tools=[
            # Scraping tools
            "mcp__lead_gen__list_available_scrapers",
            "mcp__lead_gen__get_srec_states",
            "mcp__lead_gen__run_scraper",
            # Analysis tools
            "mcp__lead_gen__analyze_multi_oem_contractors",
            "mcp__lead_gen__get_latest_scraped_data",
            # Scoring tools
            "mcp__lead_gen__score_leads",
            "mcp__lead_gen__filter_srec_states",
            # Pipeline tools
            "mcp__lead_gen__get_pipeline_stats",
            "mcp__lead_gen__export_top_prospects"
        ],
        system_prompt=system_prompt
    )

    # Initialize Claude SDK client
    client = ClaudeSDKClient(options)

    print("✅ Agent initialized successfully!")
    print("\n" + "=" * 70)
    print("🎯 COPERNIQ LEAD GENERATION ORCHESTRATION AGENT")
    print("=" * 70)
    print("\nAvailable commands:")
    print("  - Type your question or command naturally")
    print("  - Type 'help' for suggested workflows")
    print("  - Type 'status' to check pipeline status")
    print("  - Type 'exit' or 'quit' to exit")
    print("\nExample commands:")
    print("  • 'Show me the pipeline status'")
    print("  • 'Run the Generac scraper for California'")
    print("  • 'Analyze our data for multi-OEM contractors'")
    print("  • 'Score all leads and show me the top prospects'")
    print("\n" + "=" * 70 + "\n")

    # Interactive conversation loop
    conversation_history = []

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye! Happy prospecting!")
                break

            # Handle help command
            if user_input.lower() == 'help':
                print("\n📚 SUGGESTED WORKFLOWS:\n")
                print("1️⃣ Quick Pipeline Check:")
                print("   'Show me the pipeline status'\n")
                print("2️⃣ Test Scraper:")
                print("   'Run a test scrape of Generac for 3 California ZIPs'\n")
                print("3️⃣ Full Multi-OEM Analysis:")
                print("   'Run Generac, Tesla, and Enphase scrapers for CA and TX'")
                print("   'Analyze for multi-OEM contractors'\n")
                print("4️⃣ Lead Scoring:")
                print("   'Score all leads and export the top 50 prospects'\n")
                continue

            # Handle status command
            if user_input.lower() == 'status':
                user_input = "Show me the pipeline statistics"

            # Add to conversation history
            conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # Get response from agent
            print("\n🤔 Processing...\n")

            # Use the conversation history for context
            response = await client.complete(
                messages=conversation_history,
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096
            )

            # Extract assistant's response
            assistant_message = response.content[0].text if response.content else "No response"

            # Add to conversation history
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            # Print response
            print(f"Agent: {assistant_message}\n")
            print("-" * 70 + "\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Happy prospecting!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            continue


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
