# SmartChoice AI 🤖

> **AI-powered multi-domain Decision Intelligence Platform**
> Built with Python Flask + IBM Watsonx.ai Granite models

---

## Overview

SmartChoice AI is a full-stack web application that functions as an **elite strategic consultant** — helping users make complex decisions across 8+ domains through AI-driven analysis, mathematical scoring, and structured reasoning frameworks.

### Key Features

| Feature | Description |
|---|---|
| 🤖 **AI Chat Interface** | Conversational AI powered by IBM Granite models |
| 📊 **Decision Dashboard** | Visual analytics with Chart.js |
| ⚖️ **Multi-Option Comparison** | Side-by-side matrix with normalized scores |
| 🏆 **Decision Scores** | Mathematical 0-100 scoring per option |
| ⚠️ **Risk Analysis Panel** | Color-coded HIGH/MEDIUM/LOW risk tracker |
| 📜 **History Timeline** | Persistent session history with PDF export |
| 🌙 **Dark/Light Mode** | Persistent theme toggle |
| 📱 **Mobile Responsive** | Bootstrap 5 fluid layout |

### Supported Decision Domains

🎓 Education · 💼 Career · 📈 Investment · 💻 Technology · 💳 Banking · 🛡️ Insurance · 🏢 Business · 🏠 Daily Life

---

## Quick Start

```bash
# 1. Navigate to project
cd SmartChoice_AI

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux
# Edit .env with your IBM API credentials

# 5. Run
python run.py
```

Open http://localhost:5000

---

## Configuration

All agent behavior is controlled from **one file**: `app/core/agent_instructions.py`

```python
# Change AI persona
AGENT_PERSONA = "You are..."

# Switch reasoning frameworks
ACTIVE_FRAMEWORKS = ["pros_cons", "swot", "cost_benefit", ...]

# Adjust explanation depth
EXPLANATION_DEPTH = "deep_analytical"  # conceptual | analytical | deep_analytical

# Set risk strategy
RISK_STRATEGY = "balanced"  # conservative | balanced | aggressive

# Tune scoring weights per domain
DOMAIN_CRITERIA_WEIGHTS["investment"]["risk_level"] = 0.35
```

---

## Sample Decisions You Can Ask

- *"Should I pursue an MS in Data Science or an MBA in IT Management?"*
- *"Should I invest ₹15,000/month in a Mutual Fund SIP or Fixed Deposit?"*
- *"Compare Laptop A vs Laptop B for coding under ₹75,000 INR"*
- *"HDFC Regalia vs Axis Magnus — which credit card for ₹40K monthly spend?"*
- *"Should our company build custom software or buy a SaaS solution?"*
- *"Fixed vs Floating rate home loan for ₹50 lakh over 20 years"*

---

## Architecture

```
Flask App Factory
├── 4 Blueprints (chat, decisions, history, reports)
├── IBM Watsonx.ai Granite LLM integration
├── SQLAlchemy ORM (SQLite dev / PostgreSQL prod)
├── Flask-Limiter rate limiting
├── ReportLab PDF generation
└── Bootstrap 5 + Chart.js frontend
```

---

## Deployment

See [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) for full production setup.

---

## License

MIT © SmartChoice AI
