from pymongo import MongoClient
import redis

class DatabaseManager:
    def __init__(self, mongo_uri: str, redis_host: str = 'localhost', redis_port: int = 6379):
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client.agriculture_db
        self.centers_collection = self.db.agro_centers
        self.ratings_collection = self.db.ratings
        self.farmers_collection = self.db.farmers
        self.users_collection = self.db.users
        
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.cache_ttl = 3600  # 1 hour
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimal performance"""
        # Agro centers indexes
        self.centers_collection.create_index([
            ("location.county", 1),
            ("location.subcounty", 1),
            ("location.ward", 1)
        ])
        self.centers_collection.create_index("registrar_number")
        self.centers_collection.create_index("active")
        self.centers_collection.create_index([("rating.average_rating", -1)])
        
        # Farmer locations indexes
        self.farmers_collection.create_index("farmer_phone")
        self.farmers_collection.create_index([
            ("location.county", 1),
            ("location.subcounty", 1),
            ("location.ward", 1)
        ])
        self.farmers_collection.create_index("active")

db_manager = DatabaseManager("mongodb://localhost:27017/")