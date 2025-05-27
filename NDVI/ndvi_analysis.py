import ee
from GEE_auth import initialize_gee
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
from ndvi_utils import create_farm_boundary


def collect_ndvi_data(farm_geometry, start_date, end_date, satellite='LANDSAT8'):
    """
    Collect NDVI data for a farm area over a specific time period
    
    Parameters:
    farm_geometry: ee.Geometry object (from create_farm_boundary)
    start_date: Start date as string 'YYYY-MM-DD'
    end_date: End date as string 'YYYY-MM-DD'
    satellite: 'LANDSAT8', 'LANDSAT9', or 'SENTINEL2' (Sentinel-2 has better resolution)
    
    Returns:
    Dictionary with NDVI statistics and time series data
    """
    
    # Define satellite collections and NDVI calculation
    if satellite == 'LANDSAT8':
        collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        ndvi_bands = ['SR_B5', 'SR_B4']  # NIR, Red
        cloud_mask = 'QA_PIXEL'
    elif satellite == 'LANDSAT9':
        collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        ndvi_bands = ['SR_B5', 'SR_B4']  # NIR, Red
        cloud_mask = 'QA_PIXEL'
    elif satellite == 'SENTINEL2':
        collection = ee.ImageCollection('COPERNICUS/S2_SR')
        ndvi_bands = ['B8', 'B4']  # NIR, Red
        cloud_mask = 'QA60'
    
    def calculate_ndvi(image):
        """Calculate NDVI for a single image"""
        if satellite.startswith('LANDSAT'):
            # Landsat scaling factors
            nir = image.select(ndvi_bands[0]).multiply(0.0000275).add(-0.2)
            red = image.select(ndvi_bands[1]).multiply(0.0000275).add(-0.2)
        else:
            # Sentinel-2 scaling
            nir = image.select(ndvi_bands[0]).multiply(0.0001)
            red = image.select(ndvi_bands[1]).multiply(0.0001)
        
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        return image.addBands(ndvi)
    
    def mask_clouds(image):
        """Remove cloudy pixels"""
        if satellite.startswith('LANDSAT'):
            qa = image.select(cloud_mask)
            cloud_mask_value = 1 << 3  # Cloud bit
            shadow_mask_value = 1 << 4  # Cloud shadow bit
            mask = qa.bitwiseAnd(cloud_mask_value).eq(0).And(
                   qa.bitwiseAnd(shadow_mask_value).eq(0))
        else:  # Sentinel-2
            qa = image.select(cloud_mask)
            cloud_mask_value = 1 << 10  # Cloud bit
            cirrus_mask_value = 1 << 11  # Cirrus bit
            mask = qa.bitwiseAnd(cloud_mask_value).eq(0).And(
                   qa.bitwiseAnd(cirrus_mask_value).eq(0))
        
        return image.updateMask(mask)
    
    # Filter and process the collection
    filtered_collection = (collection
                          .filterDate(start_date, end_date)
                          .filterBounds(farm_geometry)
                          .map(mask_clouds)
                          .map(calculate_ndvi))
    
    # Get NDVI statistics for each image
    def get_ndvi_stats(image):
        """Get NDVI statistics for the farm area"""
        stats = image.select('NDVI').reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.minMax(),
                sharedInputs=True
            ),
            geometry=farm_geometry,
            scale=30,  # 30m resolution for Landsat, 10m for Sentinel-2
            maxPixels=1e9
        )
        
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'ndvi_mean': stats.get('NDVI_mean'),
            'ndvi_stddev': stats.get('NDVI_stdDev'),
            'ndvi_min': stats.get('NDVI_min'),
            'ndvi_max': stats.get('NDVI_max')
        })
    
    # Calculate statistics for each image
    ndvi_time_series = filtered_collection.map(get_ndvi_stats)
    
    # Get the results
    results = ndvi_time_series.getInfo()
    
    # Process results into a clean format
    ndvi_data = []
    for feature in results['features']:
        props = feature['properties']
        if props['ndvi_mean'] is not None:  # Skip images with no valid data
            ndvi_data.append({
                'date': props['date'],
                'ndvi_mean': round(props['ndvi_mean'], 3),
                'ndvi_stddev': round(props['ndvi_stddev'], 3) if props['ndvi_stddev'] else 0,
                'ndvi_min': round(props['ndvi_min'], 3),
                'ndvi_max': round(props['ndvi_max'], 3)
            })
    
    # Sort by date
    ndvi_data.sort(key=lambda x: x['date'])
    
    return {
        'satellite': satellite,
        'date_range': f"{start_date} to {end_date}",
        'total_observations': len(ndvi_data),
        'data': ndvi_data
    }

def analyze_ndvi_trends(ndvi_results: Dict, trend_analysis: str = 'basic') -> Dict:
    """
    Analyze trends in NDVI data
    
    Parameters:
    ndvi_results: Results from collect_ndvi_data (must contain 'data' key with list of observations)
    trend_analysis: 'basic', 'detailed', or 'seasonal'
    
    Returns:
    Dictionary with trend analysis results
    """
    if not ndvi_results.get('data'):
        return {'error': 'No NDVI data provided for analysis'}
    
    data = ndvi_results['data']
    valid_data = [d for d in data if d['ndvi_mean'] is not None]
    
    if len(valid_data) < 2:
        return {'error': 'Insufficient data points for trend analysis'}
    
    # Basic trend analysis
    means = [d['ndvi_mean'] for d in valid_data]
    dates = [pd.to_datetime(d['date']) for d in valid_data]
    
    # Simple linear trend
    x = list(range(len(means)))
    trend_slope = (means[-1] - means[0]) / (len(means) - 1) if len(means) > 1 else 0
    
    trend_direction = 'increasing' if trend_slope > 0.01 else 'decreasing' if trend_slope < -0.01 else 'stable'
    
    analysis = {
        'trend_direction': trend_direction,
        'trend_slope': round(trend_slope, 4),
        'highest_ndvi': {
            'value': max(means),
            'date': valid_data[means.index(max(means))]['date']
        },
        'lowest_ndvi': {
            'value': min(means),
            'date': valid_data[means.index(min(means))]['date']
        },
        'average_ndvi': round(sum(means) / len(means), 3),
        'data_points': len(valid_data),
        'date_range': {
            'start': valid_data[0]['date'],
            'end': valid_data[-1]['date']
        }
    }
    
    return analysis

# Example usage
if __name__ == "__main__":
    # Make sure GEE is initialized first
    if initialize_gee():

        # Create farm boundary
        farm_coords = [[-99.25, 36.08], [-99.18, 36.12]]
        farm_area = create_farm_boundary(farm_coords)
        
        # Get NDVI data for the last 6 months
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        # ndvi_results = collect_ndvi_data(
        #     farm_area,
        #     start_date.strftime('%Y-%m-%d'),
        #     end_date.strftime('%Y-%m-%d'),
        #     satellite='LANDSAT8'
        # )

        # Short range (daily data)
        daily_data = collect_ndvi_data(farm_area, '2023-06-01', '2023-08-31')

        # Medium range (weekly composites)
        weekly_data = collect_ndvi_data(farm_area, '2022-01-01', '2022-12-31')

        # Long range (monthly composites)
        monthly_data = collect_ndvi_data(farm_area, '2020-01-01', '2023-12-31')

        print("Daily NDVI Data:", daily_data)
        print("Weekly NDVI Data:", weekly_data)
        print("Monthly NDVI Data:", monthly_data)
        # Analyze trends
        trend_analysis = analyze_ndvi_trends(monthly_data, trend_analysis='basic')
        print("Trend Analysis:", trend_analysis)
        
        