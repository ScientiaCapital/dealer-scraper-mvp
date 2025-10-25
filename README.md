# 🚀 Multi-Source Lead Generation System

**Personal learning project exploring automation, data engineering, and cloud deployment**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A learning project by a sales professional exploring software engineering, data pipelines, and GTM automation concepts

---

## 📚 About This Project

I'm a sales professional learning to code and build technical tools. This project serves as my exploration into:

- **Web scraping and browser automation** - Learning to collect data from multiple sources
- **Cloud-native architecture** - Understanding serverless deployment patterns
- **Data engineering** - Practicing data aggregation, normalization, and deduplication
- **Software design patterns** - Implementing Factory, Abstract Base Class, and other patterns
- **GTM automation concepts** - Exploring how to build tools that support sales workflows

This repository represents my journey from sales → technical skills, documenting what I'm learning along the way.

---

## 🎯 What It Does

This system demonstrates concepts in automated lead generation:

**Input**: Multiple data sources
**Process**: Aggregation → Deduplication → Scoring → Prioritization
**Output**: Sorted dataset ready for analysis

**Key Learning Areas**:
- Multi-source data collection and normalization
- Cross-referencing records across different data structures
- Building scoring algorithms for prioritization
- Cloud-native serverless deployment
- Docker containerization and optimization

---

## 🏗️ Architecture & Design Patterns

### Abstract Base Class Pattern
```python
# Extensible scraper framework
from scrapers.base_scraper import BaseDealerScraper

class CustomScraper(BaseDealerScraper):
    # Implement abstract methods
    def get_extraction_script(self): ...
    def parse_dealer_data(self): ...
```

### Factory Pattern
```python
# Dynamic instantiation
from scrapers.scraper_factory import ScraperFactory

scraper = ScraperFactory.create("ScraperName", mode="runpod")
```

### Standardized Data Models
- Unified data structures across different sources
- Type-safe data models using dataclasses
- Consistent field mapping and validation

---

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.8+** - Primary language for orchestration and data processing
- **Playwright** - Browser automation for headless data collection
- **Requests** - HTTP client for API interactions
- **python-dotenv** - Environment variable management

### Cloud Infrastructure
- **Serverless deployment** - Auto-scaling compute with pay-per-use model
- **Docker** - Containerization for consistent deployment
- **Singleton pattern** - Optimized resource management

### Data Engineering
- **Multi-key matching** - Phone, domain, and fuzzy name matching for record linkage
- **Deduplication algorithms** - Removing duplicate records across sources
- **Priority scoring** - Multi-dimensional ranking system

---

## ⚡ Quick Start

### Prerequisites
- Python 3.8+
- pip package manager
- Cloud service account (for serverless deployment)

### 1. Installation
```bash
git clone https://github.com/yourusername/dealer-scraper-mvp.git
cd dealer-scraper-mvp
pip install -r requirements.txt
```

### 2. Configuration
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Project Structure
```
dealer-scraper-mvp/
├── scrapers/
│   ├── base_scraper.py            # Abstract base class design
│   ├── scraper_factory.py         # Factory pattern implementation
│   └── __init__.py
│
├── runpod-playwright-api/         # Serverless deployment
│   ├── handler.py
│   ├── playwright_service.py
│   └── Dockerfile
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎓 Skills Demonstrated

### Cloud & DevOps
- **Docker containerization** - Multi-stage builds, layer optimization
- **Serverless deployment** - Auto-scaling infrastructure, pay-per-use patterns
- **Environment management** - Secure configuration and secrets handling
- **Cost optimization** - Efficient resource usage in cloud environments

### Data Engineering
- **Web scraping** - Automated data collection from multiple sources
- **Data normalization** - Standardizing data across different schemas
- **Cross-referencing** - Multi-key matching algorithms for record linkage
- **Deduplication** - Identifying and removing duplicate records
- **Priority scoring** - Multi-dimensional ranking systems

### Software Architecture
- **Abstract Base Classes** - Extensible framework design
- **Factory Pattern** - Dynamic object instantiation
- **Singleton Pattern** - Resource optimization
- **Type Safety** - Using dataclasses for structured data
- **Separation of Concerns** - Modular, maintainable code structure

### API & Integration
- **HTTP APIs** - RESTful endpoint design
- **Authentication** - API key management and security
- **Error handling** - Graceful degradation and retry logic
- **Rate limiting** - Respecting API constraints

### Python Best Practices
- **Virtual environments** - Dependency isolation
- **Requirements management** - Version pinning
- **Environment variables** - Configuration management
- **Code organization** - Package structure and imports

---

## 📊 Learning Progress

### ✅ Completed
- [x] Abstract base class framework
- [x] Factory pattern implementation
- [x] Serverless cloud deployment
- [x] Docker containerization
- [x] Data normalization pipeline
- [x] Multi-source aggregation

### 🔄 In Progress
- [ ] Advanced matching algorithms
- [ ] Enrichment service integration
- [ ] CRM integration patterns

### 🔮 Future Learning Goals
- [ ] GraphQL API exploration
- [ ] Kubernetes orchestration
- [ ] Real-time data streaming
- [ ] Machine learning integration
- [ ] Advanced monitoring and observability

---

## 🔧 Technical Concepts Explored

### Browser Automation
- Headless browser control with Playwright
- JavaScript execution in browser context
- AJAX and dynamic content handling
- Cookie management and session handling

### Cloud-Native Patterns
- Serverless function design
- Cold start optimization
- State management in stateless environments
- Auto-scaling strategies

### Data Quality
- Input validation and sanitization
- Data type consistency
- Missing data handling
- Fuzzy matching for imperfect data

---

## 📈 Deployment

The project includes serverless deployment infrastructure:

```bash
cd runpod-playwright-api
docker build -t scraper-api .
# Deploy to cloud provider
```

**Key Features**:
- Auto-scaling from 0 to N instances
- Pay-per-execution pricing model
- Isolated execution contexts
- Optimized cold start times

---

## 🤝 Learning Resources

This project helped me learn from:
- Python documentation and best practices
- Playwright automation documentation
- Docker containerization guides
- Serverless architecture patterns
- Data engineering principles

---

## 📄 License

MIT License - This is an educational project for learning purposes.

---

## 🌱 About My Learning Journey

I'm a sales professional developing technical skills to better understand the tools and systems I work with. This project represents:

- **Self-directed learning** - Teaching myself Python, Docker, and cloud deployment
- **Practical application** - Building real systems to understand concepts deeply
- **Continuous improvement** - Each commit represents new skills acquired
- **Technical curiosity** - Exploring how modern GTM tools are built

**Skills I'm Developing**:
- Backend development with Python
- Cloud infrastructure and DevOps
- Data engineering and pipelines
- Software architecture and design patterns
- API integration and automation

---

<div align="center">

**⭐ Learning in public: Python • Docker • Cloud • Data Engineering • Automation**

*Built by a sales professional learning software engineering*

</div>
