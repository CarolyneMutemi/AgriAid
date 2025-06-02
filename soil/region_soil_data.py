from functools import lru_cache
import requests
import json
# import time
from typing import Dict, List, Optional, Tuple
from regions.get_region import get_ward_data

class SoilGridsAPI:
    """
    Python client for SoilGrids API by ISRIC
    Provides soil data including classification and properties for any location globally
    """
    
    def __init__(self):
        self.base_url = "https://rest.isric.org/soilgrids/v2.0"
        self.session = requests.Session()
        # self.last_request_time = 0
        
    # def _rate_limit(self):
    #     """Ensure we don't exceed 5 requests per minute"""
    #     current_time = time.time()
    #     time_since_last = current_time - self.last_request_time
    #     if time_since_last < 12:  # 60/5 = 12 seconds between requests
    #         time.sleep(12 - time_since_last)
    #     self.last_request_time = time.time()
    
    def get_soil_properties(self, lat: float, lon: float, 
                          properties: Optional[List[str]] = None,
                          depths: Optional[List[str]] = None,
                          values: Optional[List[str]] = None) -> Dict:
        """
        Get soil properties for a specific location
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees  
            properties: List of soil properties to retrieve. Available options:
                       ['bdod', 'cec', 'cfvo', 'clay', 'nitrogen', 'ocd', 'ocs', 
                        'phh2o', 'sand', 'silt', 'soc', 'wv0010', 'wv0033', 'wv1500']
            depths: List of depth intervals. Available options:
                   ['0-5cm', '5-15cm', '15-30cm', '30-60cm', '60-100cm', '100-200cm']
            values: Statistics to return. Options: ['Q0.05', 'Q0.5', 'Q0.95', 'mean', 'uncertainty']
        
        Returns:
            Dictionary containing soil property data
        """
        
        # Default parameters if not specified
        if properties is None:
            properties = ['clay', 'sand', 'silt', 'phh2o', 'soc', 'bdod']
        if depths is None:
            depths = ['0-5cm', '5-15cm', '15-30cm', '30-60cm']
        if values is None:
            values = ['mean', 'uncertainty']
            
        # self._rate_limit()
        
        # Build URL parameters
        params = {
            'lat': lat,
            'lon': lon,
            'property': properties,
            'depth': depths,
            'value': values
        }
        
        try:
            response = self.session.get(f"{self.base_url}/properties/query", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching soil properties: {e}")
            return {}
    
    def get_soil_classification(self, lat: float, lon: float, 
                              depths: Optional[List[str]] = None) -> Dict:
        """
        Get WRB soil classification for a specific location
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            depths: Depth intervals (default: ['0-200cm'])
            
        Returns:
            Dictionary containing WRB classification data
        """
        
        if depths is None:
            depths = ['0-200cm']
            
        # self._rate_limit()
        
        params = {
            'lat': lat,
            'lon': lon,
            'depth': depths
        }
        
        try:
            response = self.session.get(f"{self.base_url}/classification/query", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching soil classification: {e}")
            return {}
    
    def get_comprehensive_soil_data(self, lat: float, lon: float) -> Dict:
        """
        Get both soil properties and classification for a location
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            Dictionary with both properties and classification data
        """
        
        properties_data = self.get_soil_properties(lat, lon)
        classification_data = self.get_soil_classification(lat, lon)
        
        return {
            'location': {'lat': lat, 'lon': lon},
            'properties': properties_data,
            'classification': classification_data
        }
    
    def interpret_soil_texture(self, clay_pct: float, sand_pct: float, silt_pct: float) -> str:
        """
        Classify soil texture based on clay, sand, silt percentages
        Uses USDA soil texture triangle classification
        
        Args:
            clay_pct: Clay percentage
            sand_pct: Sand percentage  
            silt_pct: Silt percentage
            
        Returns:
            Soil texture class name
        """
        
        if clay_pct >= 40:
            return "Clay"
        elif clay_pct >= 27:
            if sand_pct >= 45:
                return "Sandy Clay"
            elif sand_pct >= 20:
                return "Clay Loam"
            else:
                return "Silty Clay"
        elif clay_pct >= 20:
            if sand_pct >= 45:
                return "Sandy Clay Loam"
            elif silt_pct >= 28:
                return "Silty Clay Loam"
            else:
                return "Clay Loam"
        elif sand_pct >= 85:
            return "Sand"
        elif sand_pct >= 70:
            if clay_pct >= 15:
                return "Sandy Clay Loam"
            else:
                return "Loamy Sand"
        elif silt_pct >= 80:
            return "Silt"
        elif silt_pct >= 50:
            return "Silt Loam"
        elif clay_pct >= 7:
            return "Loam"
        else:
            return "Sandy Loam"

@lru_cache(maxsize=1)
def get_soil_data_for_ai_agent(county:str, subcounty:str, ward:str, detailed: bool = True) -> Dict:
    """
    AI Agent Tool: Get comprehensive soil data for a location
    
    This function is designed to be used as a tool by AI agents - API calls may delay a while.
    It tells the soil type, texture, surface properties, and agricultural interpretation necessary for decision making and planting advice.
    Returns structured soil data including classification, properties, and interpretation.
    
    Args:
        county: County name (e.g. "Nairobi")
        subcounty: Subcounty name (e.g. "Westlands")
        ward: Ward name (e.g. "Parklands")
        detailed: If True, includes all depth layers. If False, focuses on surface layer (0-30cm)
        
    Returns:
        Dictionary with structured soil data:
        {
            'success': bool,
            'location': {'lat': float, 'lon': float},
            'soil_type': str,  # WRB classification
            'soil_texture': str,  # USDA texture class
            'surface_properties': {
                'ph': float,
                'clay_percent': float,
                'sand_percent': float, 
                'silt_percent': float,
                'organic_carbon': float,
                'bulk_density': float
            },
            'depth_profile': {  # Only if detailed=True
                '0-5cm': {...},
                '5-15cm': {...},
                # etc.
            },
            'interpretation': {
                'fertility_indicators': {...},
                'agricultural_suitability': str,
                'drainage_characteristics': str
            },
            'error': str  # Only present if success=False
        }
    """

    ward = get_ward_data(county, subcounty, ward)
    if not ward:
        print
        return {
            'success': False,
            'location': {'lat': None, 'lon': None},
            'error': f"Ward '{ward}' not found in {county}, {subcounty}"
        }
    
    lat = ward['centroid'][0]
    lon = ward['centroid'][1]
    
    try:
        # Initialize API client
        api = SoilGridsAPI()
        
        # Get comprehensive data
        result = {
            'success': True,
            'location': {'lat': lat, 'lon': lon},
            'soil_type': 'Unknown',
            'soil_texture': 'Unknown',
            'surface_properties': {},
            'interpretation': {}
        }
        
        # Get soil classification
        classification_data = api.get_soil_classification(lat, lon)
        print(f"Classification data: {classification_data}")
        if classification_data and 'wrb_class_name' in classification_data:
            result['soil_type'] = classification_data['wrb_class_name']
        
        # Get soil properties
        if detailed:
            depths = ['0-5cm', '5-15cm', '15-30cm', '30-60cm', '60-100cm', '100-200cm']
            result['depth_profile'] = {}
        else:
            depths = ['0-5cm', '5-15cm', '15-30cm']
        
        properties = ['clay', 'sand', 'silt', 'phh2o', 'soc', 'bdod', 'cec', 'nitrogen']
        properties_data = api.get_soil_properties(lat, lon, properties, depths)
        
        if properties_data and 'properties' in properties_data:
            # Handle the actual API response structure
            layers_data = properties_data['properties'].get('layers', [])
            
            # Convert layers list to a more usable dictionary format
            props = {}
            for layer in layers_data:
                prop_name = layer['name']
                props[prop_name] = {}
                
                for depth_info in layer['depths']:
                    depth_label = depth_info['label']
                    values = depth_info['values']
                    
                    # Apply unit conversion if needed
                    mean_val = values.get('mean')
                    if mean_val is not None and 'd_factor' in layer.get('unit_measure', {}):
                        d_factor = layer['unit_measure']['d_factor']
                        mean_val = mean_val / d_factor
                    
                    props[prop_name][depth_label] = {
                        'mean': mean_val,
                        'uncertainty': values.get('uncertainty')
                    }
            
            # Extract surface properties (0-5cm or average of top layers)
            surface_props = {}
            
            for prop in ['clay', 'sand', 'silt', 'phh2o', 'soc', 'bdod']:
                if prop in props:
                    # Try to get 0-5cm first, then 5-15cm as fallback
                    for depth in ['0-5cm', '5-15cm']:
                        if depth in props[prop] and props[prop][depth]['mean'] is not None:
                            surface_props[prop] = props[prop][depth]['mean']
                            break
            
            # Map to user-friendly names
            result['surface_properties'] = {
                'ph': surface_props.get('phh2o'),
                'clay_percent': surface_props.get('clay'),
                'sand_percent': surface_props.get('sand'),
                'silt_percent': surface_props.get('silt'),
                'organic_carbon_percent': surface_props.get('soc'),
                'bulk_density_g_cm3': surface_props.get('bdod')
            }
            
            # Calculate soil texture
            if all(k in surface_props for k in ['clay', 'sand', 'silt']):
                result['soil_texture'] = api.interpret_soil_texture(
                    surface_props['clay'], 
                    surface_props['sand'], 
                    surface_props['silt']
                )
            
            # Add detailed depth profile if requested
            if detailed:
                for depth in depths:
                    depth_data = {}
                    for prop in properties:
                        if prop in props and depth in props[prop] and props[prop][depth]['mean'] is not None:
                            depth_data[prop] = props[prop][depth]['mean']
                    if depth_data:
                        result['depth_profile'][depth] = depth_data
        
        # Add agricultural interpretation
        result['interpretation'] = _interpret_soil_for_agriculture(result['surface_properties'])
        
        print(f"Final result: {result}")
        return result
        
    except Exception as e:
        return {
            'success': False,
            'location': {'lat': lat, 'lon': lon},
            'error': str(e)
        }


def _interpret_soil_for_agriculture(surface_props: Dict) -> Dict:
    """
    Interpret soil properties for agricultural suitability
    
    Args:
        surface_props: Dictionary of surface soil properties
        
    Returns:
        Dictionary with agricultural interpretation
    """
    
    interpretation = {
        'fertility_indicators': {},
        'agricultural_suitability': 'Unknown',
        'drainage_characteristics': 'Unknown',
        'recommendations': []
    }
    
    try:
        ph = surface_props.get('ph')
        clay = surface_props.get('clay_percent')
        sand = surface_props.get('sand_percent')
        silt = surface_props.get('silt_percent')
        organic_carbon = surface_props.get('organic_carbon_percent')
        
        # pH interpretation
        if ph is not None:
            if ph < 5.5:
                interpretation['fertility_indicators']['ph_status'] = 'Acidic - may need liming'
            elif ph > 8.0:
                interpretation['fertility_indicators']['ph_status'] = 'Alkaline - may affect nutrient availability'
            else:
                interpretation['fertility_indicators']['ph_status'] = 'Suitable pH range'
        
        # Organic matter interpretation
        if organic_carbon is not None:
            if organic_carbon < 1.0:
                interpretation['fertility_indicators']['organic_matter'] = 'Low - needs organic inputs'
            elif organic_carbon > 3.0:
                interpretation['fertility_indicators']['organic_matter'] = 'High - good fertility potential'
            else:
                interpretation['fertility_indicators']['organic_matter'] = 'Moderate'
        
        # Drainage characteristics based on texture
        if clay is not None and sand is not None:
            if clay > 40:
                interpretation['drainage_characteristics'] = 'Poor drainage - clay-rich soil'
                interpretation['recommendations'].append('Consider drainage improvements')
            elif sand > 70:
                interpretation['drainage_characteristics'] = 'Excellent drainage - may need frequent irrigation'
                interpretation['recommendations'].append('Monitor water needs closely')
            else:
                interpretation['drainage_characteristics'] = 'Moderate drainage - good for most crops'
        
        # Overall agricultural suitability
        suitability_score = 0
        factors = 0
        
        if ph is not None:
            factors += 1
            if 6.0 <= ph <= 7.5:
                suitability_score += 2
            elif 5.5 <= ph <= 8.0:
                suitability_score += 1
        
        if organic_carbon is not None:
            factors += 1
            if organic_carbon > 2.0:
                suitability_score += 2
            elif organic_carbon > 1.0:
                suitability_score += 1
        
        if clay is not None:
            factors += 1
            if 20 <= clay <= 40:
                suitability_score += 2
            elif 10 <= clay <= 50:
                suitability_score += 1
        
        if factors > 0:
            avg_score = suitability_score / factors
            if avg_score >= 1.5:
                interpretation['agricultural_suitability'] = 'Good - suitable for most crops'
            elif avg_score >= 1.0:
                interpretation['agricultural_suitability'] = 'Moderate - suitable with proper management'
            else:
                interpretation['agricultural_suitability'] = 'Limited - may need significant amendments'
        
    except Exception as e:
        interpretation['error'] = f"Error in interpretation: {str(e)}"
    
    return interpretation


# Example usage and demonstration
def main():
    """Example usage demonstrating both the class and the AI agent function"""
    
    # Example coordinates (Nairobi, Kenya)
    lat, lon = -1.2921, 36.8219
    
    print(f"Getting soil data for coordinates: {lat}, {lon}")
    print("=" * 60)
    
    # Use the AI agent function
    soil_info = get_soil_data_for_ai_agent("Isiolo", "Isiolo", "Wabera", detailed=True)
    
    print("Soil Data for AI Agent:", soil_info)
    if soil_info['success']:
        print(f"🗺️  SOIL TYPE: {soil_info['soil_type']}")
        print(f"🏺 SOIL TEXTURE: {soil_info['soil_texture']}")
        
        print("\n🌱 SURFACE PROPERTIES:")
        for prop, value in soil_info['surface_properties'].items():
            if value is not None:
                print(f"  {prop}: {value}")
        
        print(f"\n🚜 AGRICULTURAL SUITABILITY: {soil_info['interpretation']['agricultural_suitability']}")
        print(f"💧 DRAINAGE: {soil_info['interpretation']['drainage_characteristics']}")
        
        if soil_info['interpretation']['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in soil_info['interpretation']['recommendations']:
                print(f"  - {rec}")
                
    else:
        print(f"❌ Error: {soil_info['error']}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()