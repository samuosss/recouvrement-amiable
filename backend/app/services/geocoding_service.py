import requests
import time
from typing import Optional, Tuple

def get_coordinates_from_address(address: str, city: str = "Tunisia") -> Tuple[Optional[float], Optional[float]]:
    """
    Convert an address to latitude/longitude using Nominatim (OpenStreetMap)
    
    Args:
        address: Street address
        city: City or country (default: Tunisia)
    
    Returns:
        Tuple of (latitude, longitude) or (None, None) if geocoding fails
    """
    try:
        # Be respectful to the free API - add delay
        time.sleep(0.1)
        
        full_address = f"{address}, {city}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": full_address,
            "format": "json",
            "limit": 1,
            "countrycodes": "tn"  # Tunisia
        }
        
        headers = {
            "User-Agent": "BanqueZitouna-Recouvrement/1.0"  # Identify your app
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) > 0:
            return float(data[0]["lat"]), float(data[0]["lon"])
            
    except Exception as e:
        print(f"Geocoding error for '{address}': {e}")
    
    return None, None


def update_agence_coordinates(db_session, agence_id: int) -> bool:
    """
    Update an agence's coordinates based on its address
    
    Args:
        db_session: SQLAlchemy database session
        agence_id: ID of the agence to update
    
    Returns:
        True if coordinates were updated, False otherwise
    """
    from app.models.agence import Agence
    
    agence = db_session.query(Agence).filter(Agence.id_agence == agence_id).first()
    if not agence or not agence.adresse:
        return False
    
    lat, lon = get_coordinates_from_address(agence.adresse)
    if lat and lon:
        agence.latitude = lat
        agence.longitude = lon
        db_session.commit()
        return True
    
    return False