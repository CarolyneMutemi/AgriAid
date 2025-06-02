import streamlit as st
import time
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from agent.ai_agent import process_sms_message

user_phone = "+12345596780"

# Configure the page
st.set_page_config(
    page_title="AgriAid - Your Agricultural AI Assistant",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Main app styling */
    .main {
        padding: 0;
    }
    
    /* Custom header */
    .header-container {
        background: linear-gradient(135deg, #2E7D32, #4CAF50, #81C784);
        padding: 2rem;
        border-radius: 0 0 20px 20px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3);
    }
    
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
        font-family: 'Inter', sans-serif;
    }
    
    .header-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.2rem;
        text-align: center;
        margin-top: 0.5rem;
        font-family: 'Inter', sans-serif;
    }
    
    /* Chat container */
    .chat-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 2px 15px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border: 1px solid #E8F5E8;
    }
    
    /* Message styling */
    .user-message {
        # background: linear-gradient(135deg, #E3F2FD, #BBDEFB);
        border-radius: 18px 18px 5px 18px;
        padding: 12px 16px;
        margin: 8px 0 8px 2rem;
        border-left: 4px solid #2196F3;
        box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
    }
    
    .ai-message {
        # background: linear-gradient(135deg, #E8F5E8, #C8E6C9);
        border-radius: 18px 18px 18px 5px;
        padding: 12px 16px;
        margin: 8px 2rem 8px 0;
        border-left: 4px solid #4CAF50;
        box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #F1F8E9, #E8F5E8);
    }
    
    /* Feature cards */
    .feature-card {
        # background: white;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        border: 1px solid #E8F5E8;
        transition: transform 0.2s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.12);
    }
    
    /* Quick actions */
    .quick-action-btn {
        background: linear-gradient(135deg, #4CAF50, #66BB6A);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 4px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s ease;
    }
    
    .quick-action-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
    }
    
    /* Status indicators */
    .status-online {
        color: #4CAF50;
        font-weight: 600;
    }
    
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        margin: 0.5rem 0;
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": "🌱 Hello! I'm AgriAid, your intelligent agricultural assistant. I'm here to help you with crop management, pest control, weather insights, and farming best practices. How can I assist you today?",
            "timestamp": datetime.now()
        }
    ]

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'name': 'Farmer',
        'location': 'Unknown',
        'primary_crops': ['Not specified'],
        'farm_size': 'Not specified'
    }

# Header
st.markdown("""
<div class="header-container">
    <h1 class="header-title">🌱 AgriAid</h1>
    <p class="header-subtitle">Your Intelligent Agricultural Assistant</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 👤 Farmer Profile")
    
    # User profile section
    with st.container():
        name = st.text_input("Name", value=st.session_state.user_profile['name'])
        location = st.text_input("Location", value=st.session_state.user_profile['location'])
        crops = st.text_input("Primary Crops", value=", ".join(st.session_state.user_profile['primary_crops']))
        farm_size = st.text_input("Farm Size", value=st.session_state.user_profile['farm_size'])
        
        if st.button("Update Profile", type="primary"):
            st.session_state.user_profile.update({
                'name': name,
                'location': location,
                'primary_crops': [crop.strip() for crop in crops.split(',')],
                'farm_size': farm_size
            })
            st.success("Profile updated!")
    
    st.markdown("---")
    
    # Weather Widget (Mock data)
    st.markdown("### 🌤️ Current Weather")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Temperature", "24°C", "2°C")
    with col2:
        st.metric("Humidity", "68%", "-5%")
    
    st.metric("Rainfall (7 days)", "15mm", "12mm")
    
    st.markdown("---")
    
    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    
    quick_actions = [
        "Check crop health",
        "Pest identification",
        "Weather forecast",
        "Fertilizer advice",
        "Market prices",
        "Irrigation schedule"
    ]
    
    for action in quick_actions:
        if st.button(action, key=f"quick_{action}"):
            st.session_state.messages.append({
                "role": "user",
                "content": f"Help me with {action.lower()}",
                "timestamp": datetime.now()
            })
            st.rerun()
    
    st.markdown("---")
    
    # System Status
    st.markdown("### 📊 System Status")
    st.markdown('<p class="status-online">🟢 Online</p>', unsafe_allow_html=True)
    st.markdown("Last updated: " + datetime.now().strftime("%H:%M"))

# Main chat interface
st.markdown("### 💬 Chat with AgriAid")

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
                <div class="user-message">
                    <strong>You:</strong> {message["content"]}
                    <br><small style="color: #666; font-size: 0.8em;">{message["timestamp"].strftime("%H:%M")}</small>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="ai-message">
                    <strong>AgriAid:</strong> {message["content"]}
                    <br><small style="color: #666; font-size: 0.8em;">{message["timestamp"].strftime("%H:%M")}</small>
                </div>
            """, unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Ask AgriAid anything about farming..."):
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "timestamp": datetime.now()
    })
    
    # Simulate AI response (replace with actual AI integration)
    with st.spinner("AgriAid is thinking..."):
        time.sleep(1)  # Simulate processing time
        
        # Generate contextual response based on user input
        response = process_sms_message(user_phone, prompt)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now()
        })
    
    st.rerun()

def generate_ai_response(user_input, profile):
    """Generate contextual AI responses based on user input"""
    
    user_input_lower = user_input.lower()
    
    # Context-aware responses
    responses = {
        'weather': f"Based on current conditions in {profile['location']}, here's what I recommend: The temperature is favorable for your {', '.join(profile['primary_crops'])}. With 68% humidity and recent rainfall, consider adjusting irrigation schedules. Would you like a detailed 7-day forecast?",
        
        'pest': f"🐛 For pest management in {', '.join(profile['primary_crops'])}, I recommend regular scouting. Common pests this season include aphids and caterpillars. Would you like me to help identify a specific pest or provide organic control methods?",
        
        'fertilizer': f"🌿 For your {profile['farm_size']} farm growing {', '.join(profile['primary_crops'])}, I suggest soil testing first. Generally, a balanced NPK ratio works well, but let me know your soil type for specific recommendations.",
        
        'irrigation': f"💧 Based on current weather (68% humidity, recent 15mm rainfall), your irrigation needs are moderate. For {', '.join(profile['primary_crops'])}, I recommend checking soil moisture levels. Would you like a custom irrigation schedule?",
        
        'market': f"📈 Current market trends show good prices for {', '.join(profile['primary_crops'])} in {profile['location']}. Premium quality crops are fetching 15-20% above average. Would you like specific pricing data or harvest timing advice?",
        
        'health': f"🌱 For crop health assessment of your {', '.join(profile['primary_crops'])}, look for: leaf discoloration, growth patterns, and pest signs. Share photos if you notice any issues, and I'll help diagnose problems.",
    }
    
    # Match user input to appropriate response
    for keyword, response in responses.items():
        if keyword in user_input_lower:
            return response
    
    # Default helpful response
    return f"I'm here to help with your agricultural needs! As an expert in farming, I can assist with crop management, pest control, weather planning, and more. Your profile shows you're growing {', '.join(profile['primary_crops'])} - what specific challenge are you facing today?"

# Footer with additional features
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <h4>🌾 Crop Monitor</h4>
        <p>Track your crop health and growth stages with AI-powered insights.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <h4>🌡️ Weather Alerts</h4>
        <p>Get personalized weather warnings and farming recommendations.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <h4>📊 Analytics</h4>
        <p>View detailed reports on yield predictions and farm performance.</p>
    </div>
    """, unsafe_allow_html=True)

# Sample chart for demonstration
if st.checkbox("Show Sample Analytics", value=False):
    st.markdown("### 📈 Sample Farm Analytics")
    
    # Create sample data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='M')
    crop_yield = [random.randint(80, 120) for _ in range(len(dates))]
    
    fig = px.line(
        x=dates, 
        y=crop_yield,
        title="Monthly Crop Yield Trends",
        labels={'x': 'Month', 'y': 'Yield (%)'}
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)

# Clear chat button
if st.button("🗑️ Clear Chat History", type="secondary"):
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": "🌱 Chat cleared! I'm AgriAid, ready to help you with your agricultural needs. What would you like to know?",
            "timestamp": datetime.now()
        }
    ]
    st.rerun()