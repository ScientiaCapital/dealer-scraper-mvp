# Coperniq Lead Generation Orchestration Agent

AI-powered assistant for automating and optimizing contractor prospecting workflows using Claude Agent SDK.

## Overview

This agent helps orchestrate complex lead generation strategies by providing natural language access to:
- **Multi-OEM dealer scraping** across 18+ brands (generators, solar, batteries, HVAC)
- **Multi-brand contractor detection** (highest-value prospects managing 2-3+ platforms)
- **ICP scoring** with Coperniq's algorithm (Resimercial 35%, Multi-OEM 25%, MEP+R 25%, O&M 15%)
- **SREC state filtering** for sustainable post-ITC markets

## Quick Start

### Prerequisites
- Python 3.10+ (you have 3.13.7 ✅)
- Virtual environment activated
- `ANTHROPIC_API_KEY` in .env file ✅

### Run the Agent

```bash
# From project root
./run_agent.sh

# Or manually:
source venv/bin/activate
python3 agent/main.py
```

### First Commands to Try

```
You: Show me the pipeline status
You: List all available scrapers
You: What SREC states do we target?
You: Help
```

## Available Tools

### 🔍 Scraping Tools
- `list_available_scrapers` - View all 18 registered OEM scrapers
- `get_srec_states` - View SREC states and ZIP configuration
- `run_scraper` - Execute scraper for specific OEM(s) and state(s)

### 📊 Analysis Tools
- `analyze_multi_oem_contractors` - Find contractors with 2-3+ brand certifications (HIGHEST VALUE)
- `get_latest_scraped_data` - View recent scraped data files

### 🎯 Scoring Tools
- `score_leads` - Apply Coperniq ICP algorithm (0-100 scale, PLATINUM/GOLD/SILVER/BRONZE)
- `filter_srec_states` - Filter to sustainable markets with post-ITC incentives

### 📈 Pipeline Tools
- `get_pipeline_stats` - View comprehensive pipeline statistics
- `export_top_prospects` - Export GOLD/PLATINUM prospects for outreach

## Example Workflows

### 1. Quick Test Run
```
You: Run a test scrape of Generac for 3 California ZIPs
```

### 2. Multi-OEM Analysis
```
You: Run the Generac, Tesla, and Enphase scrapers for California and Texas

You: Analyze the scraped data to find multi-OEM contractors

You: Score all the leads and show me the top 50 prospects
```

### 3. Full Lead Generation Pipeline
```
You: Show me the current pipeline status

You: Run scrapers for Generac, Cummins, and Mitsubishi across all SREC states

You: Analyze for multi-OEM contractors

You: Score all leads with the ICP algorithm

You: Filter to SREC states only

You: Export the top 100 prospects for our BDR team
```

## Business Context

### Coperniq's Unique Value
- **ONLY** brand-agnostic monitoring platform for microinverters + batteries + generators
- Solves the "3+ platform chaos" problem for multi-brand contractors

### Target Market
- **Resimercial** contractors (both residential + commercial)
- **Multi-OEM certified** (2-3+ brands = highest pain point)
- **SREC states** (sustainable markets post-ITC)

### Key Insights
- **Multi-OEM contractors** (2-3+ brands) are 10x more valuable than single-brand
- **SREC states** have sustainable incentives after federal ITC expires
- **ITC urgency** creates natural closing pressure (residential Dec 2025, commercial Q2 2026)

## ICP Scoring Dimensions

1. **Resimercial (35%)** - Both residential + commercial = scaling contractors
2. **Multi-OEM (25%)** - Managing 2-3+ platforms = core pain point
3. **MEP+R (25%)** - Multi-trade self-performers = platform power users
4. **O&M (15%)** - Operations & maintenance = recurring revenue focus

**Tier Thresholds:**
- 💎 **PLATINUM** (80-100): Immediate executive outreach
- 🥇 **GOLD** (60-79): Priority BDR outreach
- 🥈 **SILVER** (40-59): Nurture campaigns
- 🥉 **BRONZE** (<40): Long-term pipeline

## File Structure

```
agent/
├── main.py                    # Agent entry point
├── tools/                     # Custom MCP tools
│   ├── scraper_tools.py      # Scraping orchestration
│   ├── analysis_tools.py     # Multi-OEM detection
│   ├── scoring_tools.py      # ICP scoring & filtering
│   └── pipeline_tools.py     # Pipeline management
├── prompts/
│   └── system_prompt.txt     # Agent personality & context
└── README.md                  # This file
```

## Technical Details

- **SDK Version**: claude-agent-sdk 0.1.5
- **Model**: claude-sonnet-4-5-20250929
- **Mode**: PLAYWRIGHT (local automation, free)
- **Alternative**: RUNPOD mode (cloud scaling, pay-per-second)

## Troubleshooting

### Import Errors
The agent uses importlib to load config.py directly to avoid conflicts with the config/ package.

### API Key Not Found
Ensure `ANTHROPIC_API_KEY` is set in your `.env` file (not .env.example).

### Virtual Environment
Always activate venv before running:
```bash
source venv/bin/activate
```

## Next Steps

1. **Test with a quick scrape**: `Run Generac for 3 California ZIPs`
2. **Check your pipeline**: `Show me the pipeline status`
3. **Run full workflow**: Follow the multi-OEM analysis workflow above
4. **Export prospects**: Get your top 50 GOLD/PLATINUM contractors for outreach

## Support

For issues or questions:
- Check the main project README.md
- Review CLAUDE.md for project context
- See existing scripts in scripts/ for examples

---

**Built with Claude Agent SDK** | **Optimized for Coperniq's GTM Strategy**
