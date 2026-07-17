"""
KARMANI AI CAR VALUATORS — Hybrid Pricing Engine v2.0

Professional pricing architecture that combines:
  1. Live Pricing APIs (when configured)
  2. Internal Historical Database
  3. AI-based Used Car Valuation Engine

CRITICAL: Every price returned includes a `price_type` and `price_label`
to ensure no price is ever presented without clear attribution.

Price Types:
  - official_current    -> "Official Current Ex-Showroom Price"
  - estimated_onroad    -> "Estimated On-Road Price"
  - historical_launch   -> "Original Launch Price (Historical)"
  - ai_estimated_used   -> "AI Estimated Used Market Value"
  - average_resale      -> "Average Resale Value"
  - unavailable         -> "Official Live Price Currently Unavailable"
"""

import os
import time
import sqlite3
from datetime import datetime

# Load environment variable files manually if dotenv is not present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'users.db')


class PriceLabel:
    """Enumeration of all valid price label types."""
    OFFICIAL_CURRENT = "official_current"
    ESTIMATED_ONROAD = "estimated_onroad"
    HISTORICAL_LAUNCH = "historical_launch"
    AI_ESTIMATED_USED = "ai_estimated_used"
    AVERAGE_RESALE = "average_resale"
    UNAVAILABLE = "unavailable"
    
    DISPLAY = {
        "official_current": "Official Current Ex-Showroom Price",
        "estimated_onroad": "Estimated On-Road Price",
        "historical_launch": "Original Launch Price (Historical)",
        "ai_estimated_used": "AI Estimated Used Market Value",
        "average_resale": "Average Resale Value",
        "unavailable": "Official Live Price Currently Unavailable",
    }
    
    COLORS = {
        "official_current": "#22C55E",     # Green
        "estimated_onroad": "#EAB308",     # Yellow
        "historical_launch": "#3B82F6",    # Blue
        "ai_estimated_used": "#A855F7",    # Purple
        "average_resale": "#EF4444",       # Red
        "unavailable": "#6B7280",          # Grey
    }
    
    ICONS = {
        "official_current": "fa-circle-check",
        "estimated_onroad": "fa-calculator",
        "historical_launch": "fa-clock-rotate-left",
        "ai_estimated_used": "fa-robot",
        "average_resale": "fa-chart-line",
        "unavailable": "fa-circle-question",
    }


class HybridPricingEngine:
    """Production-grade hybrid pricing engine for Indian automobile market."""
    
    def __init__(self):
        self.marketcheck_key = os.getenv("MARKETCHECK_API_KEY", "")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.edmunds_key = os.getenv("EDMUNDS_API_KEY", "")
        self.cache_duration = int(os.getenv("CACHE_DURATION", 86400))
        self.base_url = os.getenv("BASE_URL", "https://api.marketcheck.com/v2")

    def get_vehicle_pricing(self, brand, model, variant, year=2026,
                            fuel_type="Petrol", transmission="Manual",
                            state="MH", is_discontinued=False):
        """
        Master pricing method. Returns a complete pricing breakdown
        with clear labels for every value.
        
        Returns dict with:
          - prices: list of {value, type, label, color, icon}
          - primary_price: the main display price
          - source: where the data came from
          - last_updated: timestamp
          - state: Indian state code
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self._ensure_cache_table(cursor)
        conn.commit()
        
        result = {
            "prices": [],
            "primary_price": None,
            "source": None,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "state": state,
            "brand": brand,
            "model": model,
            "variant": variant,
            "year": year,
        }
        
        # ── STEP 1: Check if we have a cached live price ──
        cached = self._check_cache(cursor, brand, model, variant, year, state)
        if cached:
            result["prices"].append(self._make_price_entry(
                cached["ex_showroom"], PriceLabel.OFFICIAL_CURRENT
            ))
            result["prices"].append(self._make_price_entry(
                cached["on_road"], PriceLabel.ESTIMATED_ONROAD
            ))
            result["primary_price"] = cached["ex_showroom"]
            result["source"] = cached["source"]
            result["last_updated"] = cached["last_updated"]
            conn.close()
            return result
        
        # ── STEP 2: Try live API (if keys configured) ──
        api_result = self._try_live_api(brand, model, variant, year, state)
        if api_result:
            # Cache the result
            self._write_cache(cursor, brand, model, variant, year, state,
                            api_result, "Live API")
            conn.commit()
            result["prices"].append(self._make_price_entry(
                api_result["ex_showroom"], PriceLabel.OFFICIAL_CURRENT
            ))
            result["prices"].append(self._make_price_entry(
                api_result["on_road"], PriceLabel.ESTIMATED_ONROAD
            ))
            result["primary_price"] = api_result["ex_showroom"]
            result["source"] = "Live Pricing API"
            conn.close()
            return result
        
        # ── STEP 3: Fall back to internal database ──
        db_price = self._get_database_price(cursor, brand, model, variant, year)
        
        if is_discontinued or year < 2024:
            # Historical / discontinued vehicle
            if db_price:
                result["prices"].append(self._make_price_entry(
                    db_price, PriceLabel.HISTORICAL_LAUNCH
                ))
                # Compute AI estimated used value
                used_value = self._compute_used_value(db_price, year, brand)
                result["prices"].append(self._make_price_entry(
                    used_value, PriceLabel.AI_ESTIMATED_USED
                ))
                # Compute average resale
                resale = self._compute_resale_value(db_price, year, brand)
                result["prices"].append(self._make_price_entry(
                    resale, PriceLabel.AVERAGE_RESALE
                ))
                result["primary_price"] = used_value
                result["source"] = "Internal Historical Database + AI Engine"
            else:
                result["prices"].append(self._make_price_entry(
                    0, PriceLabel.UNAVAILABLE
                ))
                result["source"] = "No data available"
        else:
            # Current / active model — no live API available
            if db_price:
                # We have a database estimate but no live confirmation
                result["prices"].append(self._make_price_entry(
                    db_price, PriceLabel.HISTORICAL_LAUNCH
                ))
                
                # Compute on-road estimate
                on_road = self._compute_on_road(db_price, state, fuel_type)
                result["prices"].append(self._make_price_entry(
                    on_road["on_road"], PriceLabel.ESTIMATED_ONROAD
                ))
                
                # Add unavailable notice for official price
                result["prices"].append(self._make_price_entry(
                    0, PriceLabel.UNAVAILABLE
                ))
                
                result["primary_price"] = db_price
                result["source"] = "Internal Database (Live API Not Configured)"
            else:
                result["prices"].append(self._make_price_entry(
                    0, PriceLabel.UNAVAILABLE
                ))
                result["source"] = "No data available"
        
        conn.close()
        return result
    
    def _make_price_entry(self, value, price_type):
        """Create a standardized price entry with label, color, icon."""
        return {
            "value": value,
            "type": price_type,
            "label": PriceLabel.DISPLAY.get(price_type, "Price"),
            "color": PriceLabel.COLORS.get(price_type, "#6B7280"),
            "icon": PriceLabel.ICONS.get(price_type, "fa-circle-info"),
        }
    
    def _ensure_cache_table(self, cursor):
        """Ensure pricing_cache table exists."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pricing_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT,
                model TEXT,
                variant TEXT,
                year INTEGER,
                state TEXT,
                ex_showroom REAL,
                on_road REAL,
                insurance REAL,
                rto REAL,
                accessories REAL,
                source TEXT,
                timestamp INTEGER
            )
        ''')
    
    def _check_cache(self, cursor, brand, model, variant, year, state):
        """Check for valid cached pricing."""
        cursor.execute('''
            SELECT ex_showroom, on_road, insurance, rto, accessories, source, timestamp 
            FROM pricing_cache 
            WHERE brand = ? AND model = ? AND variant = ? AND year = ? AND state = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (brand, model, variant, year, state))
        row = cursor.fetchone()
        
        if row:
            now = int(time.time())
            if now - row[6] < self.cache_duration:
                return {
                    "ex_showroom": row[0],
                    "on_road": row[1],
                    "insurance": row[2],
                    "rto": row[3],
                    "accessories": row[4],
                    "source": f"{row[5]} (Cached)",
                    "last_updated": datetime.fromtimestamp(row[6]).strftime("%Y-%m-%d %H:%M:%S"),
                }
        return None
    
    def _write_cache(self, cursor, brand, model, variant, year, state, data, source):
        """Write pricing data to cache."""
        now = int(time.time())
        cursor.execute('''
            INSERT INTO pricing_cache (
                brand, model, variant, year, state,
                ex_showroom, on_road, insurance, rto, accessories,
                source, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            brand, model, variant, year, state,
            data.get("ex_showroom", 0),
            data.get("on_road", 0),
            data.get("insurance", 0),
            data.get("rto", 0),
            data.get("accessories", 0),
            source, now
        ))
    
    def _try_live_api(self, brand, model, variant, year, state):
        """Attempt live API call. Returns None if no API keys configured."""
        if not (self.marketcheck_key or self.rapidapi_key):
            return None
        
        # In production: make actual HTTP requests here
        # For now: return None (no keys configured)
        return None
    
    def _get_database_price(self, cursor, brand, model, variant, year):
        """Look up price from internal database."""
        # Try exact match first
        cursor.execute('''
            SELECT base_showroom_price FROM car_database 
            WHERE brand = ? AND model = ? AND variant = ?
            AND manufacturing_year = ?
            LIMIT 1
        ''', (brand, model, variant, year))
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Try without year (latest available)
        cursor.execute('''
            SELECT base_showroom_price FROM car_database 
            WHERE brand = ? AND model = ? AND variant = ?
            ORDER BY manufacturing_year DESC
            LIMIT 1
        ''', (brand, model, variant))
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Try model-level fallback
        cursor.execute('''
            SELECT MIN(base_showroom_price) FROM car_database 
            WHERE brand = ? AND model = ?
        ''', (brand, model))
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        
        return None
    
    def _compute_used_value(self, original_price, year, brand):
        """AI-based used car value estimation."""
        current_year = 2026
        age = current_year - year
        if age <= 0:
            return original_price
        
        # Brand-specific retention factors (year-over-year)
        retention = {
            "Toyota": 0.92, "Maruti Suzuki": 0.90, "Honda": 0.88,
            "Hyundai": 0.87, "Mahindra": 0.88, "Tata Motors": 0.85,
            "Kia": 0.86, "Volkswagen": 0.82, "Skoda": 0.81,
            "BMW": 0.78, "Mercedes-Benz": 0.80, "Audi": 0.76,
            "Volvo": 0.79, "Jaguar": 0.72, "Land Rover": 0.74,
            "Porsche": 0.85, "Mini": 0.75,
            "Chevrolet": 0.60, "Ford": 0.72, "Fiat": 0.58,
            "Renault": 0.75, "Nissan": 0.76, "MG Motor": 0.80,
        }
        
        factor = retention.get(brand, 0.82)
        value = original_price
        
        for yr_age in range(1, age + 1):
            if yr_age == 1:
                value *= (factor * 0.92)  # Steeper first-year drop
            else:
                value *= factor
        
        # Floor at 8% of original
        value = max(value, original_price * 0.08)
        return round(value)
    
    def _compute_resale_value(self, original_price, year, brand):
        """Compute average resale value (typically 5-10% below market value)."""
        used = self._compute_used_value(original_price, year, brand)
        return round(used * 0.92)  # 8% dealer margin
    
    def _compute_on_road(self, ex_showroom, state, fuel_type):
        """Compute estimated on-road price based on state and fuel type."""
        rto_ratios = {
            "MH": 0.12, "DL": 0.085, "KA": 0.15, "TN": 0.10,
            "UP": 0.08, "GA": 0.09, "KL": 0.11, "HR": 0.07,
            "GJ": 0.06, "RJ": 0.085, "WB": 0.10, "AP": 0.14,
            "TS": 0.13, "MP": 0.10, "PB": 0.09, "CH": 0.04,
        }
        rto_rate = rto_ratios.get(state, 0.10)
        
        if fuel_type == "Diesel":
            rto_rate += 0.015
        elif fuel_type in ("EV", "Electric"):
            rto_rate = 0.02
        
        rto = round(ex_showroom * rto_rate)
        
        ins_rate = 0.028
        if ex_showroom > 2500000:
            ins_rate = 0.038
        elif ex_showroom < 800000:
            ins_rate = 0.025
        
        insurance = round(ex_showroom * ins_rate) + 12000
        accessories = round(ex_showroom * 0.012)
        on_road = ex_showroom + rto + insurance + accessories
        
        return {
            "ex_showroom": ex_showroom,
            "on_road": on_road,
            "insurance": insurance,
            "rto": rto,
            "accessories": accessories,
        }
    
    def get_depreciation_timeline(self, original_price, launch_year, 
                                  discontinued_year, brand):
        """Compute annual depreciation curve for a vehicle."""
        current_year = 2026
        retention = {
            "Toyota": 0.93, "Maruti Suzuki": 0.91, "Honda": 0.88,
            "Hyundai": 0.87, "Mahindra": 0.88, "Tata Motors": 0.85,
            "BMW": 0.78, "Mercedes-Benz": 0.80, "Audi": 0.76,
            "Jaguar": 0.72, "Chevrolet": 0.60, "Ford": 0.75,
            "Fiat": 0.58,
        }
        
        factor = retention.get(brand, 0.83)
        used_value = original_price
        history = []
        
        for yr in range(launch_year, current_year + 1):
            age = yr - launch_year
            if age == 0:
                val = original_price
            else:
                current_factor = factor * 0.95 if age == 1 else factor
                val = round(used_value * current_factor)
            
            if yr == discontinued_year:
                val = round(val * 0.90)
            
            used_value = max(val, original_price * 0.08)
            history.append({"year": yr, "value": used_value})
        
        depreciation_pct = round(
            ((original_price - used_value) / original_price) * 100, 1
        )
        
        return {
            "current_value": used_value,
            "depreciation_percentage": depreciation_pct,
            "history": history,
        }
    
    def get_price_comparison_by_state(self, ex_showroom, fuel_type="Petrol"):
        """Get on-road price comparison across major Indian states."""
        states = {
            "MH": "Maharashtra", "DL": "Delhi", "KA": "Karnataka",
            "TN": "Tamil Nadu", "UP": "Uttar Pradesh", "GJ": "Gujarat",
            "HR": "Haryana", "KL": "Kerala", "TS": "Telangana",
            "WB": "West Bengal", "RJ": "Rajasthan", "PB": "Punjab",
        }
        
        comparison = []
        for code, name in states.items():
            data = self._compute_on_road(ex_showroom, code, fuel_type)
            comparison.append({
                "state_code": code,
                "state_name": name,
                "on_road": data["on_road"],
                "rto": data["rto"],
                "insurance": data["insurance"],
            })
        
        comparison.sort(key=lambda x: x["on_road"])
        return comparison
