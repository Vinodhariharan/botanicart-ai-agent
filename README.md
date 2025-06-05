# BotaniCart AI Agent

An intelligent AI-powered shopping assistant for the **BotaniCart** plant e-commerce platform. This conversational agent helps users discover the perfect plants through natural language interaction and provides expert care guidance post-purchase.

## Overview

Built with **LangChain**, **Gemini AI**, and **Firebase Firestore**, the BotaniCart AI Agent transforms plant shopping into a guided, personalized experience. It offers recommendations, care tips, and real-time product availability—reducing customer support load and boosting conversions.

## Features

### Smart Shopping Assistant

* Personalized plant suggestions (e.g., price, maintenance, pet safety)
* Real-time inventory and pricing
* Always-on fallback recommendations

### Plant Care Guide

* Post-purchase care instructions
* Troubleshooting tips (e.g., yellow leaves, wilting)
* Seasonal and contextual advice

### Conversational Commerce

* Natural language interaction
* Session context retention
* Intelligent upselling and cross-selling

## Tech Stack

* **LangChain ReAct Agent** (core logic)
* **Gemini 1.5 Flash** (NLP engine)
* **Firebase Firestore** (product and customer data)
* **Python** backend, optional Docker setup

## Quick Start

### Prerequisites

* Python 3.8+
* Firebase Firestore setup
* Gemini API key

### Setup

```bash
git clone https://github.com/Vinodhariharan/botanicart-ai-agent
cd botanicart-ai-agent
pip install -r requirements.txt
```

### Configure

##### Create a `.env` file (not updated):

```env
GEMINI_API_KEY=your_gemini_api_key
FIREBASE_PROJECT_ID=your_project_id
BOTANICART_DB_URL=your_database_url
```

## Contributing

1. Fork the repo
2. Create a feature branch
3. Follow coding standards
4. Submit a PR with clear feature description

---

**Built for BotaniCart – Where AI meets plants**

> GitHub: [Vinodhariharan/botanicart-ai-agent](https://github.com/Vinodhariharan/botanicart-ai-agent)
