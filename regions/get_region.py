import os
import json
from typing import List, Dict, Any, Optional, Union
import math
from langchain_core.tools import tool
from dotenv import load_dotenv
load_dotenv()

KENYA_WARDS_FILE = os.getenv("KENYA_WARDS_FILE", "assets/kenya_wards.json")


def get_counties(paginate: bool = False, page: int = 1, page_size: int = 10) -> Union[List[str], Dict[str, Any]]:
    """
    Extract county names from the JSON data.
    Should also be used to find if a specific county exists.
    
    Args:
        data: The JSON data dictionary
        paginate: Whether to return paginated results (default: False)
        page: Page number for pagination (default: 1)
        page_size: Number of items per page (default: 10)
    
    Returns:
        List of county names or paginated result dictionary
    """
    data = load_json_file(KENYA_WARDS_FILE)
    counties = list(data.keys())
    
    if not paginate:
        return counties
    
    # Pagination logic
    total_items = len(counties)
    total_pages = math.ceil(total_items / page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    return {
        "data": counties[start_idx:end_idx],
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }


def get_subcounties(county: Optional[str] = None, paginate: bool = False, page: int = 1, page_size: int = 10) -> Union[List[str], Dict[str, Any]]:
    """
    Extract subcounty names from the JSON data.
    To be used to find if a specific subcounty exists within a county so it's necessary to pass the county name.
    
    Args:
        data: The JSON data dictionary
        county: Specific county to get subcounties from (optional)
        paginate: Whether to return paginated results (default: False)
        page: Page number for pagination (default: 1)
        page_size: Number of items per page (default: 10)
    
    Returns:
        List of subcounty names or paginated result dictionary
    """
    subcounties = []
    data = load_json_file(KENYA_WARDS_FILE)
    
    if county:
        if county in data:
            subcounties = list(data[county].keys())
        else:
            raise ValueError(f"County '{county}' not found in data")
    else:
        # Get all subcounties from all counties
        for county_data in data.values():
            subcounties.extend(list(county_data.keys()))
    
    if not paginate:
        return subcounties
    
    # Pagination logic
    total_items = len(subcounties)
    total_pages = math.ceil(total_items / page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    return {
        "data": subcounties[start_idx:end_idx],
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }


def get_wards(county: Optional[str] = None, subcounty: Optional[str] = None, paginate: bool = False, page: int = 1, page_size: int = 10) -> Union[List[str], Dict[str, Any]]:
    """
    Used to get wards in a county in a subcounty so it's necessary to pass the county and subcounty names.
    
    Args:
        data: The JSON data dictionary
        county: Specific county to get wards from (optional)
        subcounty: Specific subcounty to get wards from (optional, requires county)
        paginate: Whether to return paginated results (default: False)
        page: Page number for pagination (default: 1)
        page_size: Number of items per page (default: 10)
    
    Returns:
        List of ward names or paginated result dictionary
    """
    wards = []
    data = load_json_file(KENYA_WARDS_FILE)
    
    if county and subcounty:
        if county in data and subcounty in data[county]:
            wards = list(data[county][subcounty].keys())
        else:
            raise ValueError(f"County '{county}' or subcounty '{subcounty}' not found in data")
    elif county:
        if county in data:
            for subcounty_data in data[county].values():
                wards.extend(list(subcounty_data.keys()))
        else:
            raise ValueError(f"County '{county}' not found in data")
    else:
        # Get all wards from all counties and subcounties
        for county_data in data.values():
            for subcounty_data in county_data.values():
                wards.extend(list(subcounty_data.keys()))
    
    if not paginate:
        return wards
    
    # Pagination logic
    total_items = len(wards)
    total_pages = math.ceil(total_items / page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    return {
        "data": wards[start_idx:end_idx],
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }


def get_ward_data(county: str, subcounty: str, ward: str) -> Dict[str, Any]:
    """
    Get specific ward data including area_m2, buffer_radius_m, and centroid.
    
    Args:
        data: The JSON data dictionary
        county: County name
        subcounty: Subcounty name
        ward: Ward name
    
    Returns:
        Dictionary containing ward data (area_m2, buffer_radius_m, centroid)
    
    Raises:
        ValueError: If county, subcounty, or ward is not found
    """
    try:
        data = load_json_file()
        return data[county][subcounty][ward]
    except KeyError as e:
        raise ValueError(f"Path not found: {county} -> {subcounty} -> {ward}. Missing key: {e}")


# Example usage functions
def load_json_file(file_path: Optional[str] = KENYA_WARDS_FILE) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to the JSON file
    
    Returns:
        Loaded JSON data as dictionary
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


# Example usage:
if __name__ == "__main__":
    # Sample data for testing
    sample_data = {
        "Isiolo": {
            "Isiolo Sub County": {
                "Wabera": {
                    "area_m2": 12978582.52835129,
                    "buffer_radius_m": 2032.5380998708076,
                    "centroid": [37.59258512424839, 0.3588667172516978]
                },
                "Bulla Pesa": {
                    "area_m2": 8234567.89,
                    "buffer_radius_m": 1654.32,
                    "centroid": [37.45, 0.25]
                }
            }
        },
        "Meru": {
            "Meru Central": {
                "Kiirua": {
                    "area_m2": 15678901.23,
                    "buffer_radius_m": 2234.56,
                    "centroid": [37.65, 0.12]
                }
            }
        }
    }
    
    # Test the functions
    print("Counties:", get_counties(sample_data))
    print("Subcounties:", get_subcounties(sample_data))
    print("Wards:", get_wards(sample_data))
    print("Wards in Isiolo:", get_wards(sample_data, county="Isiolo"))
    print("Ward data:", get_ward_data(sample_data, "Isiolo", "Isiolo Sub County", "Wabera"))
    
    # Test pagination
    print("Paginated counties:", get_counties(sample_data, paginate=True, page=1, page_size=1))