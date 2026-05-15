# Hasta ML: Autonomous Car Negotiation Agent 🚗🤖

**Hasta ML** is an end-to-end autonomous pipeline designed to scrape, value, and negotiate for used cars on the Moroccan market (Avito.ma). By combining web scraping, machine learning, and Large Language Models (LLMs), it automates the entire process of finding a great deal—from discovery to price agreement.

## 🌟 Key Features

*   **Autonomous Scraper**: A Playwright-based crawler that extracts car specs, pricing, and seller contact info from Avito.ma.
*   **AI Negotiation Brain**: A state machine built with **LangGraph** and powered by **LLaMA 3.1**. It handles multi-turn WhatsApp conversations in a mix of Darija and French.
*   **Machine Learning Valuation**: 
    *   **TensorFlow Neural Network**: Predicts "True Market Value" based on historical negotiation data.
    *   **Scikit-Learn Fallback**: Ensures reliability during "cold-start" phases.
*   **WhatsApp Integration**: Real-time communication via `wacli` CLI wrapper.
*   **Live Dashboard**: A **Streamlit** mission control for monitoring active negotiations, potential savings, and A/B test strategy performance.

## 🛠️ Tech Stack

*   **Logic**: LangGraph, LangChain, Python
*   **AI**: LLaMA 3.1 (Ollama)
*   **ML**: TensorFlow, Scikit-Learn, Pandas, NumPy
*   **Web**: Playwright, Streamlit
*   **Database**: SQLite

## 🚀 Getting Started

### Prerequisites
1.  Install [Ollama](https://ollama.com/) and pull the model: `ollama pull llama3.1`.
2.  Install [wacli](https://github.com/m1k1o/wacli) for WhatsApp CLI interaction.
3.  Install [Playwright](https://playwright.dev/python/docs/intro) browsers.

### Installation
```bash
pip install -r requirements.txt
playwright install chromium
```

### Usage
1.  **Scrape Leads**: `python scraper.py`
2.  **Start Negotiation Engine**: `python main.py`
3.  **Launch Dashboard**: `streamlit run dashboard.py`
4.  **Train the Brain**: `python train_ml.py`

## 📊 How it Works
1.  **Scrape**: Listings are pulled from Avito and saved to `research_study.db`.
2.  **Value**: The system calculates a target price based on model, year, and mileage.
3.  **Negotiate**: The AI initiates contact. It analyzes seller replies, adjusts its strategy, and attempts to close the deal at or below the market value.
4.  **Learn**: Negotiation results are used to retrain the TensorFlow model, refining future valuations.

---
*Developed for autonomous market research and negotiation.*
