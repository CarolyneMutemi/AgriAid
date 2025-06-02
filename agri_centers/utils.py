import hashlib
from models.models import Location, AgroCenter
from db.db_manager import db_manager

def generate_center_id(location: Location, contact_number: str) -> str:
    """Generate unique center ID"""
    data = f"{location.county}_{location.subcounty}_{location.ward}_{contact_number}"
    return hashlib.md5(data.encode()).hexdigest()[:12]

def _clear_location_cache( location: Location):
    """Clear cache for a specific location"""
    pattern = f"centers:{location.county}:{location.subcounty}:{location.ward}:*"
    top_pattern = f"top_centers:{location.county}:{location.subcounty}:{location.ward}:*"
    
    for key in db_manager.redis_client.scan_iter(match=pattern):
        db_manager.redis_client.delete(key)
    
    for key in db_manager.redis_client.scan_iter(match=top_pattern):
        db_manager.redis_client.delete(key)

def _update_center_rating(
     
    center_id: str, 
    rating_change: float, 
    is_new_rating: bool
):
    """Update center's aggregated rating"""
    if is_new_rating:
        # New rating
        db_manager.centers_collection.update_one(
            {"center_id": center_id},
            {
                "$inc": {
                    "rating.total_ratings": 1,
                    "rating.total_score": rating_change
                }
            }
        )
    else:
        # Updated rating
        db_manager.centers_collection.update_one(
            {"center_id": center_id},
            {
                "$inc": {
                    "rating.total_score": rating_change
                }
            }
        )
    
    # Recalculate average
    center = db_manager.centers_collection.find_one({"center_id": center_id})
    if center and center["rating"]["total_ratings"] > 0:
        new_average = center["rating"]["total_score"] / center["rating"]["total_ratings"]
        db_manager.centers_collection.update_one(
            {"center_id": center_id},
            {"$set": {"rating.average_rating": round(new_average, 2)}}
        )

def format_center_for_ussd(center: AgroCenter, include_rating: bool = True) -> str:
    """Format center info for USSD display (character limit friendly)"""
    rating_text = f" ⭐{center.rating.average_rating:.1f}({center.rating.total_ratings})" if include_rating and center.rating.total_ratings > 0 else ""
    
    return f"{center.name}{rating_text}\n📞 {center.contact_number}\n📝 {center.description[:50]}..."

def format_center_for_sms(center: AgroCenter) -> str:
    """Format center info for SMS (more detailed)"""
    rating_text = f"\nRating: ⭐{center.rating.average_rating:.1f}/5 ({center.rating.total_ratings} reviews)" if center.rating.total_ratings > 0 else "\nRating: No reviews yet"
    
    days = ", ".join([day.value[:3] for day in center.availability.days])
    availability = f"{days} {center.availability.start_time.strftime('%H:%M')}-{center.availability.end_time.strftime('%H:%M')}"
    
    return f"""🌾 {center.name}
📞 Contact: {center.contact_number}
📍 {center.location.ward}, {center.location.subcounty}
📝 {center.description}
🕒 Available: {availability}{rating_text}
ID: {center.center_id}"""
