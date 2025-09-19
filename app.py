import os
import re
import requests
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.ollama import Ollama
from firecrawl import Firecrawl

# Load environment variables
load_dotenv()

# Keys
ORS_API_KEY = os.getenv("ORS_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

# ----------- Helpers -----------

def get_weather(lat, lon):
    """Fetch free weather data from Open-Meteo API"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json().get("daily", {})
    return {"error": "Weather API failed"}

def get_distance_time(start_coords, end_coords):
    """Fetch distance & time using ORS API"""
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}
    params = {"start": f"{start_coords[1]},{start_coords[0]}", "end": f"{end_coords[1]},{end_coords[0]}"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        data = res.json()
        dist = data["features"][0]["properties"]["segments"][0]["distance"] / 1000
        time_min = data["features"][0]["properties"]["segments"][0]["duration"] / 60
        return f"{dist:.1f} km, {time_min:.0f} min"
    return "Distance lookup failed"

def crawl_places(url: str) -> str:
    """Crawl attractions/restaurants from a website and return markdown."""
    firecrawl = Firecrawl(api_key=FIRECRAWL_API_KEY)
    result = firecrawl.scrape(url, formats=["markdown"])

    if result.success and hasattr(result, "data") and hasattr(result.data, "markdown"):
        return result.data.markdown
    elif isinstance(result, dict) and "data" in result and "markdown" in result["data"]:
        # Fallback if SDK version behaves differently
        return result["data"]["markdown"]
    else:
        return "No data found"


# ----------- Streamlit UI -----------

st.set_page_config(page_title="🌍 Free AI Travel Planner", page_icon="✈️", layout="wide")
st.title("🌍 Free AI Travel Planner")
st.caption("Powered by Ollama + ORS + Firecrawl + Open-Meteo (100% Free APIs)")

# Sidebar
with st.sidebar:
    st.header("🔑 API Keys")
    ors_key = st.text_input("OpenRouteService API Key", value=ORS_API_KEY, type="password")
    firecrawl_key = st.text_input("Firecrawl API Key", value=FIRECRAWL_API_KEY, type="password")
    if ors_key: os.environ["ORS_API_KEY"] = ors_key
    if firecrawl_key: os.environ["FIRECRAWL_API_KEY"] = firecrawl_key

# Main inputs
st.header("📍 Trip Details")
destination = st.text_input("Destination", placeholder="e.g., Paris, Tokyo, New York")
num_days = st.number_input("Number of Days", min_value=1, max_value=21, value=5)
budget = st.number_input("Budget (USD)", min_value=100, max_value=10000, step=100, value=2000)
preferences = st.text_area("Preferences", placeholder="Museums, nightlife, food, shopping...")

if st.button("🎯 Generate Itinerary", type="primary"):
    if not ors_key or not firecrawl_key:
        st.error("Please enter both ORS and Firecrawl API keys.")
    elif not destination:
        st.error("Please enter a destination.")
    else:
        with st.spinner("Planning your trip with AI agents..."):
            try:
                # Use Ollama to generate itinerary text
                agent = Agent(
                    name="Travel Planner",
                    model=Ollama(id="llama3.2:latest"),  # lighter than gpt-oss:20b
                    description="Generates detailed itineraries with timing, costs, and recommendations",
                )

                prompt = f"""
                Create a detailed {num_days}-day travel itinerary for {destination}.
                Budget: ${budget}.
                Preferences: {preferences}.
                Include:
                - Specific daily activities
                - Restaurants & attractions
                - Approximate costs
                - Use buffer time
                """

                response = agent.run(prompt)
                itinerary_text = response.content if hasattr(response, "content") else str(response)

                # Show result
                st.success("✅ Your Itinerary is Ready!")
                st.markdown(itinerary_text)

                # Weather (example: Paris coords)
                st.subheader("🌤 Weather Forecast (Sample)")
                weather = get_weather(48.8566, 2.3522)
                st.json(weather)

                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
