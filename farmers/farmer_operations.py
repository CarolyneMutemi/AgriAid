# ================================
# FARMER LOCATION MANAGEMENT
# ================================

from typing import List, Dict
from datetime import datetime
import json
from langchain_core.tools import tool

from db.db_manager import db_manager
from models.models import Location, FarmerLocation, AgroCenter
from models.models import RegistrationResponse

from .utils import generate_farmer_registration_id, _clear_farmer_cache
from agri_centers.agri_center_operations import get_top_rated_centers


def register_farmer_location(
    farmer_phone: str,
    farmer_name: str,
    county: str,
    subcounty: str,
    ward: str,
    farm_description: str = ""
) -> RegistrationResponse:
    """Register a farmer to a specific ward location"""
    location = Location(
        county=county,
        subcounty=subcounty,
        ward=ward
    )
    try:
        # Generate registration ID
        registration_id = generate_farmer_registration_id(farmer_phone, location)
        
        # Check if farmer is already registered in this ward
        existing = db_manager.farmers_collection.find_one({
            "registration_id": registration_id,
            "active": True
        })
        
        if existing:
            return RegistrationResponse(
                success=False,
                message=f"You are already registered in {location.ward} ward, {location.subcounty}.",
                errors=["Duplicate registration"]
            )
        
        # Create new farmer location registration
        farmer_location = FarmerLocation(
            registration_id=registration_id,
            farmer_phone=farmer_phone,
            farmer_name=farmer_name,
            location=location,
            farm_description=farm_description or f"Farm in {location.ward}"
        )
        
        # Save to database
        db_manager.farmers_collection.insert_one(farmer_location.to_dict())
        
        # Clear farmer's location cache
        _clear_farmer_cache(farmer_phone)
        
        return RegistrationResponse(
            success=True,
            message=f"Successfully registered to {location.ward}, {location.subcounty}, {location.county}!",
            center_id=registration_id  # Reusing field for registration_id
        )
        
    except Exception as e:
        return RegistrationResponse(
            success=False,
            message="Registration failed due to system error.",
            errors=[str(e)]
        )


def get_farmer_locations(
    farmer_phone: str
) -> List[FarmerLocation]:
    """Get all locations where a farmer is registered"""
    cache_key = f"farmer_locations:{farmer_phone}"
    
    # Try cache first
    cached = db_manager.redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        return [FarmerLocation.from_dict(loc) for loc in data]
    
    # Query database
    locations_data = db_manager.farmers_collection.find({
        "farmer_phone": farmer_phone,
        "active": True
    }).sort("created_at", -1)
    
    locations = [FarmerLocation.from_dict(data) for data in locations_data]
    
    # Cache for 30 minutes
    db_manager.redis_client.setex(
        cache_key,
        1800,
        json.dumps([loc.to_dict() for loc in locations])
    )
    
    return locations


def delete_farmer_location(
    farmer_phone: str,
    registration_id: str
) -> RegistrationResponse:
    """Delete a farmer's location registration"""
    try:
        # Verify ownership
        farmer_location = db_manager.farmers_collection.find_one({
            "registration_id": registration_id,
            "farmer_phone": farmer_phone,
            "active": True
        })
        
        if not farmer_location:
            return RegistrationResponse(
                success=False,
                message="Location registration not found or already removed.",
                errors=["Registration not found"]
            )
        
        # Soft delete
        db_manager.farmers_collection.update_one(
            {"registration_id": registration_id},
            {
                "$set": {
                    "active": False,
                    "updated_at": datetime.now().isoformat()
                }
            }
        )
        
        # Clear farmer's cache
        _clear_farmer_cache(farmer_phone)
        
        location = Location.from_dict(farmer_location["location"])
        return RegistrationResponse(
            success=True,
            message=f"Successfully removed registration from {location.ward}, {location.subcounty}.",
            center_id=registration_id
        )
        
    except Exception as e:
        return RegistrationResponse(
            success=False,
            message="Deletion failed due to system error.",
            errors=[str(e)]
        )


def get_farmers_in_location(
    county: str,
    subcounty: str,
    ward: str
) -> int:
    """Get count of farmers registered in a specific location"""
    location = Location(county=county, subcounty=subcounty, ward=ward)
    count = db_manager.farmers_collection.count_documents({
        "location.county": location.county,
        "location.subcounty": location.subcounty,
        "location.ward": location.ward,
        "active": True
    })
    
    return count


def get_farmer_recommended_centers(
    farmer_phone: str,
    limit: int = 3
) -> Dict[str, List[AgroCenter]]:
    """Get recommended agro centers based on farmer's registered locations"""
    farmer_locations = get_farmer_locations(db_manager, farmer_phone)
    
    if not farmer_locations:
        return {}
    
    recommendations = {}
    
    for farmer_location in farmer_locations:
        location_key = f"{farmer_location.location.ward}, {farmer_location.location.subcounty}"
        top_centers = get_top_rated_centers(db_manager, farmer_location.location, limit)
        
        if top_centers:
            recommendations[location_key] = top_centers
    
    return recommendations


def is_farmer_registered_in_ward(
    farmer_phone: str,
    county: str,
    subcounty: str,
    ward: str
) -> bool:
    """Check if farmer is registered in a specific ward"""
    location = Location(county=county, subcounty=subcounty, ward=ward)
    registration_id = generate_farmer_registration_id(farmer_phone, location)
    
    existing = db_manager.farmers_collection.find_one({
        "registration_id": registration_id,
        "active": True
    })
    
    return existing is not None
