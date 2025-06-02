import json
from datetime import datetime
from typing import Optional

from db.db_manager import db_manager
from models.models import UserSession

# ================================
# SESSION MANAGEMENT
# ================================

def get_user_session(phone_number: str) -> Optional[UserSession]:
    """Get user session from cache"""
    session_data = db_manager.redis_client.get(f"session:{phone_number}")
    if session_data:
        data = json.loads(session_data)
        return UserSession(
            phone_number=data["phone_number"],
            current_step=data["current_step"],
            data=data["data"],
            pagination_offset=data.get("pagination_offset", 0),
            last_activity=datetime.fromisoformat(data["last_activity"])
        )
    return None

def save_user_session(session: UserSession):
    """Save user session to cache"""
    session_data = {
        "phone_number": session.phone_number,
        "current_step": session.current_step,
        "data": session.data,
        "pagination_offset": session.pagination_offset,
        "last_activity": datetime.now().isoformat()
    }
    
    db_manager.redis_client.setex(
        f"session:{session.phone_number}",
        3600,  # 1 hour session timeout
        json.dumps(session_data)
    )

def clear_user_session(phone_number: str):
    """Clear user session"""
    db_manager.redis_client.delete(f"session:{phone_number}")
