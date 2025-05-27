import ee
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


def create_farm_boundary(coordinates, buffer_meters=0):
    """
    Create a farm boundary from coordinates
    
    Parameters:
    coordinates: Can be either:
        - Single point: [longitude, latitude] - will create a small buffer around it
        - Multiple points: [[lon1, lat1], [lon2, lat2], ...] - creates polygon
        - Rectangle: [[min_lon, min_lat], [max_lon, max_lat]] - creates bounding box
    buffer_meters: Buffer distance in meters (useful for point coordinates)
    
    Returns:
    ee.Geometry object representing the farm boundary
    """
    
    if len(coordinates) == 2 and not isinstance(coordinates[0], list):
        # Single point coordinates [longitude, latitude]
        print(f"Creating point boundary at: {coordinates}")
        point = ee.Geometry.Point(coordinates)
        if buffer_meters > 0:
            return point.buffer(buffer_meters)
        else:
            return point.buffer(100)  # Default 100m buffer
    
    elif len(coordinates) == 2 and isinstance(coordinates[0], list):
        # Rectangle coordinates [[min_lon, min_lat], [max_lon, max_lat]]
        print(f"Creating rectangle boundary: {coordinates}")
        min_lon, min_lat = coordinates[0]
        max_lon, max_lat = coordinates[1]
        return ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
    
    else:
        # Multiple points forming a polygon
        print(f"Creating polygon boundary with {len(coordinates)} points")
        return ee.Geometry.Polygon([coordinates])


def get_farm_info(geometry):
    """
    Get basic information about the farm area
    """
    area_hectares = geometry.area().divide(10000).getInfo()  # Convert m² to hectares
    centroid = geometry.centroid().coordinates().getInfo()
    
    print(f"Farm area: {area_hectares:.2f} hectares")
    print(f"Farm center coordinates: {centroid}")
    
    return {
        'area_hectares': area_hectares,
        'center_coordinates': centroid
    }


def determine_processing_strategy(start_date: str, end_date: str, user_intent: str = 'auto') -> Tuple[str, int, int]:
    """
    Determine optimal processing strategy based on date range and user intent
    
    Returns:
    - aggregation_period: 'daily', 'weekly', 'monthly', 'seasonal', 'yearly'
    - scale: resolution in meters
    - max_samples: maximum number of data points
    """
    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    
    # User intent override
    intent_mapping = {
        'detailed': ('daily', 30, 90),
        'summary': ('monthly', 30, 24),
        'trend': ('weekly', 30, 52)
    }
    
    if user_intent in intent_mapping:
        return intent_mapping[user_intent]
    
    # Auto-select based on time range
    if days <= 30:
        return 'daily', 30, days
    elif days <= 90:
        return 'weekly', 30, min(13, days // 7)  # ~13 weeks max
    elif days <= 365:
        return 'monthly', 30, min(12, days // 30)  # ~12 months max
    elif days <= 1095:  # 3 years
        return 'seasonal', 30, min(12, days // 90)  # 4 seasons per year
    else:
        return 'yearly', 60, min(10, days // 365)  # Max 10 years, lower resolution

def generate_time_periods(start_date: str, end_date: str, period: str) -> List[Dict]:
    """
    Generate time periods for aggregation
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    periods = []
    
    if period == 'daily':
        current = start
        while current <= end:
            periods.append({
                'start': current.strftime('%Y-%m-%d'),
                'end': current.strftime('%Y-%m-%d'),
                'label': current.strftime('%Y-%m-%d')
            })
            current += timedelta(days=1)
    
    elif period == 'weekly':
        current = start
        while current <= end:
            week_end = min(current + timedelta(days=6), end)
            periods.append({
                'start': current.strftime('%Y-%m-%d'),
                'end': week_end.strftime('%Y-%m-%d'),
                'label': f"Week of {current.strftime('%Y-%m-%d')}"
            })
            current += timedelta(days=7)
    
    elif period == 'monthly':
        current = start.replace(day=1)  # Start from first day of month
        while current <= end:
            # Get last day of current month
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1)
            else:
                next_month = current.replace(month=current.month + 1)
            month_end = min(next_month - timedelta(days=1), end)
            
            periods.append({
                'start': max(current, start).strftime('%Y-%m-%d'),
                'end': month_end.strftime('%Y-%m-%d'),
                'label': current.strftime('%Y-%m')
            })
            current = next_month
    
    elif period == 'seasonal':
        # Define seasons: Spring (Mar-May), Summer (Jun-Aug), Fall (Sep-Nov), Winter (Dec-Feb)
        seasons = [
            ('Spring', [3, 4, 5]),
            ('Summer', [6, 7, 8]),
            ('Fall', [9, 10, 11]),
            ('Winter', [12, 1, 2])
        ]
        
        current_year = start.year
        end_year = end.year
        
        for year in range(current_year, end_year + 1):
            for season_name, months in seasons:
                season_start = pd.to_datetime(f'{year}-{months[0]:02d}-01')
                if months[-1] == 2:  # Handle February end
                    season_end = pd.to_datetime(f'{year + 1 if months[0] == 12 else year}-{months[-1]:02d}-28')
                else:
                    next_month = months[-1] + 1 if months[-1] < 12 else 1
                    next_year = year if months[-1] < 12 else year + 1
                    season_end = pd.to_datetime(f'{next_year}-{next_month:02d}-01') - timedelta(days=1)
                
                # Check if season overlaps with our date range
                if season_end >= start and season_start <= end:
                    actual_start = max(season_start, start)
                    actual_end = min(season_end, end)
                    
                    periods.append({
                        'start': actual_start.strftime('%Y-%m-%d'),
                        'end': actual_end.strftime('%Y-%m-%d'),
                        'label': f'{season_name} {year}'
                    })
    
    elif period == 'yearly':
        current_year = start.year
        end_year = end.year
        
        for year in range(current_year, end_year + 1):
            year_start = pd.to_datetime(f'{year}-01-01')
            year_end = pd.to_datetime(f'{year}-12-31')
            
            actual_start = max(year_start, start)
            actual_end = min(year_end, end)
            
            periods.append({
                'start': actual_start.strftime('%Y-%m-%d'),
                'end': actual_end.strftime('%Y-%m-%d'),
                'label': str(year)
            })
    
    return periods
