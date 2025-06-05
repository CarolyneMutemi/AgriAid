# AgriAid 🌾🤖

AI-powered SMS assistant for Kenyan farmers.

AgriAid is an agricultural assistant designed to support farmers in low-bandwidth (2G) areas using SMS and AI technologies. Built using FastAPI, LangGraph, and GPT-4o, it offers timely agricultural insights, crop suggestions, and agrovet support, all through a simple text interface.

## 🔥 Key Features

- **NDVI Analysis:** Uses satellite imagery to deliver vegetation trend insights by Kenyan ward.
- **Weather Reports:** Real-time weather, yesterday’s data, and forecasts for planning.
- **Soil Insight (via SoilGrids):** Pulls basic soil profile for targeted suggestions (improving).
- **FAO Crop Calendar Integration:** Suggests crops and planting times based on season and region.
- **Agrovet Directory & Contact Requests:** Farmers can find local agrovets or request to be contacted.
- **Crop & Fertilizer Recommendations:** Coming soon – smart suggestions for better yields.
- **Mobile Pest & Disease Detection:** Planned feature for image-based diagnosis via smartphone.
- **Session Memory:** Tracks context for up to 1 hour or 30 interactions, resetting after that.
- **Farmer Farm Registration:** Enables personalized advice and regional targeting.

## 🚀 Tech Stack

- `FastAPI` – for API backend
- `LangGraph + GPT-4o` – for intelligent agent workflows
- `ChromaDB` – for fast RAG-based retrieval
- `Streamlit` – for demo UI (not production frontend)
- `Africa's Talking API` – for SMS delivery

## 📱 Demo & Sandbox

- 🎥 [Demo Video](#) _(coming soon)_
- 🌍 [Simulator & Sandbox](#) _(coming soon)_

## 📦 Installation

```bash
git clone https://github.com/CarolyneMutemi/AgriAid
cd AgriAid
# create a virtual environment
python3 -m venv venv
source venv/bin/activate
# install dependencies
pip3 install -r requirements.txt
# set up virtual environment and install dependencies
uvicorn main:app --reload
```
