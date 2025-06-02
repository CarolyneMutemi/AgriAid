# ================================
# DATA MODELS
# ================================

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, time


@dataclass
class Location:
    county: str
    subcounty: str
    ward: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "county": self.county,
            "subcounty": self.subcounty,
            "ward": self.ward
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        return cls(
            county=data["county"],
            subcounty=data["subcounty"],
            ward=data["ward"]
        )

@dataclass
class FarmerLocation:
    registration_id: str
    farmer_phone: str
    location: Location
    farmer_name: str
    farm_description: str  # Optional description of the farm/crop type
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "registration_id": self.registration_id,
            "farmer_phone": self.farmer_phone,
            "location": self.location.to_dict(),
            "farm_description": self.farm_description,
            "created_at": self.created_at.isoformat(),
            "active": self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FarmerLocation':
        return cls(
            registration_id=data["registration_id"],
            farmer_phone=data["farmer_phone"],
            farmer_name=data.get("farmer_name", ""),
            location=Location.from_dict(data["location"]),
            farm_description=data["farm_description"],
            created_at=datetime.fromisoformat(data["created_at"]),
            active=data.get("active", True)
        )

@dataclass
class User:
    phone_number: str
    name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    farms: List[FarmerLocation] = field(default_factory=list)
    agri_centers: List = field(default_factory=list)  # List of AgroCenter IDs
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone_number": self.phone_number,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "farms": [farm.to_dict() for farm in self.farms],
            "agri_centers": self.agri_centers,
            "active": self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        return cls(
            phone_number=data["phone_number"],
            name=data.get("name", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            active=data.get("active", True)
        )

class DayOfWeek(Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"

@dataclass
class Availability:
    days: List[DayOfWeek]
    start_time: time
    end_time: time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "days": [day.value for day in self.days],
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M")
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Availability':
        return cls(
            days=[DayOfWeek(day) for day in data["days"]],
            start_time=datetime.strptime(data["start_time"], "%H:%M").time(),
            end_time=datetime.strptime(data["end_time"], "%H:%M").time()
        )


@dataclass
class Rating:
    total_ratings: int = 0
    total_score: float = 0.0
    average_rating: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_ratings": self.total_ratings,
            "total_score": self.total_score,
            "average_rating": self.average_rating
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rating':
        return cls(
            total_ratings=data.get("total_ratings", 0),
            total_score=data.get("total_score", 0.0),
            average_rating=data.get("average_rating", 0.0)
        )

@dataclass
class AgroCenter:
    center_id: str
    name: str
    contact_number: str
    registrar_number: str
    location: Location
    description: str
    availability: str
    rating: Rating = field(default_factory=Rating)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "center_id": self.center_id,
            "name": self.name,
            "contact_number": self.contact_number,
            "registrar_number": self.registrar_number,
            "location": self.location.to_dict(),
            "description": self.description,
            "availability": self.availability,
            "rating": self.rating.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "active": self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgroCenter':
        return cls(
            center_id=data["center_id"],
            name=data["name"],
            contact_number=data["contact_number"],
            registrar_number=data["registrar_number"],
            location=Location.from_dict(data["location"]),
            description=data["description"],
            availability=data["availability"],
            rating=Rating.from_dict(data.get("rating", {})),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            active=data.get("active", True)
        )

@dataclass
class UserSession:
    phone_number: str
    current_step: str
    data: Dict[str, Any] = field(default_factory=dict)
    pagination_offset: int = 0
    last_activity: datetime = field(default_factory=datetime.now)

@dataclass
class RegistrationResponse:
    success: bool
    message: str
    center_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)

@dataclass
class SearchResponse:
    centers: List[AgroCenter]
    total_count: int
    has_more: bool
    next_offset: int

# Configuration
@dataclass
class SessionConfig:
    max_messages_per_session: int = 10
    session_duration_hours: int = 1
    max_sessions_per_day: int = 5
    session_timeout_minutes: int = 30  # New session allowed after timeout
    max_sms_length: int = 160  # Standard SMS length
