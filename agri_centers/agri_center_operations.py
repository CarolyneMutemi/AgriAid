"""
Agriculture Centers USSD/SMS AI Agent System
===========================================

System Architecture:
- USSD: Fast cached responses for browsing/selection
- SMS: Detailed confirmations and database operations
- MongoDB: Long-term storage
- Redis: Caching and session management
- Functional design with dataclasses for typing
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, time
import json
from langchain_core.tools import tool

from db.db_manager import db_manager
from models.models import DayOfWeek, Location, AgroCenter, Availability
from models.models import RegistrationResponse, SearchResponse
from .utils import generate_center_id, _clear_location_cache, _update_center_rating

# ================================
# CORE AGRO CENTERS FUNCTIONS
# ================================


def register_agro_center(
    name: str,
    contact_number: str,
    registrar_number: str,
    county: str,
    subcounty: str,
    ward: str,
    description: str,
    availability: str
) -> RegistrationResponse:
    """
    Register a new agro center
    - name: Name of the center
    - contact_number: Contact number for the center
    - registrar_number: Phone number of the registrar (user registering the center)
    - county: County where the center is located
    - subcounty: Subcounty where the center is located
    - ward: Ward where the center is located
    - description: Brief description of the center
    - availability: string representation of availability (e.g. "Mon-Fri 8:00-17:00")
    Returns a RegistrationResponse indicating success or failure
    """
    location = Location(
        county=county,
        subcounty=subcounty,
        ward=ward
    )
    try:
        # Check ward limit (max 5 centers per ward)
        ward_count = db_manager.centers_collection.count_documents({
            "location.county": location.county,
            "location.subcounty": location.subcounty,
            "location.ward": location.ward,
            "active": True
        })
        
        if ward_count >= 5:
            return RegistrationResponse(
                success=False,
                message="Maximum 5 centers allowed per ward. Registration failed.",
                errors=["Ward limit exceeded"]
            )
        
        # Generate center ID
        center_id = generate_center_id(location, contact_number)
        print(f"Generated center ID: {center_id}")
        
        # Check if center already exists
        existing = db_manager.centers_collection.find_one({
            "center_id": center_id,
            "active": True
        })
        
        if existing:
            return RegistrationResponse(
                success=False,
                message="Center with this contact and location already exists.",
                errors=["Duplicate center"]
            )
        
        # Create new center
        new_center = AgroCenter(
            center_id=center_id,
            name=name,
            contact_number=contact_number,
            registrar_number=registrar_number,
            location=location,
            description=description,
            availability=availability
        )

        print(f"New center data: {new_center}")
        print(f"New center data: {new_center.to_dict()}")
        
        # Save to database
        db_manager.centers_collection.insert_one(new_center.to_dict())
        
        # Clear relevant caches
        _clear_location_cache(location)
        
        return RegistrationResponse(
            success=True,
            message=f"Center '{name}' registered successfully! ID: {center_id}",
            center_id=center_id
        )
        
    except Exception as e:
        print(f"Error during registration: {e}")
        return RegistrationResponse(
            success=False,
            message=f"Registration failed due to system error: {e}.",
            errors=[str(e)]
        )


def get_centers_by_location(
    county: str,
    subcounty: str,
    ward: str,
    offset: int = 0,
    limit: int = 5,
    sort_by_rating: bool = True
) -> SearchResponse:
    """Get agro centers by location with pagination"""
    print(f"Fetching centers for {county}, {subcounty}, {ward} with offset={offset}, limit={limit}, sort_by_rating={sort_by_rating}")
    location = Location(county=county, subcounty=subcounty, ward=ward)
    cache_key = f"centers:{location.county}:{location.subcounty}:{location.ward}:{offset}:{limit}:{sort_by_rating}"
    
    # Try cache first for USSD speed
    cached = db_manager.redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        return SearchResponse(
            centers=[AgroCenter.from_dict(c) for c in data["centers"]],
            total_count=data["total_count"],
            has_more=data["has_more"],
            next_offset=data["next_offset"]
        )
    
    # Query database
    query = {
        "location.county": location.county,
        "location.subcounty": location.subcounty,
        "location.ward": location.ward,
        "active": True
    }
    
    sort_criteria = [("rating.average_rating", -1)] if sort_by_rating else [("created_at", -1)]
    
    cursor = db_manager.centers_collection.find(query).sort(sort_criteria)
    total_count = db_manager.centers_collection.count_documents(query)
    
    centers_data = list(cursor.skip(offset).limit(limit))
    centers = [AgroCenter.from_dict(data) for data in centers_data]
    
    has_more = (offset + limit) < total_count
    next_offset = offset + limit if has_more else offset
    
    # Cache result
    cache_data = {
        "centers": [c.to_dict() for c in centers],
        "total_count": total_count,
        "has_more": has_more,
        "next_offset": next_offset
    }
    
    db_manager.redis_client.setex(cache_key, db_manager.cache_ttl, json.dumps(cache_data))
    
    return SearchResponse(
        centers=centers,
        total_count=total_count,
        has_more=has_more,
        next_offset=next_offset
    )


def get_user_centers(
    registrar_number: str
) -> List[AgroCenter]:
    """Get all centers registered by a user"""
    centers_data = db_manager.centers_collection.find({
        "registrar_number": registrar_number,
        "active": True
    }).sort("created_at", -1)
    
    return [AgroCenter.from_dict(data) for data in centers_data]


def update_agro_center(
    center_id: str,
    registrar_number: str,
    contact_number: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    availability: Optional[str] = None
) -> RegistrationResponse:
    """
    Update an existing agro center
    If one wants to change the location, they must delete and re-register.
    """
    updates = {}
    if contact_number:
        updates["contact_number"] = contact_number
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if availability:
        updates["availability"] = availability
    if not updates:
        return RegistrationResponse(
            success=False,
            message="No updates provided.",
            errors=["No fields to update"]
        )
    try:
        # Verify ownership
        center = db_manager.centers_collection.find_one({
            "center_id": center_id,
            "registrar_number": registrar_number,
            "active": True
        })
        
        if not center:
            return RegistrationResponse(
                success=False,
                message="Center not found or you don't have permission to edit it.",
                errors=["Center not found or no permission"]
            )
        
        # Prepare update data
        update_data = {
            **updates,
            "updated_at": datetime.now().isoformat()
        }
        
        # Update database
        db_manager.centers_collection.update_one(
            {"center_id": center_id},
            {"$set": update_data}
        )
        
        # Clear caches
        location = Location.from_dict(center["location"])
        _clear_location_cache(location)
        
        return RegistrationResponse(
            success=True,
            message="Center updated successfully!",
            center_id=center_id
        )
        
    except Exception as e:
        return RegistrationResponse(
            success=False,
            message="Update failed due to system error.",
            errors=[str(e)]
        )


def delete_agro_center(
    center_id: str,
    registrar_number: str
) -> RegistrationResponse:
    """Soft delete an agro center"""
    try:
        # Verify ownership
        center = db_manager.centers_collection.find_one({
            "center_id": center_id,
            "registrar_number": registrar_number,
            "active": True
        })
        
        if not center:
            return RegistrationResponse(
                success=False,
                message="Center not found or you don't have permission to delete it.",
                errors=["Center not found or no permission"]
            )
        
        # Soft delete
        db_manager.centers_collection.update_one(
            {"center_id": center_id},
            {
                "$set": {
                    "active": False,
                    "updated_at": datetime.now().isoformat()
                }
            }
        )
        
        # Clear caches
        location = Location.from_dict(center["location"])
        _clear_location_cache(location)
        
        return RegistrationResponse(
            success=True,
            message="Center deleted successfully!",
            center_id=center_id
        )
        
    except Exception as e:
        return RegistrationResponse(
            success=False,
            message="Deletion failed due to system error.",
            errors=[str(e)]
        )


def rate_agro_center(
    center_id: str,
    rating: float,
    rater_phone: str
) -> RegistrationResponse:
    """Rate an agro center (1-5 stars)"""
    try:
        if not (1 <= rating <= 5):
            return RegistrationResponse(
                success=False,
                message="Rating must be between 1 and 5.",
                errors=["Invalid rating"]
            )
        
        # Check if user already rated this center
        existing_rating = db_manager.ratings_collection.find_one({
            "center_id": center_id,
            "rater_phone": rater_phone
        })
        
        if existing_rating:
            # Update existing rating
            old_rating = existing_rating["rating"]
            db_manager.ratings_collection.update_one(
                {"_id": existing_rating["_id"]},
                {
                    "$set": {
                        "rating": rating,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            rating_change = rating - old_rating
        else:
            # Create new rating
            db_manager.ratings_collection.insert_one({
                "center_id": center_id,
                "rater_phone": rater_phone,
                "rating": rating,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
            rating_change = rating
        
        # Update center's rating summary
        _update_center_rating(center_id, rating_change, not existing_rating)
        
        return RegistrationResponse(
            success=True,
            message=f"Thank you for rating! Your {rating}-star rating has been recorded.",
            center_id=center_id
        )
        
    except Exception as e:
        return RegistrationResponse(
            success=False,
            message="Rating failed due to system error.",
            errors=[str(e)]
        )


def get_top_rated_centers(
    county: str,
    subcounty: str,
    ward: str,
    limit: int = 3
) -> List[AgroCenter]:
    """Get top-rated centers for quick USSD response"""
    location = Location(county=county, subcounty=subcounty, ward=ward)
    cache_key = f"top_centers:{location.county}:{location.subcounty}:{location.ward}:{limit}"
    
    cached = db_manager.redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        return [AgroCenter.from_dict(c) for c in data]
    
    centers_data = db_manager.centers_collection.find({
        "location.county": location.county,
        "location.subcounty": location.subcounty,
        "location.ward": location.ward,
        "active": True,
        "rating.total_ratings": {"$gt": 0}  # Only centers with ratings
    }).sort([
        ("rating.average_rating", -1),
        ("rating.total_ratings", -1)
    ]).limit(limit)
    
    centers = [AgroCenter.from_dict(data) for data in centers_data]
    
    # Cache for 30 minutes
    db_manager.redis_client.setex(
        cache_key, 
        1800, 
        json.dumps([c.to_dict() for c in centers])
    )
    
    return centers

# ================================
# USAGE EXAMPLE
# ================================

# def example_usage():
#     from farmers.farmer_operations import register_farmer_location, get_farmer_locations, delete_farmer_location, get_farmer_recommended_centers
#     """Example of how to use the system"""
#     # Initialize
    
#     # Register a center
#     location = Location("Nairobi", "Westlands", "Parklands")
#     availability = Availability(
#         days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
#               DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY],
#         start_time=time(8, 0),
#         end_time=time(17, 0)
#     )
    
#     result = register_agro_center(
#         db_manager=db_manager,
#         name="Green Thumb Agriculture Center",
#         contact_number="+254712345678",
#         registrar_number="+254712345678",
#         location=location,
#         description="Expert advice on crop management and pest control",
#         availability=availability
#     )
    
#     print(f"Center Registration: {result.message}")
    
#     # Register a farmer
#     farmer_result = register_farmer_location(
#         db_manager=db_manager,
#         farmer_phone="+254700000001",
#         location=location,
#         farm_description="Tomato and cabbage farm"
#     )
    
#     print(f"Farmer Registration: {farmer_result.message}")
    
#     # Get farmer's locations
#     farmer_locations = get_farmer_locations("+254700000001")
#     print(f"Farmer has {len(farmer_locations)} registered locations")
    
#     # Get recommendations for farmer
#     recommendations = get_farmer_recommended_centers("+254700000001")
#     for location_key, centers in recommendations.items():
#         print(f"Recommendations for {location_key}: {len(centers)} centers")
    
#     # Search centers
#     search_result = get_centers_by_location(location)
#     print(f"Found {len(search_result.centers)} centers")
    
#     # Rate a center
#     if search_result.centers:
#         rating_result = rate_agro_center(
#             
#             search_result.centers[0].center_id, 
#             4.5, 
#             "+254700000000"
#         )
#         print(f"Rating: {rating_result.message}")
        
#     # Delete farmer location
#     # if farmer_locations:
#     #     delete_result = delete_farmer_location(
#     #         db_manager,
#     #         "+254700000001",
#     #         farmer_locations[0].registration_id
#     #     )
#     #     print(f"Delete: {delete_result.message}")

# if __name__ == "__main__":
#     example_usage()