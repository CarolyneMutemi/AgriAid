# ================================
# FARMER-SPECIFIC HELPER FUNCTIONS
# ================================


import hashlib
from models.models import Location

from db.db_manager import db_manager
from models.models import Location, FarmerLocation


def generate_farmer_registration_id(farmer_phone: str, location: Location) -> str:
    """Generate unique farmer registration ID"""
    data = f"{farmer_phone}_{location.county}_{location.subcounty}_{location.ward}"
    return hashlib.md5(data.encode()).hexdigest()[:12]

def _clear_farmer_cache(farmer_phone: str):
    """Clear cache for a specific farmer"""
    cache_key = f"farmer_locations:{farmer_phone}"
    db_manager.redis_client.delete(cache_key)

def format_farmer_welcome_message(farmer_location: FarmerLocation) -> str:
    """Format welcome message for a farmer after registration"""
    return f"""Welcome {farmer_location.farmer_name}!"""

def format_farmer_location_for_ussd(farmer_location: FarmerLocation, index: int) -> str:
    """Format farmer location for USSD display"""
    return f"{index}. {farmer_location.location.ward}\n   {farmer_location.location.subcounty}, {farmer_location.location.county}\n   {farmer_location.farm_description}"

def format_farmer_location_for_sms(farmer_location: FarmerLocation) -> str:
    """Format farmer location for SMS"""
    return f"""📍 Location #{farmer_location.registration_id[:6]}
🌾 {farmer_location.farm_description}
📍 {farmer_location.location.ward} Ward
    {farmer_location.location.subcounty}, {farmer_location.location.county}
📅 Registered: {farmer_location.created_at.strftime('%d/%m/%Y')}"""
