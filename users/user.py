from datetime import datetime
from db.db_manager import db_manager
from typing import Optional, Dict, Any

def register_user(phone_number: str, name: str) -> Dict[str, Any]:
    """Register a new user in the database."""
    user_data = {
        "phone_number": phone_number,
        "name": name,
        "created_at": datetime.now().isoformat()
    }

    # Check if user already exists
    existing_user = db_manager.users_collection.find_one({"phone_number": phone_number})
    if existing_user:
        raise ValueError(f"User with phone number {phone_number} already exists.")
    
    try:
        db_manager.users_collection.insert_one(user_data)
        # cache user data in Redis
        db_manager.redis_client.set(f"user:{phone_number}", user_data, ex=db_manager.cache_ttl)
        return user_data
    except Exception as e:
        raise RuntimeError(f"Failed to register user: {str(e)}")

def get_user_by_phone_number(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    This will mainly be used to check if a user is registered/exists in our database and get their name.
    Retrieves user data from the database by phone number.
    """
    print("Has been called with phone number:", phone_number)
    # Check Redis cache first
    cached_user = db_manager.redis_client.get(f"user:{phone_number}")
    if cached_user:
        return cached_user
    
    # If not in cache, query MongoDB
    user_data = db_manager.users_collection.find_one({"phone_number": phone_number})
    
    if user_data:
        user_data.pop("_id", None)  # Remove MongoDB ObjectId
    return user_data if user_data else None

def update_user_name(phone_number: str, new_name: str) -> Optional[Dict[str, Any]]:
    """Update the user's name in the database."""
    result = db_manager.users_collection.update_one(
        {"phone_number": phone_number},
        {"$set": {"name": new_name}}
    )

    # Clear cache after update
    db_manager.redis_client.delete(f"user:{phone_number}")
    
    if result.modified_count > 0:
        return get_user_by_phone_number(phone_number)
    return None

def delete_user(phone_number: str) -> bool:
    """Delete a user from the database by phone number."""
    # Clear cache before deletion
    db_manager.redis_client.delete(f"user:{phone_number}")
    # Perform deletion in MongoDB
    result = db_manager.users_collection.delete_one({"phone_number": phone_number})
    return result.deleted_count > 0
