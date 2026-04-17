"""Populate latitude/longitude for existing agences"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import requests
from app.core.database import SessionLocal
from app.models.agence import Agence
from app.models.region import Region

# Tunisia major cities coordinates (fallback when geocoding fails)
CITY_COORDINATES = {
    "Tunis": (36.818, 10.165),
    "Ariana": (36.861, 10.196),
    "Ben Arous": (36.753, 10.228),
    "Manouba": (36.808, 10.096),
    "Nabeul": (36.452, 10.733),
    "Zaghouan": (36.402, 10.143),
    "Bizerte": (37.274, 9.873),
    "Béja": (36.733, 9.183),
    "Jendouba": (36.501, 8.780),
    "Kef": (36.174, 8.705),
    "Siliana": (36.083, 9.371),
    "Sousse": (35.826, 10.636),
    "Monastir": (35.678, 10.825),
    "Mahdia": (35.504, 11.062),
    "Sfax": (34.739, 10.760),
    "Kairouan": (35.671, 10.100),
    "Kasserine": (35.167, 8.837),
    "Sidi Bouzid": (35.035, 9.485),
    "Gabès": (33.881, 10.097),
    "Medenine": (33.355, 10.500),
    "Tataouine": (32.928, 10.451),
    "Gafsa": (34.425, 8.784),
    "Tozeur": (33.920, 8.135),
    "Kebili": (33.704, 8.969),
}

def geocode_address(address: str, city: str = None):
    """Convert address to coordinates using Nominatim"""
    try:
        time.sleep(0.1)  # Be respectful to the API
        
        search_address = address
        if city:
            search_address = f"{address}, {city}, Tunisia"
        else:
            search_address = f"{address}, Tunisia"
            
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": search_address,
            "format": "json",
            "limit": 1,
            "countrycodes": "tn"
        }
        headers = {
            "User-Agent": "BanqueZitouna-Recouvrement/1.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"  Geocoding error: {e}")
    
    return None, None

def populate_coordinates():
    """Populate coordinates for all agences without them"""
    db = SessionLocal()
    
    try:
        # Get all agences
        agences = db.query(Agence).all()
        print(f"Found {len(agences)} agences")
        
        updated = 0
        skipped = 0
        
        for agence in agences:
            if agence.latitude and agence.longitude:
                print(f"✓ {agence.nom_agence}: already has coordinates")
                skipped += 1
                continue
            
            # Try to geocode from address
            lat, lon = None, None
            
            if agence.adresse:
                # Get region name for better geocoding
                region = db.query(Region).filter(Region.id_region == agence.id_region).first()
                region_name = region.nom_region if region else None
                
                print(f"📍 Geocoding: {agence.nom_agence} - {agence.adresse}")
                lat, lon = geocode_address(agence.adresse, region_name)
            
            # Fallback to region coordinates
            if not lat or not lon:
                region = db.query(Region).filter(Region.id_region == agence.id_region).first()
                if region and region.nom_region in CITY_COORDINATES:
                    lat, lon = CITY_COORDINATES[region.nom_region]
                    print(f"  ↳ Using fallback coordinates for {region.nom_region}")
                else:
                    # Default to Tunis
                    lat, lon = 36.818, 10.165
                    print(f"  ↳ Using default coordinates (Tunis)")
            
            if lat and lon:
                agence.latitude = lat
                agence.longitude = lon
                updated += 1
                print(f"  ✅ Updated: {lat}, {lon}")
        
        db.commit()
        print(f"\n📊 Summary:")
        print(f"  - Total agences: {len(agences)}")
        print(f"  - Updated: {updated}")
        print(f"  - Skipped (already had coordinates): {skipped}")
        print(f"  - Missing: {len(agences) - updated - skipped}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_coordinates()