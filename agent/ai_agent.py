from typing import Annotated, Sequence, TypedDict, Optional, Dict, Any, List
from datetime import datetime, timedelta
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
import redis
import pymongo
import json
import uuid
from dataclasses import dataclass
import asyncio

from agri_centers.agri_center_operations import register_agro_center, get_centers_by_location, get_user_centers, update_agro_center, delete_agro_center, rate_agro_center, get_top_rated_centers
from farmers.farmer_operations import register_farmer_location, get_farmer_locations, delete_farmer_location, get_farmers_in_location, get_farmer_recommended_centers, is_farmer_registered_in_ward
from NDVI.ndvi_analysis import ndvi_analysis_for_ai
from regions.get_region import get_counties, get_subcounties, get_wards, get_ward_data
from weather.weather_data import get_weather_for_farmer
from soil.region_soil_data import get_soil_data_for_ai_agent
from users.user import register_user, get_user_by_phone_number, update_user_name, delete_user
from models.models import SessionConfig
from SMS.sms import send_message


load_dotenv()

# State and Session Management
class AgentState(TypedDict):
    """Agent state for LangGraph"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    user_phone: str
    message_count: int
    session_start: datetime

class SessionData(TypedDict):
    """Session data structure for storage"""
    session_id: str
    user_phone: str
    messages: List[Dict[str, Any]]
    message_count: int
    session_start: str
    last_activity: str
    is_active: bool

tools = [tool(register_agro_center), tool(get_centers_by_location), tool(get_user_centers),
         tool(update_agro_center), tool(delete_agro_center), tool(rate_agro_center), tool(get_top_rated_centers),
         tool(register_farmer_location), tool(get_farmer_locations), tool(delete_farmer_location),
         tool(get_farmers_in_location), tool(get_farmer_recommended_centers), tool(is_farmer_registered_in_ward),
         tool(ndvi_analysis_for_ai), tool(get_counties), tool(get_subcounties), tool(get_wards), tool(get_ward_data),
         tool(get_weather_for_farmer), tool(get_soil_data_for_ai_agent),
         tool(register_user), tool(get_user_by_phone_number), tool(update_user_name), tool(delete_user),
         tool(send_message)]

# Database connections
def get_redis_client() -> redis.Redis:
    """Initialize Redis client"""
    return redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_mongo_client() -> pymongo.MongoClient:
    """Initialize MongoDB client"""
    return pymongo.MongoClient('mongodb://localhost:27017/')

# Session management functions
def create_session_id() -> str:
    """Generate unique session ID"""
    return str(uuid.uuid4())

def get_session_key(user_phone: str, session_id: str) -> str:
    """Create Redis key for session"""
    return f"sms_session:{user_phone}:{session_id}"

def get_user_sessions_key(user_phone: str) -> str:
    """Create Redis key for user's daily sessions"""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"user_sessions:{user_phone}:{today}"

def check_rate_limits(user_phone: str, redis_client: redis.Redis, config: SessionConfig) -> tuple[bool, str]:
    """Check if user can start new session"""
    # Check daily session limit
    sessions_today = redis_client.get(get_user_sessions_key(user_phone))
    sessions_count = int(sessions_today) if sessions_today else 0
    
    if sessions_count >= config.max_sessions_per_day:
        return False, f"Daily limit reached. You can have {config.max_sessions_per_day} sessions per day. Try again tomorrow."
    
    # Check if there's an active session
    active_session = get_active_session(user_phone, redis_client)
    if active_session:
        time_since_last = datetime.now() - datetime.fromisoformat(active_session['last_activity'])
        if time_since_last.total_seconds() < config.session_timeout_minutes * 60:
            return False, f"Please wait {config.session_timeout_minutes} minutes before starting a new session."
    
    return True, ""

def get_active_session(user_phone: str, redis_client: redis.Redis) -> Optional[SessionData]:
    """Get user's active session if exists"""
    # This is a simplified version - you might want to store active session IDs separately
    keys = redis_client.keys(f"sms_session:{user_phone}:*")
    for key in keys:
        session_data = redis_client.get(key)
        if session_data:
            session = json.loads(session_data)
            if session['is_active']:
                return session
    return None

def save_session(session_data: SessionData, redis_client: redis.Redis, config: SessionConfig):
    """Save session to Redis"""
    key = get_session_key(session_data['user_phone'], session_data['session_id'])
    redis_client.setex(
        key, 
        config.session_duration_hours * 3600,  # TTL in seconds
        json.dumps(session_data, default=str)
    )

def load_session(user_phone: str, session_id: str, redis_client: redis.Redis) -> Optional[SessionData]:
    """Load session from Redis"""
    key = get_session_key(user_phone, session_id)
    session_data = redis_client.get(key)
    return json.loads(session_data) if session_data else None

def increment_daily_sessions(user_phone: str, redis_client: redis.Redis):
    """Increment user's daily session count"""
    key = get_user_sessions_key(user_phone)
    redis_client.incr(key)
    redis_client.expire(key, 86400)  # Expire after 24 hours

def create_welcome_message(config: SessionConfig) -> str:
    """Create welcome message for new session"""
    return (f"Welcome to AgriAid! 🌱\n"
            f"Session: {config.session_duration_hours}h, "
            f"Max {config.max_messages_per_session} messages.\n"
            )

def create_session_end_message() -> str:
    """Create session end message"""
    return "Session ended. Thank you for using AgriAid! Start a new session anytime. 🌾"

def should_end_session(session_data: SessionData, config: SessionConfig) -> tuple[bool, str]:
    """Check if session should end"""
    # Check message limit
    if session_data['message_count'] >= config.max_messages_per_session:
        return True, f"Message limit ({config.max_messages_per_session}) reached. " + create_session_end_message()
    
    # Check time limit
    session_start = datetime.fromisoformat(session_data['session_start'])
    if datetime.now() - session_start > timedelta(hours=config.session_duration_hours):
        return True, f"Session time ({config.session_duration_hours}h) expired. " + create_session_end_message()
    
    return False, ""

# LangGraph agent functions
def create_model(tools):
    """Create the language model with tools"""
    model = ChatOpenAI(model="gpt-4o", temperature=0.1).bind_tools(tools)
    return model

def model_call(state: AgentState) -> AgentState:
    """Main model call function"""
    system_prompt = SystemMessage(content=
        "You are AgriAid, an intelligent assistant designed to help users with agricultural questions and issues, communicating via SMS.. \
            Your goal is to provide accurate, actionable, and empathetic advice to farmers, gardeners, and agricultural professionals. "
        "Keep responses under 300 characters when possible. Be helpful, concise, and practical. "
        "Focus on actionable farming advice. Use simple language suitable for farmers. "
        "If you need to use tools, do so to provide accurate information."
        "If a user asked something and you can't get it from the tools use your training data. \
            Also, if a user seems to have an issue that requires help from an agriculture specialist get the nearest agriculture centers information \
                and contact and send together with recommended advice - this can happen in several ways e.g user can ask about pest issue or disease."
        "A user may provide a county, subcounty, or ward name and they might misspell it, so you should try to match it with the correct name. \
            That means you always should check if the provided county, subcounty, or ward name exists in the database before passing it to other tools. \
                Meaning you should use the get_counties, get_subcounties, and get_wards tools to check if the provided names exist. \
                    If they don't exist, but you find similar matches that's from county to subcounty to ward then comfirm with the user \
                        if the match is what they intended if not then inform them the provided location doesn't exist also inform them if no similar matches were found."
        "Also if the user provides their phone number without a country code, you should assume it's a Kenyan number and add the country code +254.\
            But also note if the number starts with 0 then you should remove the 0 and add the country code +254. "
        "If a user asks for a functionality that is not available, politely inform them that the feature is not supported yet. "
        f"Also the user's phone number is {state['user_phone']}. You can use this phone number for the tools that require it.\
            But it's different from the phone number for the agriculture centers contact number but it's the registrar's number so don't ask for the registrar's number.."
        f"In the beginning of a message you should check if the user exists using the get_user_by_phone_number tool and pass in the user's phone number - {state['user_phone']}  and if they don't ask them if they want to register and decide if you want to register them or not based their response. "
        "Use their name in the welcome message if they are registered."
        "If a user wants to register a new agro center or farmer location first confirm if they are registered and if they are not ask them if they want to register and then register them. Then proceed with the registration of their agro centers or farms. "
        "If a user asks for planting advice, use the ndvi_analysis_for_ai tool to analyze the NDVI data for their farm plus any training data you have and weather tools if necessary. "
        "Also, if a user is new give them a brief overview of what services you provide, based on the tools and your internal data, and how you can help them. "
        "If a user asks you to contact an agriculture center, you should use the send_message tool to send them a clear message but it should clearly be about help in regard to agriculture if not advise the user to ask about something in that sector. And also ask the user if they are willing for us to share their phone number that is the current user with the center for the center to contact them back. If not then inform them that you can't contact the center without sharing their phone number. "
        "Do not update anyone's information if they are not the current user. For example, don't update an agro center if the user is not the registrar of that center, same to farmer location or user information. "
    )
    
    model = create_model(tools)
    response = model.invoke([system_prompt] + state["messages"])
    
    return {
        "messages": [response],
        "message_count": state["message_count"] + 1
    }

def should_continue(state: AgentState) -> str:
    """Determine if conversation should continue"""
    messages = state["messages"]
    last_message = messages[-1]
    
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"

def create_agent_graph():
    """Create the LangGraph agent"""
    graph = StateGraph(state_schema=AgentState)
    
    # Add nodes
    graph.add_node("agent", model_call)
    tool_node = ToolNode(tools=tools)
    graph.add_node("tools", tool_node)
    
    # Add edges
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    graph.add_edge("tools", "agent")
    
    return graph.compile()

def truncate_message(message: str, max_length: int = 160) -> str:
    """Truncate message to SMS length"""
    if len(message) <= max_length:
        return message
    return message[:max_length-3] + "..."

def process_sms_message(
    user_phone: str, 
    message_text: str, 
    config: SessionConfig = SessionConfig()
) -> str:
    """Main function to process incoming SMS message"""
    redis_client = get_redis_client()
    
    try:
        # Check for active session
        active_session = get_active_session(user_phone, redis_client)
        
        if not active_session:
            # Check rate limits for new session
            can_start, limit_message = check_rate_limits(user_phone, redis_client, config)
            if not can_start:
                return limit_message
            
            # Create new session
            session_id = create_session_id()
            session_data = SessionData(
                session_id=session_id,
                user_phone=user_phone,
                messages=[],
                message_count=0,
                session_start=datetime.now().isoformat(),
                last_activity=datetime.now().isoformat(),
                is_active=True
            )
            
            increment_daily_sessions(user_phone, redis_client)
            
            # Send welcome message first
            welcome_msg = create_welcome_message(config)
            
            # Process the actual message
            session_data['message_count'] = 1
            session_data['messages'].append({
                'type': 'human',
                'content': message_text,
                'timestamp': datetime.now().isoformat()
            })
            
        else:
            session_data = active_session
            
            # Check if session should end
            should_end, end_message = should_end_session(session_data, config)
            if should_end:
                session_data['is_active'] = False
                save_session(session_data, redis_client, config)
                return end_message
            
            session_data['message_count'] += 1
            session_data['messages'].append({
                'type': 'human',
                'content': message_text,
                'timestamp': datetime.now().isoformat()
            })
        
        # Prepare messages for agent
        messages = []
        for msg in session_data['messages'][-config.max_messages_per_session:]:  # Keep last 10 messages for context
            if msg['type'] == 'human':
                messages.append(HumanMessage(content=msg['content']))
            elif msg['type'] == 'ai':
                messages.append(AIMessage(content=msg['content']))
        
        # Add current message if not already added
        if not messages or messages[-1].content != message_text:
            messages.append(HumanMessage(content=message_text))
        
        # Create agent state
        agent_state = AgentState(
            messages=messages,
            session_id=session_data['session_id'],
            user_phone=user_phone,
            message_count=session_data['message_count'],
            session_start=datetime.fromisoformat(session_data['session_start'])
        )
        
        # Run agent
        agent = create_agent_graph()
        result = agent.invoke(agent_state)
        
        # Get AI response
        ai_message = result["messages"][-1].content
        # ai_message = truncate_message(ai_message, config.max_sms_length)
        
        # Update session with AI response
        session_data['messages'].append({
            'type': 'ai',
            'content': ai_message,
            'timestamp': datetime.now().isoformat()
        })
        session_data['last_activity'] = datetime.now().isoformat()
        
        # Save updated session
        save_session(session_data, redis_client, config)
        
        # Return response (prepend welcome message for new sessions)
        if not active_session:
            return f"{welcome_msg}\n\n{ai_message}"
        
        return ai_message
        
    except Exception as e:
        return f"Sorry, I encountered an error. Please try again. Error: {str(e)[:50]}"
    
    finally:
        redis_client.close()

# Example usage and testing
def main():
    """Example usage"""
    config = SessionConfig(
        max_messages_per_session=30,  # Lower for testing
        session_duration_hours=1,
        max_sessions_per_day=10
    )
    
    user_phone = "+123455980"

    while True:
        user_input = input("\nEnter your message (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        response = process_sms_message(user_phone, user_input, config)
        print(f"\nAgriAid: {response}\n")

if __name__ == "__main__":
    # Run example
    asyncio.run(main())