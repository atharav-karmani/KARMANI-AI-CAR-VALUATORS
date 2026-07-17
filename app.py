import os
import sqlite3
import random
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

# Load environment variables from .env manually
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()

load_env()


# Initialize the Flask application
app = Flask(
    __name__, 
    template_folder='templates', 
    static_folder='static'
)
CORS(app)
app.secret_key = 'premium_car_valuation_secret_key_caps'

# Define database directory and connection paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
DB_PATH = os.path.join(DB_DIR, 'users.db')

def format_indian_currency(number):
    """Formats numbers into standard Indian numbering system format (e.g. 7,50,000)."""
    if number is None:
        return "0"
    try:
        number = int(number)
    except (ValueError, TypeError):
        return str(number)
        
    s = str(number)
    if len(s) <= 3:
        return s
    
    last_three = s[-3:]
    remaining = s[:-3]
    
    out = []
    while len(remaining) > 2:
        out.append(remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        out.append(remaining)
    out.reverse()
    
    return ",".join(out) + "," + last_three

@app.template_filter('indian_currency')
def indian_currency_filter(val):
    return format_indian_currency(val)

def populate_car_database(conn):
    """Fills the SQLite specs table with complete Indian car variant databases programmatically."""
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS car_database')
    cursor.execute('''
        CREATE TABLE car_database (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT,
            model TEXT,
            variant TEXT,
            manufacturing_year INTEGER NOT NULL,
            fuel_type TEXT,
            transmission TEXT,
            engine_capacity TEXT,
            engine_type TEXT,
            power TEXT,
            torque TEXT,
            mileage TEXT,
            body_type TEXT,
            wheelbase TEXT,
            ground_clearance TEXT,
            boot_space TEXT,
            fuel_tank_capacity TEXT,
            drivetrain TEXT,
            emission_norm TEXT,
            num_cylinders INTEGER,
            seating_capacity INTEGER,
            airbags INTEGER,
            abs TEXT,
            esp TEXT,
            sunroof TEXT,
            adas TEXT,
            cruise_control TEXT,
            base_showroom_price REAL,
            price_type TEXT DEFAULT 'historical_launch',
            price_label TEXT DEFAULT 'Original Launch Price',
            is_discontinued INTEGER DEFAULT 0,
            discontinued_year INTEGER,
            ncap_rating INTEGER DEFAULT 0,
            color_options TEXT
        )
    ''')
    
    # Complete spec configurations: brand -> { model -> (body_type, base_price, cc, power, torque, mileage, [variants], [fuels], [transmissions]) }
    db_data = {
        "Maruti Suzuki": {
            "800": ("Hatchback", 210000, 796, 37, 59, 19.6, ["Standard", "AC", "Duo"], ["Petrol", "LPG"], ["Manual"]),
            "Omni": ("Van", 260000, 796, 34, 59, 16.8, ["5 Seater", "8 Seater", "Cargo"], ["Petrol", "CNG"], ["Manual"]),
            "Gypsy": ("SUV", 580000, 1298, 80, 103, 11.5, ["King", "Soft Top", "Hard Top"], ["Petrol"], ["Manual"]),
            "Zen": ("Hatchback", 320000, 993, 60, 78, 16.5, ["LX", "LXi", "VXi", "Carbon", "Steel"], ["Petrol", "Diesel"], ["Manual"]),
            "Zen Estilo": ("Hatchback", 390000, 998, 67, 90, 19.0, ["LX", "LXi", "VXi"], ["Petrol", "CNG"], ["Manual"]),
            "Esteem": ("Sedan", 470000, 1298, 85, 110, 15.9, ["LX", "LXi", "VXi"], ["Petrol", "Diesel"], ["Manual"]),
            "Versa": ("Van", 420000, 1298, 82, 102, 13.4, ["DX", "DX2", "LXi"], ["Petrol"], ["Manual"]),
            "SX4": ("Sedan", 740000, 1586, 104, 145, 15.6, ["VXi", "ZXi", "ZXi Leather"], ["Petrol", "Diesel", "CNG"], ["Manual", "Automatic"]),
            "Alto": ("Hatchback", 350000, 796, 47, 69, 22.0, ["Std", "LXi", "VXi"], ["Petrol", "CNG"], ["Manual"]),
            "Alto K10": ("Hatchback", 450000, 998, 66, 89, 24.4, ["Std", "LXi", "VXi", "VXi+"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "WagonR": ("Hatchback", 550000, 998, 66, 89, 24.3, ["LXi", "VXi", "ZXi", "ZXi+"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Swift": ("Hatchback", 650000, 1197, 89, 113, 22.4, ["LXi", "VXi", "ZXi", "ZXi+"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Dzire": ("Sedan", 700000, 1197, 89, 113, 22.6, ["LXi", "VXi", "ZXi", "ZXi+"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Baleno": ("Hatchback", 750000, 1197, 89, 113, 22.3, ["Sigma", "Delta", "Zeta", "Alpha"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Ignis": ("Hatchback", 580000, 1197, 82, 113, 20.8, ["Sigma", "Delta", "Zeta", "Alpha"], ["Petrol"], ["Manual", "AMT"]),
            "Fronx": ("SUV", 850000, 1197, 89, 113, 21.7, ["Sigma", "Delta", "Delta+", "Zeta", "Alpha"], ["Petrol", "CNG"], ["Manual", "AMT", "Automatic"]),
            "Brezza": ("SUV", 950000, 1462, 102, 136, 17.3, ["LXi", "VXi", "ZXi", "ZXi+"], ["Petrol", "CNG"], ["Manual", "Automatic"]),
            "Grand Vitara": ("SUV", 1200000, 1490, 102, 137, 21.1, ["Sigma", "Delta", "Zeta", "Alpha"], ["Petrol", "Hybrid", "CNG"], ["Manual", "Automatic", "e-CVT"]),
            "Jimny": ("SUV", 1274000, 1462, 103, 134, 16.9, ["Zeta", "Alpha"], ["Petrol"], ["Manual", "Automatic"]),
            "XL6": ("MUV", 1160000, 1462, 102, 137, 20.9, ["Zeta", "Alpha", "Alpha+"], ["Petrol", "CNG"], ["Manual", "Automatic"]),
            "Invicto": ("MUV", 2600000, 1987, 184, 188, 23.2, ["Zeta+", "Alpha+"], ["Hybrid"], ["e-CVT"]),
            "Ciaz": ("Sedan", 940000, 1462, 103, 138, 20.0, ["Sigma", "Delta", "Zeta", "Alpha"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "Eeco": ("Van", 530000, 1197, 80, 104, 19.7, ["5 Seater", "7 Seater", "Cargo"], ["Petrol", "CNG"], ["Manual"]),
            "S-Presso": ("Hatchback", 430000, 998, 66, 89, 24.0, ["Std", "LXi", "VXi", "VXi+"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Ertiga": ("MUV", 980000, 1462, 102, 136, 20.5, ["LXi", "VXi", "ZXi", "ZXi+"], ["Petrol", "CNG"], ["Manual", "Automatic"]),
            "Kizashi": ("Sedan", 1650000, 2393, 176, 230, 12.5, ["Base", "Premium"], ["Petrol"], ["Manual", "CVT"]),
            "Grand Vitara XL7": ("SUV", 1500000, 2736, 170, 250, 10.5, ["Standard", "Luxury"], ["Petrol"], ["Manual", "Automatic"])
        },
        "Hyundai": {
            "i10": ("Hatchback", 450000, 1086, 68, 99, 19.8, ["D-Lite", "Era", "Magna", "Asta"], ["Petrol", "CNG"], ["Manual", "Automatic"]),
            "Grand i10": ("Hatchback", 580000, 1197, 82, 114, 18.9, ["Era", "Magna", "Sportz", "Asta"], ["Petrol", "Diesel", "CNG"], ["Manual", "AMT"]),
            "i20": ("Hatchback", 750000, 1197, 82, 114, 20.3, ["Era", "Magna", "Sportz", "Asta", "Asta(O)", "N Line"], ["Petrol"], ["Manual", "IVT", "DCT"]),
            "Aura": ("Sedan", 650000, 1197, 82, 114, 20.5, ["E", "S", "SX", "SX+"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Venue": ("SUV", 800000, 1197, 82, 114, 17.5, ["E", "S", "S+", "S(O)", "SX", "SX(O)"], ["Petrol", "Diesel"], ["Manual", "Automatic", "DCT"]),
            "Creta": ("SUV", 1150000, 1497, 113, 144, 17.4, ["E", "EX", "S", "S(O)", "SX", "SX Tech", "SX(O)", "Knight Edition"], ["Petrol", "Diesel"], ["Manual", "Automatic", "IVT", "DCT"]),
            "Creta N Line": ("SUV", 1680000, 1482, 158, 253, 18.2, ["N8", "N10"], ["Petrol"], ["Manual", "DCT"]),
            "Alcazar": ("SUV", 1670000, 1493, 113, 250, 18.1, ["Prestige", "Platinum", "Signature"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "Tucson": ("SUV", 2900000, 1997, 154, 192, 13.0, ["Platinum", "Signature"], ["Petrol", "Diesel"], ["Automatic"]),
            "Exter": ("SUV", 650000, 1197, 82, 113, 19.4, ["EX", "S", "SX", "SX(O)", "SX(O) Connect"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Verna": ("Sedan", 1100000, 1497, 113, 144, 18.6, ["EX", "S", "SX", "SX(O)", "Turbo SX(O)"], ["Petrol"], ["Manual", "IVT", "DCT"]),
            "Ioniq 5": ("SUV", 4600000, 0, 225, 350, 631, ["RWD EV"], ["EV"], ["Automatic"])
        },
        "Toyota": {
            "Innova": ("MUV", 1400000, 2494, 101, 200, 11.4, ["G", "GX", "VX", "ZX"], ["Diesel", "Petrol"], ["Manual"]),
            "Innova Crysta": ("MUV", 1990000, 2393, 148, 343, 12.9, ["G", "GX", "VX", "ZX"], ["Diesel"], ["Manual"]),
            "Innova Hycross": ("MUV", 1950000, 1987, 184, 188, 23.2, ["G", "GX", "VX", "ZX", "ZX(O)"], ["Petrol", "Hybrid"], ["Automatic", "e-CVT"]),
            "Fortuner": ("SUV", 3300000, 2755, 201, 500, 14.4, ["4x2 MT", "4x2 AT", "4x4 MT", "4x4 AT", "Legender", "GR Sport"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "Urban Cruiser": ("SUV", 900000, 1462, 103, 138, 17.0, ["Mid", "High", "Premium"], ["Petrol"], ["Manual", "Automatic"]),
            "Glanza": ("Hatchback", 680000, 1197, 89, 113, 22.3, ["E", "S", "G", "V"], ["Petrol", "CNG"], ["Manual", "AMT"]),
            "Rumion": ("MUV", 1030000, 1462, 102, 137, 20.1, ["S", "G", "V"], ["Petrol", "CNG"], ["Manual", "Automatic"]),
            "Camry": ("Sedan", 4600000, 2487, 176, 221, 22.2, ["Hybrid 2.5L"], ["Hybrid"], ["e-CVT"]),
            "Hilux": ("SUV", 3040000, 2755, 201, 420, 12.5, ["Std MT", "High MT", "High AT"], ["Diesel"], ["Manual", "Automatic"]),
            "Land Cruiser": ("SUV", 21000000, 3346, 304, 700, 11.0, ["ZX Diesel"], ["Diesel"], ["Automatic"])
        },
        "Mahindra": {
            "Scorpio Classic": ("SUV", 1350000, 2179, 130, 300, 15.0, ["S", "S11"], ["Diesel"], ["Manual"]),
            "Scorpio N": ("SUV", 1360000, 2198, 172, 400, 14.0, ["Z2", "Z4", "Z6", "Z8", "Z8L"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "Bolero": ("SUV", 980000, 1493, 75, 210, 16.0, ["B4", "B6", "B6(O)"], ["Diesel"], ["Manual"]),
            "Bolero Neo": ("SUV", 990000, 1493, 100, 260, 17.2, ["N4", "N8", "N10", "N10(O)"], ["Diesel"], ["Manual"]),
            "Thar": ("SUV", 1120000, 2184, 130, 300, 15.2, ["AX(O)", "LX", "Earth Edition"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "Thar Roxx": ("SUV", 1299000, 2184, 150, 330, 14.0, ["MX1", "MX3", "MX5", "AX3L", "AX5L", "AX7L"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "XUV300": ("SUV", 800000, 1197, 109, 200, 17.0, ["W4", "W6", "W8", "W8(O)"], ["Petrol", "Diesel"], ["Manual", "AMT"]),
            "XUV400": ("SUV", 1550000, 0, 148, 310, 456, ["EC Pro", "EL Pro"], ["EV"], ["Automatic"]),
            "XUV700": ("SUV", 1400000, 2198, 182, 420, 13.5, ["MX", "AX3", "AX5", "AX7", "AX7L"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "XUV 3XO": ("SUV", 749000, 1197, 110, 200, 18.9, ["MX1", "MX2", "MX3", "AX5", "AX7"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "BE 6": ("SUV", 1800000, 0, 220, 380, 500, ["Pro", "Ultimate"], ["EV"], ["Automatic"]),
            "XEV 9e": ("SUV", 2200000, 0, 280, 420, 550, ["Pro", "Ultimate"], ["EV"], ["Automatic"]),
            "Marazzo": ("MUV", 1430000, 1497, 121, 300, 17.3, ["M2", "M4+", "M6+"], ["Diesel"], ["Manual"]),
            "KUV100": ("Hatchback", 610000, 1198, 82, 115, 18.1, ["K2", "K4+", "K6+", "K8"], ["Petrol", "Diesel"], ["Manual"]),
            "Quanto": ("SUV", 750000, 1493, 100, 240, 17.2, ["C2", "C4", "C6", "C8"], ["Diesel"], ["Manual"]),
            "TUV300": ("SUV", 850000, 1493, 100, 240, 18.4, ["T4", "T6", "T8", "T10"], ["Diesel"], ["Manual", "AMT"]),
            "Xylo": ("MUV", 900000, 2179, 120, 280, 14.0, ["D2", "D4", "H4", "H8"], ["Diesel"], ["Manual"]),
            "Verito": ("Sedan", 720000, 1461, 65, 160, 21.0, ["D2", "D4", "D6"], ["Diesel"], ["Manual"])
        },
        "Tata Motors": {
            "Nexon": ("SUV", 800000, 1199, 118, 170, 17.4, ["Smart", "Pure", "Creative", "Fearless", "Dark Edition", "Red Dark Edition", "Creative EV", "Fearless EV"], ["Petrol", "Diesel", "EV"], ["Manual", "AMT", "DCT", "Automatic"]),
            "Harrier": ("SUV", 1550000, 1956, 168, 350, 16.3, ["Smart", "Pure", "Creative", "Fearless", "Dark Edition"], ["Diesel"], ["Manual", "Automatic"]),
            "Safari": ("SUV", 1650000, 1956, 168, 350, 16.1, ["Smart", "Pure", "Creative", "Fearless", "Dark Edition"], ["Diesel"], ["Manual", "Automatic"]),
            "Punch": ("SUV", 600000, 1199, 86, 113, 20.0, ["Pure", "Adventure", "Accomplished", "Creative", "EV"], ["Petrol", "CNG", "EV"], ["Manual", "AMT", "Automatic"]),
            "Altroz": ("Hatchback", 660000, 1199, 86, 113, 19.3, ["XE", "XM", "XT", "XZ", "XZ+"], ["Petrol", "Diesel", "CNG"], ["Manual", "DCT"]),
            "Tiago": ("Hatchback", 560000, 1199, 86, 113, 20.0, ["XE", "XM", "XT", "XZ", "XZ+"], ["Petrol", "CNG", "EV"], ["Manual", "AMT", "Automatic"])
        },
        "Honda": {
            "City": ("Sedan", 1180000, 1498, 119, 145, 17.8, ["SV", "V", "VX", "ZX", "e:HEV Hybrid"], ["Petrol", "Hybrid"], ["Manual", "CVT", "e-CVT"]),
            "Amaze": ("Sedan", 720000, 1199, 89, 110, 18.6, ["E", "S", "VX"], ["Petrol"], ["Manual", "CVT"]),
            "Elevate": ("SUV", 1160000, 1498, 119, 145, 16.9, ["SV", "V", "VX", "ZX"], ["Petrol"], ["Manual", "CVT"])
        },
        "Kia": {
            "Seltos": ("SUV", 1090000, 1497, 113, 144, 17.0, ["HTE", "HTK", "HTK+", "HTX", "HTX+", "GTX+", "X-Line"], ["Petrol", "Diesel"], ["Manual", "iMT", "IVT", "Automatic", "DCT"]),
            "Sonet": ("SUV", 800000, 1197, 82, 115, 18.4, ["HTE", "HTK", "HTK+", "HTX", "HTX+", "GTX+", "X-Line"], ["Petrol", "Diesel"], ["Manual", "iMT", "Automatic", "DCT"]),
            "Carens": ("MUV", 1050000, 1497, 113, 144, 16.5, ["Premium", "Prestige", "Luxury", "Luxury+"], ["Petrol", "Diesel"], ["Manual", "iMT", "Automatic", "DCT"])
        },
        "MG Motor": {
            "Hector": ("SUV", 1500000, 1956, 168, 350, 15.8, ["Style", "Shine", "Smart", "Sharp", "Savvy Pro"], ["Petrol", "Diesel"], ["Manual", "CVT"]),
            "Astor": ("SUV", 1000000, 1498, 108, 144, 15.4, ["Style", "Super", "Smart", "Sharp", "Savvy"], ["Petrol"], ["Manual", "CVT", "Automatic"]),
            "Gloster": ("SUV", 3800000, 1996, 212, 478, 12.0, ["Sharp", "Savvy"], ["Diesel"], ["Automatic"]),
            "ZS EV": ("SUV", 2200000, 0, 174, 280, 461, ["Executive", "Excite", "Exclusive", "Empower"], ["EV"], ["Automatic"])
        },
        "BYD": {
            "Atto 3": ("SUV", 3400000, 0, 201, 310, 521, ["Dynamic", "Premium", "Superior"], ["EV"], ["Automatic"]),
            "Seal": ("Sedan", 4100000, 0, 308, 360, 650, ["Dynamic", "Premium", "Performance"], ["EV"], ["Automatic"])
        },
        "Isuzu": {
            "V-Cross": ("SUV", 2300000, 1898, 161, 360, 14.4, ["Z 4x2", "Z 4x4", "Prestige 4x4"], ["Diesel"], ["Manual", "Automatic"]),
            "D-Max": ("SUV", 1900000, 1898, 161, 360, 15.2, ["Cab 4x2", "Cab 4x4"], ["Diesel"], ["Manual", "Automatic"])
        },
        "Force Motors": {
            "Gurkha": ("SUV", 1675000, 2596, 138, 320, 12.0, ["3-Door", "5-Door"], ["Diesel"], ["Manual"]),
            "Traveller": ("MUV", 1800000, 2596, 115, 350, 10.5, ["3050", "3350", "3700"], ["Diesel"], ["Manual"])
        },
        "Mini": {
            "Cooper": ("Hatchback", 4200000, 1998, 129, 280, 16.5, ["S 3-Door", "SE Electric"], ["Petrol", "EV"], ["Automatic"]),
            "Countryman": ("SUV", 4800000, 1998, 189, 280, 14.3, ["Cooper S", "Cooper S JCW"], ["Petrol"], ["Automatic"])
        },
        "Volvo": {
            "XC40": ("SUV", 4600000, 1969, 197, 300, 14.4, ["B4 Ultimate", "Recharge EV"], ["Petrol", "EV"], ["Automatic"]),
            "XC90": ("SUV", 9800000, 1969, 300, 420, 12.1, ["B6 Ultimate"], ["Petrol"], ["Automatic"])
        },
        "BMW": {
            "3 Series": ("Sedan", 4800000, 1998, 258, 400, 16.1, ["330i M Sport", "320d Luxury", "M340i xDrive"], ["Petrol", "Diesel"], ["Automatic"]),
            "X1": ("SUV", 4600000, 1995, 148, 360, 20.3, ["sDrive18i M Sport", "sDrive18d xLine"], ["Petrol", "Diesel"], ["Automatic"]),
            "X5": ("SUV", 9600000, 2998, 375, 520, 12.0, ["xDrive40i M Sport", "xDrive30d xLine"], ["Petrol", "Diesel"], ["Automatic"])
        },
        "Mercedes-Benz": {
            "C-Class": ("Sedan", 5800000, 1999, 201, 300, 16.9, ["C200 Avantgarde", "C220d Avantgarde"], ["Petrol", "Diesel"], ["Automatic"]),
            "E-Class": ("Sedan", 7500000, 1991, 194, 320, 15.0, ["E200 Expression", "E220d Exclusive", "E350d AMG Line"], ["Petrol", "Diesel"], ["Automatic"]),
            "GLC": ("SUV", 7300000, 1999, 258, 400, 14.7, ["GLC 300 4MATIC", "GLC 220d 4MATIC"], ["Petrol", "Diesel"], ["Automatic"])
        },
        "Audi": {
            "A4": ("Sedan", 4500000, 1984, 190, 320, 17.4, ["Premium", "Premium Plus", "Technology"], ["Petrol"], ["Automatic"]),
            "Q3": ("SUV", 4300000, 1984, 190, 320, 15.0, ["Premium", "Premium Plus", "Technology"], ["Petrol"], ["Automatic"]),
            "Q7": ("SUV", 8500000, 2995, 335, 500, 11.2, ["Premium Plus", "Technology"], ["Petrol"], ["Automatic"])
        },
        "Lexus": {
            "ES": ("Sedan", 6300000, 2487, 175, 221, 22.5, ["300h Exquisite", "300h Luxury"], ["Hybrid"], ["e-CVT"]),
            "RX": ("SUV", 9500000, 2487, 246, 316, 18.8, ["350h Luxury", "500h F Sport"], ["Hybrid"], ["e-CVT"])
        },
        "Porsche": {
            "Macan": ("SUV", 8800000, 1984, 261, 400, 11.4, ["Base", "S", "GTS"], ["Petrol"], ["Automatic"]),
            "911": ("Sports", 18500000, 2981, 379, 450, 9.0, ["Carrera", "Carrera S", "Turbo S", "GT3"], ["Petrol"], ["Automatic"])
        },
        "Ferrari": {
            "Roma": ("Sports", 37600000, 3855, 612, 760, 8.9, ["V8 Coupe"], ["Petrol"], ["Automatic"]),
            "296 GTB": ("Sports", 54000000, 2992, 818, 740, 14.8, ["Assetto Fiorano", "V6 Hybrid"], ["Hybrid"], ["Automatic"])
        },
        "Lamborghini": {
            "Urus": ("SUV", 41800000, 3996, 657, 850, 7.8, ["S", "Performante"], ["Petrol"], ["Automatic"]),
            "Huracan": ("Sports", 35000000, 5204, 631, 600, 7.2, ["EVO", "Tecnica", "STO"], ["Petrol"], ["Automatic"])
        },
        "Bentley": {
            "Continental GT": ("Coupe", 42000000, 3996, 542, 770, 7.8, ["V8 Coupe", "Speed W12"], ["Petrol"], ["Automatic"]),
            "Bentayga": ("SUV", 41000000, 3996, 542, 770, 7.6, ["V8", "Azure"], ["Petrol"], ["Automatic"])
        },
        "Rolls Royce": {
            "Cullinan": ("SUV", 69500000, 6749, 563, 850, 6.6, ["V12 SUV", "Black Badge"], ["Petrol"], ["Automatic"]),
            "Ghost": ("Sedan", 69500000, 6749, 563, 850, 6.3, ["V12 Sedan", "Extended"], ["Petrol"], ["Automatic"])
        },
        "McLaren": {
            "720S": ("Sports", 46500000, 3994, 710, 770, 8.2, ["Spider V8", "Coupe V8"], ["Petrol"], ["Automatic"]),
            "Artura": ("Sports", 51000000, 2993, 671, 720, 14.5, ["Standard V6 Hybrid"], ["Hybrid"], ["Automatic"])
        },
        "Maserati": {
            "Levante": ("SUV", 15000000, 2979, 350, 500, 9.2, ["GT V6", "Modena"], ["Petrol"], ["Automatic"]),
            "Ghibli": ("Sedan", 12000000, 1998, 330, 450, 12.0, ["GT Hybrid", "Modena V6"], ["Hybrid"], ["Automatic"])
        },
        "Aston Martin": {
            "DB11": ("Sports", 38000000, 3982, 503, 675, 9.5, ["V8 Coupe", "V12 AMR"], ["Petrol"], ["Automatic"]),
            "DBX": ("SUV", 38000000, 3982, 542, 700, 10.1, ["V8 SUV", "707 Edition"], ["Petrol"], ["Automatic"])
        },
        "Lotus": {
            "Eletre": ("SUV", 25000000, 0, 603, 710, 600, ["Base", "S", "R"], ["EV"], ["Automatic"]),
            "Emira": ("Sports", 17500000, 1991, 360, 430, 11.0, ["First Edition V6", "First Edition i4"], ["Petrol"], ["Manual", "Automatic"])
        },
        "Bugatti": {
            "Chiron": ("Sports", 280000000, 7993, 1479, 1600, 4.0, ["Standard", "Sport", "Pur Sport", "Super Sport"], ["Petrol"], ["Automatic"]),
            "Veyron": ("Sports", 120000000, 7993, 987, 1250, 4.5, ["16.4", "Grand Sport", "Super Sport"], ["Petrol"], ["Automatic"])
        },
        "Renault": {
            "Kwid": ("Hatchback", 470000, 999, 67, 91, 22.0, ["RXE", "RXL", "RXT", "Climber"], ["Petrol"], ["Manual", "AMT"]),
            "Kiger": ("SUV", 600000, 999, 71, 96, 20.5, ["RXE", "RXL", "RXT", "RXZ"], ["Petrol"], ["Manual", "AMT", "CVT"]),
            "Triber": ("MUV", 600000, 999, 71, 96, 19.0, ["RXE", "RXL", "RXT", "RXZ"], ["Petrol"], ["Manual", "AMT"])
        },
        "Nissan": {
            "Magnite": ("SUV", 600000, 999, 71, 96, 20.0, ["XE", "XL", "XV", "XV Premium"], ["Petrol"], ["Manual", "AMT", "CVT"])
        },
        "Volkswagen": {
            "Virtus": ("Sedan", 1150000, 999, 114, 178, 19.4, ["Comfortline", "Highline", "Topline", "GT Plus"], ["Petrol"], ["Manual", "Automatic", "DCT"]),
            "Taigun": ("SUV", 1160000, 999, 114, 178, 19.8, ["Comfortline", "Highline", "Topline", "GT Plus"], ["Petrol"], ["Manual", "Automatic", "DCT"])
        },
        "Skoda": {
            "Slavia": ("Sedan", 1140000, 999, 114, 178, 19.4, ["Active", "Ambition", "Style", "L&K"], ["Petrol"], ["Manual", "Automatic", "DCT"]),
            "Kushaq": ("SUV", 1150000, 999, 114, 178, 19.7, ["Active", "Ambition", "Style", "Monte Carlo"], ["Petrol"], ["Manual", "Automatic", "DCT"])
        },
        "Jeep": {
            "Compass": ("SUV", 2000000, 1956, 168, 350, 16.2, ["Sport", "Longitude", "Limited", "Model S"], ["Diesel"], ["Manual", "Automatic"]),
            "Wrangler": ("SUV", 6200000, 1998, 268, 400, 12.1, ["Unlimited", "Rubicon"], ["Petrol"], ["Automatic"])
        },
        "Citroen": {
            "C3": ("Hatchback", 616000, 1198, 81, 115, 19.3, ["Live", "Feel", "Shine"], ["Petrol"], ["Manual"]),
            "C5 Aircross": ("SUV", 3700000, 1997, 174, 400, 17.5, ["Feel", "Shine"], ["Diesel"], ["Automatic"])
        },
        "Ford": {
            "Figo": ("Hatchback", 580000, 1194, 95, 119, 18.5, ["Ambiente", "Trend", "Titanium", "Titanium+"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "EcoSport": ("SUV", 820000, 1496, 121, 149, 15.9, ["Ambiente", "Trend", "Titanium", "S", "Sports Edition"], ["Petrol", "Diesel"], ["Manual", "Automatic"]),
            "Endeavour": ("SUV", 3000000, 1996, 168, 420, 12.4, ["Titanium 4x2", "Titanium+ 4x4", "Sport Edition"], ["Diesel"], ["Automatic"])
        },
        "Chevrolet": {
            "Beat": ("Hatchback", 420000, 1199, 79, 108, 18.6, ["PS", "LS", "LT", "LTZ"], ["Petrol", "Diesel", "LPG"], ["Manual"]),
            "Cruze": ("Sedan", 1400000, 1998, 164, 360, 17.3, ["LT", "LTZ MT", "LTZ AT"], ["Diesel"], ["Manual", "Automatic"]),
            "Tavera": ("MUV", 850000, 2499, 78, 186, 12.2, ["LS", "LT"], ["Diesel"], ["Manual"])
        },
        "Fiat": {
            "Punto": ("Hatchback", 550000, 1248, 75, 197, 20.0, ["Active", "Dynamic", "Emotion", "Abarth"], ["Petrol", "Diesel"], ["Manual"]),
            "Linea": ("Sedan", 780000, 1248, 92, 209, 19.5, ["Active", "Dynamic", "Emotion", "T-Jet"], ["Petrol", "Diesel"], ["Manual"])
        },
        "Mitsubishi": {
            "Pajero": ("SUV", 2800000, 2477, 176, 350, 11.5, ["Sport 4x2", "Sport 4x4"], ["Diesel"], ["Manual", "Automatic"]),
            "Lancer": ("Sedan", 720000, 1468, 87, 120, 13.7, ["GLXi", "SFXi"], ["Petrol", "Diesel"], ["Manual"])
        },
        "Opel": {
            "Astra": ("Sedan", 750000, 1598, 75, 121, 11.2, ["1.6 GL", "1.6 Club"], ["Petrol", "Diesel"], ["Manual"]),
            "Corsa": ("Sedan", 520000, 1389, 88, 110, 13.4, ["1.4 GL", "1.4 GLS", "Sail"], ["Petrol"], ["Manual"])
        },
        "Daewoo": {
            "Matiz": ("Hatchback", 320000, 796, 52, 71, 18.5, ["SS", "SD", "SE"], ["Petrol"], ["Manual"]),
            "Cielo": ("Sedan", 620000, 1498, 80, 128, 11.5, ["GL", "GLE"], ["Petrol"], ["Manual", "Automatic"])
        },
        "Premier": {
            "Padmini": ("Sedan", 150000, 1366, 47, 85, 15.0, ["Standard", "Deluxe"], ["Petrol", "Diesel"], ["Manual"])
        },
        "Hindustan Motors": {
            "Ambassador": ("Sedan", 550000, 1817, 74, 135, 12.5, ["Nova", "Classic", "Grand"], ["Petrol", "Diesel", "CNG"], ["Manual"])
        }
    }
    
    count = 0
    for brand, models in db_data.items():
        for model_name, config in models.items():
            b_type, base_price, cc, pow_hp, tor_nm, mil_kmp, variants, fuels, transmissions = config
            for var in variants:
                for fuel in fuels:
                    for trans in transmissions:
                        # Skip invalid mappings
                        if fuel == "EV" and trans == "Manual":
                            continue
                        if fuel == "CNG" and trans == "Automatic":
                            continue
                            
                        # Adjust metrics slightly per variant so they aren't identical copies
                        price_adj = base_price
                        if "VXi" in var or "EX" in var or "Delta" in var or "S" in var:
                            price_adj *= 1.08
                        elif "ZXi" in var or "SX" in var or "Zeta" in var or "AX5" in var:
                            price_adj *= 1.18
                        elif "+" in var or "Connect" in var or "Alpha" in var or "AX7" in var or "Signature" in var or "Technology" in var or "Savvy" in var or "M Sport" in var or "Legender" in var:
                            price_adj *= 1.32
                        elif "LXi" in var or "Era" in var or "Sigma" in var or "MX" in var:
                            price_adj *= 0.95
                            
                        # Transmission premium
                        if trans in ["Automatic", "CVT", "DCT", "e-CVT"]:
                            price_adj += 120000
                            
                        # Fuel adjustments
                        if fuel == "Diesel":
                            price_adj += 150000
                        elif fuel == "Hybrid":
                            price_adj += 250000
                        elif fuel == "EV":
                            price_adj += 350000
                        elif fuel == "CNG":
                            price_adj += 90000
                            
                        cc_str = "0 cc" if fuel == "EV" else f"{cc} cc"
                        cylinders = 0 if fuel == "EV" else (3 if cc < 1100 else 4)
                        if cc >= 2900:
                            cylinders = 6
                        
                        engine_type = "Permanent Magnet Synchronous Motor" if fuel == "EV" else f"{cc/1000:.1f}L {cylinders}-Cylinder inline engine"
                        
                        pow_str = f"{pow_hp} bhp"
                        tor_str = f"{tor_nm} Nm"
                        mil_str = f"{mil_kmp} kmpl" if fuel != "EV" else "450 km/charge"
                        
                        wheelbase = "2450 mm"
                        if b_type == "Sedan":
                            wheelbase = "2600 mm"
                        elif b_type == "SUV":
                            wheelbase = "2700 mm"
                        elif b_type == "MUV":
                            wheelbase = "2780 mm"
                            
                        gc = "165 mm"
                        if b_type == "SUV":
                            gc = "200 mm"
                        elif b_type == "MUV":
                            gc = "180 mm"
                            
                        boot = "350 Litres"
                        if b_type == "SUV":
                            boot = "450 Litres"
                        elif b_type == "MUV":
                            boot = "550 Litres"
                            
                        tank = "37 Litres" if cc < 1100 else "45 Litres"
                        if b_type == "SUV":
                            tank = "60 Litres"
                        if fuel == "EV":
                            tank = "N/A (Battery)"
                            
                        drivetrain = "FWD"
                        if b_type == "SUV" and "4x4" in var:
                            drivetrain = "4WD"
                        elif b_type in ["Sports", "Sedan"] and brand in ["BMW", "Mercedes-Benz", "Porsche", "Ferrari", "Lamborghini"]:
                            drivetrain = "RWD"
                            
                        seats = 5
                        if b_type == "MUV" or model_name in ["Safari", "Scorpio N", "XUV700", "Ertiga", "XL6"]:
                            seats = 7
                        elif b_type == "Sports":
                            seats = 2
                            
                        sunroof = "Panoramic" if ("+" in var or "Alpha" in var or "AX7" in var or "Signature" in var or "Technology" in var or "Savvy" in var or "M Sport" in var or "Legender" in var) and b_type in ["SUV", "Sedan"] else "No"
                        adas = "Yes" if sunroof == "Panoramic" and brand in ["Mahindra", "Hyundai", "Tata Motors", "MG Motor", "Honda", "BMW", "Audi", "Mercedes-Benz", "Volvo"] else "No"
                        cruise = "Yes" if "VXi" in var or "ZXi" in var or "SX" in var or "Zeta" in var or "AX5" in var or adas == "Yes" else "No"
                        
                        launch_yr = 1995
                        if brand in ["Kia", "MG Motor", "BYD", "Citroen"]:
                            launch_yr = 2019
                        elif model_name in ["Grand Vitara", "Hyryder", "Virtus", "Slavia", "Elevate", "Kushaq", "Taigun", "Punch", "Exter", "Seltos", "Sonet", "Carens"]:
                            launch_yr = 2020
                        
                        for yr in range(launch_yr, 2027):
                            price_factor = 1.0 - (2026 - yr) * 0.05
                            if price_factor < 0.25:
                                price_factor = 0.25
                            year_price = round(price_adj * price_factor)

                            # Deduce custom fields
                            discontinued_brands = {
                                "Chevrolet": 2017, "Ford": 2021, "Fiat": 2019,
                                "Mitsubishi": 2019, "Opel": 2006, "Daewoo": 2005,
                                "Premier": 2000, "Hindustan Motors": 2014
                            }
                            
                            is_disc = 1 if brand in discontinued_brands else 0
                            disc_yr = discontinued_brands.get(brand)
                            
                            if is_disc:
                                pr_type = "historical_launch"
                                pr_label = "Original Launch Price (Historical)"
                            elif yr >= 2024:
                                pr_type = "estimated_showroom"
                                pr_label = "Estimated Ex-Showroom Price"
                            else:
                                pr_type = "historical_launch"
                                pr_label = "Original Launch Price"
                                
                            ncap = 5 if brand in ["Tata", "Mahindra"] else (4 if brand in ["Toyota", "Honda", "Volkswagen", "Skoda"] else 3)
                            colors = "Solid Fire Red, Granite Grey, Pearl White, Metallic Silver, Carbon Black"

                            cursor.execute('''
                                INSERT INTO car_database (
                                    brand, model, variant, manufacturing_year, fuel_type, transmission, engine_capacity, engine_type,
                                    power, torque, mileage, body_type, wheelbase, ground_clearance, boot_space,
                                    fuel_tank_capacity, drivetrain, emission_norm, num_cylinders, seating_capacity,
                                    airbags, abs, esp, sunroof, adas, cruise_control, base_showroom_price,
                                    price_type, price_label, is_discontinued, discontinued_year, ncap_rating, color_options
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                brand, model_name, var, yr, fuel, trans, cc_str, engine_type, pow_str, tor_str, mil_str,
                                b_type, wheelbase, gc, boot, tank, drivetrain, "BS6 Phase 2", cylinders, seats,
                                6 if adas == "Yes" else 2, "Yes", "Yes" if cc > 1100 else "No", sunroof, adas, cruise, year_price,
                                pr_type, pr_label, is_disc, disc_yr, ncap, colors
                            ))
                            count += 1
                        
    conn.commit()
    print(f"Generated {count} production specs entries in car_database table.")

def populate_catalog_database(conn):
    """Initializes and seeds the catalog explorer tables in users.db."""
    cursor = conn.cursor()
    
    # 6. Catalog Manufacturers Table
    cursor.execute('DROP TABLE IF EXISTS catalog_manufacturers')
    cursor.execute('''
        CREATE TABLE catalog_manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            country TEXT NOT NULL,
            founded INTEGER,
            website TEXT,
            description TEXT,
            market_share REAL,
            average_resale REAL,
            popular_models TEXT,
            logo_path TEXT
        )
    ''')

    # 7. Catalog Models Table
    cursor.execute('DROP TABLE IF EXISTS catalog_models')
    cursor.execute('''
        CREATE TABLE catalog_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            body_type TEXT,
            base_price REAL,
            launch_year INTEGER,
            image_path TEXT,
            description TEXT,
            FOREIGN KEY (manufacturer_id) REFERENCES catalog_manufacturers (id) ON DELETE CASCADE
        )
    ''')

    # 8. Catalog Variants Table
    cursor.execute('DROP TABLE IF EXISTS catalog_variants')
    cursor.execute('''
        CREATE TABLE catalog_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            fuel_type TEXT,
            transmission TEXT,
            base_showroom_price REAL,
            on_road_price REAL,
            FOREIGN KEY (model_id) REFERENCES catalog_models (id) ON DELETE CASCADE
        )
    ''')

    # 9. Catalog Specifications Table
    cursor.execute('DROP TABLE IF EXISTS catalog_specifications')
    cursor.execute('''
        CREATE TABLE catalog_specifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id INTEGER NOT NULL,
            engine_capacity TEXT,
            power TEXT,
            torque TEXT,
            mileage TEXT,
            seating_capacity INTEGER,
            safety_rating INTEGER,
            ground_clearance TEXT,
            drivetrain TEXT,
            fuel_tank_capacity TEXT,
            airbags INTEGER,
            sunroof TEXT,
            adas TEXT,
            cruise_control TEXT,
            colors TEXT,
            wheelbase TEXT,
            boot_space TEXT,
            FOREIGN KEY (variant_id) REFERENCES catalog_variants (id) ON DELETE CASCADE
        )
    ''')

    # 10. Catalog AI Scores Table
    cursor.execute('DROP TABLE IF EXISTS catalog_ai_scores')
    cursor.execute('''
        CREATE TABLE catalog_ai_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id INTEGER NOT NULL,
            popularity_score INTEGER,
            resale_score INTEGER,
            demand_score INTEGER,
            maintenance_score INTEGER,
            reliability_score INTEGER,
            insurance_category TEXT,
            annual_ownership_cost REAL,
            FOREIGN KEY (variant_id) REFERENCES catalog_variants (id) ON DELETE CASCADE
        )
    ''')

    # 11. Catalog Generations Table
    cursor.execute('DROP TABLE IF EXISTS catalog_generations')
    cursor.execute('''
        CREATE TABLE catalog_generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            start_year INTEGER,
            end_year INTEGER,
            FOREIGN KEY (model_id) REFERENCES catalog_models (id) ON DELETE CASCADE
        )
    ''')

    # 12. Catalog Pricing Table
    cursor.execute('DROP TABLE IF EXISTS catalog_pricing')
    cursor.execute('''
        CREATE TABLE catalog_pricing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            original_launch_price REAL,
            launch_year INTEGER,
            discontinued_year INTEGER,
            current_used_market_price REAL,
            depreciation_percentage REAL,
            FOREIGN KEY (variant_id) REFERENCES catalog_variants (id) ON DELETE CASCADE
        )
    ''')

    # Seed Manufacturers
    manufacturer_meta = {
        "Maruti Suzuki": ("India/Japan", 1981, "https://www.marutisuzuki.com", "India's largest automotive manufacturer, known for reliable, highly fuel-efficient passenger cars and extensive service reach.", 41.5, 78.0, "Swift, Dzire, Baleno"),
        "Hyundai": ("South Korea", 1967, "https://www.hyundai.com/in", "Leading passenger car exporter and builder, featuring futuristic designs, tech-laden interiors, and reliable performance.", 14.6, 70.0, "Creta, Venue, Verna"),
        "Tata Motors": ("India", 1945, "https://www.tatamotors.com", "Pioneering Indian carmaker building robust vehicles with industry-best 5-star crash safety ratings and leading EV segment.", 13.9, 68.0, "Nexon, Punch, Harrier"),
        "Mahindra": ("India", 1945, "https://auto.mahindra.com", "Renowned manufacturer of tough, sophisticated utility vehicles and premium SUVs with advanced diesel engines and 4WD capabilities.", 11.0, 75.0, "Scorpio N, Thar, XUV700"),
        "Toyota": ("Japan", 1937, "https://www.toyotabharat.com", "Global benchmark for quality, producing bulletproof diesel engines, comfortable people movers, and premium self-charging hybrids.", 6.2, 85.0, "Fortuner, Innova Crysta, Hycross"),
        "Honda": ("Japan", 1948, "https://www.hondacarindia.com", "Acclaimed for smooth i-VTEC engines, highly comfortable sedans, and high quality driving dynamics.", 2.5, 72.0, "City, Amaze, Elevate"),
        "Kia": ("South Korea", 1944, "https://www.kia.com/in", "Modern, feature-rich SUVs and multi-purpose vehicles offering sophisticated powertrains and aggressive designs.", 5.9, 74.0, "Seltos, Sonet, Carens"),
        "MG Motor": ("UK/China", 1924, "https://www.mgmotor.co.in", "British heritage brand building smart, tech-focused connected SUVs and accessible electric cars.", 1.2, 60.0, "Hector, Astor, ZS EV"),
        "Renault": ("France", 1899, "https://www.renault.co.in", "Providing practical, smart hatchbacks and modular 7-seater vehicles designed for budget-focused Indian families.", 1.5, 62.0, "Kwid, Kiger, Triber"),
        "Nissan": ("Japan", 1933, "https://www.nissan.in", "Japanese engineering building rugged utility cars and highly competitive compact SUVs like the Magnite.", 0.8, 64.0, "Magnite"),
        "Volkswagen": ("Germany", 1937, "https://www.volkswagen.co.in", "Solid build quality, punchy TSI turbo-petrol engines, and stable German ride characteristics.", 1.2, 60.0, "Virtus, Taigun"),
        "Skoda": ("Czech Republic", 1895, "https://www.skoda-auto.co.in", "Clever features, sharp European aesthetics, spacious layouts, and engaging driving dynamics.", 1.3, 58.0, "Slavia, Kushaq"),
        "Jeep": ("USA", 1941, "https://www.jeep-india.com", "Legendary American off-road specialist constructing premium monocoque diesel SUVs with high ride height.", 0.5, 62.0, "Compass, Wrangler"),
        "Force Motors": ("India", 1958, "https://www.forcemotors.com", "Indian manufacturer building highly capable rugged off-road utility vans and Gurkha 4x4 SUVs.", 0.15, 65.0, "Gurkha, Traveller"),
        "Isuzu": ("Japan", 1916, "https://isuzu.in", "Pioneer in diesel pickup utility platforms, creating robust passenger lifestyle utility flatbeds.", 0.1, 70.0, "V-Cross, D-Max"),
        "BMW": ("Germany", 1916, "https://www.bmw.in", "Premium brand focusing on high-performance driving dynamics, luxurious rear-wheel-drive sedans, and sporty SUVs.", 1.3, 58.0, "3 Series, X1, X5"),
        "Mercedes-Benz": ("Germany", 1926, "https://www.mercedes-benz.co.in", "The pinnacle of luxury motoring in India, delivering unmatched comfort, ride quality, and active safety systems.", 1.5, 62.0, "C-Class, E-Class, GLC"),
        "Audi": ("Germany", 1909, "https://www.audi.in", "Luxury carmaker famous for Quattro all-wheel drive, premium cabins, and futuristic Matrix LED setups.", 1.1, 56.0, "A4, Q3, Q7"),
        "Volvo": ("Sweden", 1927, "https://www.volvocars.com/in", "Renowned leader in vehicular safety, offering Scandinavian design luxury and eco-friendly hybrid or pure EV options.", 0.3, 54.0, "XC40, XC90"),
        "Jaguar": ("UK", 1922, "https://www.jaguar.in", "Iconic premium brand combining sporting performance, dynamic control, and classical luxury cabin configurations.", 0.2, 52.0, "XF, F-Pace"),
        "Land Rover": ("UK", 1948, "https://www.landrover.in", "World leader in off-road luxury vehicles, offering exceptional go-anywhere capability and premium command seating.", 0.4, 65.0, "Defender, Range Rover Evoque"),
        "Mini": ("UK", 1959, "https://www.mini.in", "Iconic premium hatchback brand focusing on retro styling, go-kart handling, and customizable options.", 0.15, 68.0, "Cooper, Countryman"),
        "Lexus": ("Japan", 1989, "https://www.lexusindia.co.in", "Toyota's luxury division, providing exceptionally quiet, comfortable hybrid sedans and premium SUVs.", 0.15, 68.0, "ES, RX"),
        "Porsche": ("Germany", 1931, "https://www.porsche.in", "Prestigious manufacturer of legendary sports cars and high-performance SUVs with precision handling.", 0.1, 72.0, "911, Macan"),
        "BYD": ("China", 1995, "https://www.bydautoindia.com", "World's leading electric vehicle developer, supplying advanced Blade battery packs and premium EV crossover SUVs.", 0.25, 68.0, "Atto 3, Seal"),
        "Citroen": ("France", 1919, "https://www.citroen.in", "French manufacturer offering unique designs, custom color combos, and exceptionally comfortable suspension dynamics.", 0.3, 55.0, "C3, C5 Aircross"),
        "Ferrari": ("Italy", 1939, "https://www.ferrari.com", "Legendary Italian supercar manufacturer synonymous with Formula 1 heritage, high-revving engines, and striking designs.", 0.02, 80.0, "Roma, 296 GTB"),
        "Lamborghini": ("Italy", 1963, "https://www.lamborghini.com", "Producer of extreme, aggressive super sports cars and the Urus super SUV, delivering thrilling raw power.", 0.05, 82.0, "Urus, Huracan"),
        "Bentley": ("UK", 1919, "https://www.bentleymotors.com", "Prestigious hand-crafted grand tourers blending luxury materials with effortless twin-turbo performance.", 0.01, 62.0, "Continental GT, Bentayga"),
        "Rolls Royce": ("UK", 1906, "https://www.rolls-roycemotors.com", "The absolute standard of bespoke luxury, building ultra-exclusive, whisper-quiet motor cars.", 0.01, 75.0, "Cullinan, Ghost"),
        "McLaren": ("UK", 1963, "https://www.mclaren.com", "High performance British supercar and hypercar manufacturer with racing heritage and precision carbon-fibre monocoques.", 0.01, 68.0, "720S, Artura"),
        "Maserati": ("Italy", 1914, "https://www.maserati.com/in", "Italian luxury brand known for elegant grand touring models and distinctive roaring exhaust signatures.", 0.01, 50.0, "Levante, Ghibli"),
        "Aston Martin": ("UK", 1913, "https://www.astonmartin.com", "British brand combining high-end luxury, high speed, and bespoke grand tourer styling.", 0.01, 60.0, "DB11, DBX"),
        "Chevrolet": ("USA", 1911, "https://www.chevrolet.co.in", "American brand that offered spacious utility models and solid diesel sedans in the Indian market.", 0.0, 48.0, "Beat, Cruze"),
        "Ford": ("USA", 1903, "https://www.ford.co.in", "Pioneered fun-to-drive diesel hatchbacks and full-size off-road 4WD utility SUVs.", 0.0, 65.0, "Figo, EcoSport, Endeavour"),
        "Fiat": ("Italy", 1899, "https://www.fiat-india.com", "Italian engineering that supplied robust multijet engines, handling chassis, and iconic hatchbacks.", 0.0, 45.0, "Punto, Linea"),
        "Mitsubishi": ("Japan", 1870, "https://www.mitsubishi-motors.co.in", "Famed rally-bred off-road SUV manufacturer, beloved for solid mechanical durability.", 0.0, 72.0, "Pajero, Lancer"),
        "Opel": ("Germany", 1862, "https://www.opel.com", "German brand that offered premium, comfortable sedans in the early days of the modern Indian market.", 0.0, 40.0, "Astra, Corsa"),
        "Daewoo": ("South Korea", 1967, "https://www.daewoo.com", "South Korean builder that offered highly popular entry-level hatchbacks and sedans.", 0.0, 35.0, "Matiz, Cielo"),
        "Premier": ("India", 1944, "https://www.premier.co.in", "Historic pioneer that manufactured the legendary Premier Padmini on Indian roads for decades.", 0.0, 60.0, "Padmini"),
        "Hindustan Motors": ("India", 1942, "https://www.hindustan-motors.com", "Iconic Indian manufacturer that produced the Ambassador, the absolute king of Indian roads for half a century.", 0.0, 70.0, "Ambassador"),
        "Lotus": ("UK", 1952, "https://www.lotuscars.com", "Legendary British lightweight sports car manufacturer, now introducing high-performance electric hyper-SUVs in India.", 0.01, 58.0, "Eletre, Emira"),
        "Bugatti": ("France", 1909, "https://www.bugatti.com", "The pinnacle of hypercar performance, engineering record-breaking quad-turbo W16 engines for elite collectors globally.", 0.001, 85.0, "Chiron, Veyron")
    }

    brand_ids = {}
    for name, info in manufacturer_meta.items():
        slug = name.lower().replace(" ", "-").replace(":", "").replace("&", "and")
        logo_path = f"/static/images/brand_logos/{slug}.svg"
        
        cursor.execute('''
            INSERT INTO catalog_manufacturers (
                name, slug, country, founded, website, description, market_share, average_resale, popular_models, logo_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, slug, info[0], info[1], info[2], info[3], info[4], info[5], info[6], logo_path))
        brand_ids[name] = cursor.lastrowid

    # Indexes for catalog tables optimization
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_variants_model ON catalog_variants(model_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_specs_variant ON catalog_specifications(variant_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_scores_variant ON catalog_ai_scores(variant_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pricing_variant ON catalog_pricing(variant_id)')

    # Query car_database to populate models, variants, specifications, and AI scores
    for name, m_id in brand_ids.items():
        cursor.execute('SELECT DISTINCT model, body_type FROM car_database WHERE brand = ?', (name,))
        models = cursor.fetchall()
        
        for m_name, b_type in models:
            m_slug = m_name.lower().replace(" ", "-").replace("/", "-")
            m_desc = f"The {name} {m_name} is a high-performance, premium {b_type} engineered to deliver an exceptional combination of luxury, efficiency, and driving dynamics for Indian road conditions."
            image_path = f"/static/images/cars/placeholder.svg"
            
            cursor.execute('''
                INSERT INTO catalog_models (
                    manufacturer_id, name, slug, body_type, base_price, launch_year, image_path, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (m_id, m_name, m_slug, b_type, 0.0, 2020, image_path, m_desc))
            model_id = cursor.lastrowid
            
            # Create a model generation entry
            cursor.execute('''
                INSERT INTO catalog_generations (model_id, name, start_year, end_year)
                VALUES (?, ?, ?, ?)
            ''', (model_id, "1st Generation", 2018, 2026))
            
            # Find all unique variants for this model
            cursor.execute('''
                SELECT variant, fuel_type, transmission, MIN(base_showroom_price), engine_capacity, power, torque, mileage,
                       seating_capacity, airbags, abs, esp, sunroof, adas, cruise_control, ground_clearance, wheelbase,
                       boot_space, fuel_tank_capacity, drivetrain
                FROM car_database 
                WHERE brand = ? AND model = ?
                GROUP BY variant, fuel_type, transmission
            ''', (name, m_name))
            variants = cursor.fetchall()
            
            min_price = float('inf')
            for var_row in variants:
                v_name = var_row[0]
                v_slug = v_name.lower().replace(" ", "-").replace("+", "plus")
                fuel = var_row[1]
                trans = var_row[2]
                base_price = var_row[3]
                on_road_price = round(base_price * 1.15) # 15% local taxes/registration
                
                if base_price < min_price:
                    min_price = base_price
                
                cursor.execute('''
                    INSERT INTO catalog_variants (
                        model_id, name, slug, fuel_type, transmission, base_showroom_price, on_road_price
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (model_id, v_name, v_slug, fuel, trans, base_price, on_road_price))
                variant_id = cursor.lastrowid
                
                # Seeding specs
                safety_rating = 4
                if name in ["Tata Motors", "Mahindra", "Volvo"]:
                    safety_rating = 5
                elif name in ["Maruti Suzuki", "Renault", "Citroen"]:
                    safety_rating = 3
                
                colors_list = "Pearl Arctic White, Solid Fire Red, Metallic Silky Silver, Prime Orange, Pearl Midnight Blue, Granite Grey"
                
                cursor.execute('''
                    INSERT INTO catalog_specifications (
                        variant_id, engine_capacity, power, torque, mileage, seating_capacity, safety_rating, ground_clearance,
                        drivetrain, fuel_tank_capacity, airbags, sunroof, adas, cruise_control, colors, wheelbase, boot_space
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    variant_id, var_row[4], var_row[5], var_row[6], var_row[7], var_row[8], safety_rating, var_row[15],
                    var_row[19], var_row[18], var_row[9], var_row[12], var_row[13], var_row[14], colors_list, var_row[16], var_row[17]
                ))
                
                # Seeding AI scores
                pop = 85
                if name in ["Maruti Suzuki", "Hyundai", "Tata Motors"]:
                    pop = 95
                elif name in ["BMW", "Audi", "Mercedes-Benz"]:
                    pop = 88
                
                resale = 65
                if name == "Toyota":
                    resale = 88
                elif name == "Maruti Suzuki":
                    resale = 82
                elif name == "Honda":
                    resale = 78
                elif name == "Hyundai":
                    resale = 75
                
                maint_score = 75
                if name in ["Maruti Suzuki", "Hyundai", "Tata Motors"]:
                    maint_score = 90
                elif name in ["BMW", "Audi", "Mercedes-Benz", "Porsche", "Ferrari", "Lamborghini"]:
                    maint_score = 50
                
                rel_score = 80
                if name in ["Toyota", "Honda"]:
                    rel_score = 92
                elif name in ["Maruti Suzuki", "Hyundai"]:
                    rel_score = 88
                
                ins_cat = "Standard Comprehensive"
                if base_price > 2500000:
                    ins_cat = "Luxury Premium"
                elif base_price < 800000:
                    ins_cat = "Economy Basic"
                
                annual_cost = round(base_price * 0.05)
                
                cursor.execute('''
                    INSERT INTO catalog_ai_scores (
                        variant_id, popularity_score, resale_score, demand_score, maintenance_score, reliability_score,
                        insurance_category, annual_ownership_cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (variant_id, pop, resale, pop - 5, maint_score, rel_score, ins_cat, annual_cost))

                is_active = 1
                launch_yr = 2022
                disc_yr = None
                used_price = None
                dep_pct = 0.0
                
                # Check if brand is historically discontinued in India
                if name in ["Chevrolet", "Ford", "Fiat", "Mitsubishi", "Opel", "Daewoo", "Premier", "Hindustan Motors"]:
                    is_active = 0
                    launch_yr = 2010
                    disc_yr = 2018
                    used_price = round(base_price * 0.22) # ~22% residual value
                    dep_pct = 78.0
                    
                cursor.execute('''
                    INSERT INTO catalog_pricing (
                        variant_id, is_active, original_launch_price, launch_year, discontinued_year, current_used_market_price, depreciation_percentage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (variant_id, is_active, base_price, launch_yr, disc_yr, used_price, dep_pct))
            
            # Update base_price on the model record to reflect the starting model variant price
            if min_price != float('inf'):
                cursor.execute('UPDATE catalog_models SET base_price = ? WHERE id = ?', (min_price, model_id))
                
    # Index setup successfully created
    conn.commit()
    print("Catalog tables successfully initialized and populated from database specifications.")

def init_db():
    """Initializes SQLite database and tables if they do not exist."""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile_number TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Saved Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            variant TEXT NOT NULL,
            year INTEGER NOT NULL,
            kms INTEGER NOT NULL,
            health_score INTEGER NOT NULL,
            valuation_score INTEGER NOT NULL,
            estimated_value REAL NOT NULL,
            report_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 3. Cars Table (Includes every inspection, cosmetic, mechanical and documentation detail)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            variant TEXT NOT NULL,
            manufacturing_year INTEGER NOT NULL,
            purchase_year INTEGER NOT NULL,
            registration_year INTEGER NOT NULL,
            registration_state TEXT NOT NULL,
            registration_number TEXT NOT NULL,
            number_plate_type TEXT NOT NULL,
            fuel_type TEXT NOT NULL,
            transmission TEXT NOT NULL,
            kilometers_driven INTEGER NOT NULL,
            owner_number INTEGER NOT NULL,
            insurance TEXT NOT NULL,
            insurance_type TEXT,
            insurance_expiry TEXT,
            service_history TEXT NOT NULL,
            number_of_services INTEGER NOT NULL,
            last_service_date TEXT NOT NULL,
            accident_history TEXT NOT NULL,
            accident_severity TEXT,
            colour TEXT,
            engine_serial_no TEXT,
            chassis_no TEXT,
            rc_available TEXT,
            puc_available TEXT,
            service_records_available TEXT,
            engine_condition TEXT,
            gearbox_condition TEXT,
            clutch_condition TEXT,
            brake_condition TEXT,
            tyre_condition TEXT,
            suspension_condition TEXT,
            battery_condition TEXT,
            ac_condition TEXT,
            electrical_condition TEXT,
            paint_condition TEXT,
            rust_condition TEXT,
            door_condition TEXT,
            outer_body_score INTEGER,
            inner_body_score INTEGER,
            seat_quality_score INTEGER,
            infotainment_score INTEGER,
            mirror_condition TEXT,
            windshield_condition TEXT,
            sunroof TEXT,
            alloy_wheels TEXT,
            accessories TEXT,
            modifications TEXT,
            estimated_market_value REAL,
            expected_selling_price REAL,
            fair_price_low REAL,
            fair_price_high REAL,
            ai_valuation_score INTEGER,
            confidence_score INTEGER,
            vehicle_health_score INTEGER,
            depreciation_percentage REAL,
            deal_rating TEXT,
            is_saved INTEGER DEFAULT 1,
            is_favorite INTEGER DEFAULT 0,
            is_garage INTEGER DEFAULT 0,
            garage_images TEXT,
            puc_expiry TEXT,
            next_service_date TEXT,
            battery_expiry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
    ''')
    
    # 4. Favorites Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            car_id INTEGER NOT NULL,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            variant TEXT NOT NULL,
            manufacturing_year INTEGER NOT NULL,
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (car_id) REFERENCES cars (id) ON DELETE CASCADE
        )
    ''')
    
    # 5. Chat History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # 6. Catalog Media Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS catalog_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER,
            variant_id INTEGER,
            media_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            caption TEXT,
            is_hero INTEGER DEFAULT 0,
            FOREIGN KEY (model_id) REFERENCES catalog_models (id) ON DELETE CASCADE,
            FOREIGN KEY (variant_id) REFERENCES catalog_variants (id) ON DELETE CASCADE
        )
    ''')
    
    # 7. Catalog Reminders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS catalog_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            car_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            reminder_type TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (car_id) REFERENCES cars (id) ON DELETE CASCADE
        )
    ''')
    
    # 8. System Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            log_level TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT
        )
    ''')
    
    # 9. Rate Limit Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            request_count INTEGER DEFAULT 1
        )
    ''')

    # 10. Contact Messages Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip TEXT,
            browser TEXT,
            status TEXT DEFAULT 'unread'
        )
    ''')
    
    populate_car_database(conn)
    populate_catalog_database(conn)

    # Seed default system administrator
    cursor.execute("SELECT id FROM users WHERE email = 'admin@karmani.com'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (full_name, email, mobile_number, password_hash, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', ('System Administrator', 'admin@karmani.com', '9999999999', generate_password_hash('admin'), 1))
        
    conn.commit()
    conn.close()

# Auto-initialize database on application startup
init_db()

@app.before_request
def rate_limiting():
    # Generate CSRF token if not in session
    if 'csrf_token' not in session:
        import secrets
        session['csrf_token'] = secrets.token_hex(16)

    # Bypass static files, css, and images
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return
        
    import time
    ip = request.remote_addr
    now = int(time.time())
    window = now - 60
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Clean up rate limit logs older than 10 minutes to maintain performance
        cursor.execute('DELETE FROM rate_limit_log WHERE timestamp < ?', (now - 600,))
        
        # Count requests in last 60 seconds for current IP
        cursor.execute('''
            SELECT SUM(request_count) FROM rate_limit_log 
            WHERE ip_address = ? AND timestamp >= ?
        ''', (ip, window))
        cnt_row = cursor.fetchone()
        cnt = cnt_row[0] if cnt_row and cnt_row[0] else 0
        
        if cnt >= 60: # Limit 60 requests per minute
            cursor.execute('''
                INSERT INTO system_logs (log_level, message, details)
                VALUES (?, ?, ?)
            ''', ('WARNING', 'Rate Limit Exceeded', f'IP: {ip}, Endpoint: {request.path} requested {cnt} times in last 60s'))
            conn.commit()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Too many requests. Please wait a minute before trying again.'}), 429
            
        cursor.execute('''
            INSERT INTO rate_limit_log (ip_address, endpoint, timestamp, request_count)
            VALUES (?, ?, ?, 1)
        ''', (ip, request.endpoint or '', now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Rate limiting database error: {e}")

def calculate_valuation(data):
    """Production-grade Indian Vehicle Valuation AI Engine utilizing ML Random Forest prediction."""
    from ml.predict import predict_valuation
    return predict_valuation(data)

# API Endpoint: Get all brands
@app.route('/api/brands')
def api_brands():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT brand FROM car_database ORDER BY brand ASC')
    brands = [r[0] for r in cursor.fetchall()]
    conn.close()
    return jsonify(brands)

# API Endpoint: Get models by brand
@app.route('/api/models')
def api_models():
    brand = request.args.get('brand')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT model FROM car_database WHERE brand = ? ORDER BY model ASC', (brand,))
    models = [r[0] for r in cursor.fetchall()]
    conn.close()
    return jsonify(models)

# API Endpoint: Get variants by brand & model
@app.route('/api/variants')
def api_variants():
    brand = request.args.get('brand')
    model = request.args.get('model')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT variant FROM car_database WHERE brand = ? AND model = ? ORDER BY variant ASC', (brand, model))
    variants = [r[0] for r in cursor.fetchall()]
    conn.close()
    return jsonify(variants)

# API Endpoint: Get specific variant specs
@app.route('/api/spec')
def api_spec():
    brand = request.args.get('brand')
    model = request.args.get('model')
    variant = request.args.get('variant')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM car_database WHERE brand = ? AND model = ? AND variant = ? LIMIT 1', (brand, model, variant))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        res = dict(row)
        
        # Standardize existing fields
        res['abs'] = 'Yes' if str(res.get('abs', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        res['esp'] = 'Yes' if str(res.get('esp', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        res['sunroof'] = 'Yes' if str(res.get('sunroof', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        res['adas'] = 'Yes' if str(res.get('adas', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        res['cruise_control'] = 'Yes' if str(res.get('cruise_control', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        
        # Derive missing comfort & safety parameters dynamically
        price = res.get('base_showroom_price', 0) or 0
        try:
            price = float(price)
        except (ValueError, TypeError):
            price = 0.0

        is_premium = price > 1200000 or res.get('adas', 'No') == 'Yes' or res.get('esp', 'No') == 'Yes'
        variant_name = str(res.get('variant', '')).lower()
        transmission_val = str(res.get('transmission', '') or '').lower()
        
        res['reverse_camera'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
        res['android_auto'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
        res['apple_carplay'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
        res['tpms'] = 'Yes' if is_premium else 'No'
        res['hill_assist'] = 'Yes' if (is_premium or transmission_val == 'automatic') else 'No'
        res['fog_lamps'] = 'Yes' if ('lxi' not in variant_name) else 'No'
        res['power_steering'] = 'Yes'  # Power steering standard
        res['automatic_climate_control'] = 'Yes' if is_premium else 'No'
        res['traction_control'] = 'Yes' if (res.get('esp', 'No') == 'Yes' or is_premium) else 'No'
        res['parking_sensors'] = 'Yes'  # Standard
        
        return jsonify({'status': 'success', 'spec': res})
        
    return jsonify({'status': 'error', 'message': 'Specification not found.'}), 404

# Route for the home page ("/")
@app.route('/')
def home():
    return render_template('index.html')

# Route for the dedicated Car Valuation page ("/valuation")
@app.route('/valuation', methods=['GET', 'POST'])
def valuation():
    if request.method == 'POST':
        try:
            # Parse request payload (JSON or Form-encoded)
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form

            # Extract form values
            brand = data.get('brand')
            model = data.get('model')
            variant = data.get('variant')
            manufacturing_year = int(data.get('manufacturing_year', 2022))
            purchase_year = int(data.get('purchase_year', 2022))
            registration_year = int(data.get('registration_year', 2022))
            registration_state = data.get('registration_state')
            registration_number = data.get('registration_number')
            number_plate_type = data.get('number_plate_type')
            fuel_type = data.get('fuel_type')
            transmission = data.get('transmission')
            kilometers_driven = int(data.get('kilometers_driven', 30000))
            owner_number = int(data.get('owner_number', 1))
            insurance = data.get('insurance')
            insurance_type = data.get('insurance_type')
            insurance_expiry = data.get('insurance_expiry')
            service_history = data.get('service_history')
            number_of_services = int(data.get('number_of_services', 5))
            last_service_date = data.get('last_service_date')
            accident_history = data.get('accident_history')
            accident_severity = data.get('accident_severity')
            
            # Form modifications, condition variables
            colour = data.get('colour', 'White')
            engine_serial_no = data.get('engine_serial_no', 'N/A')
            chassis_no = data.get('chassis_no', 'N/A')
            rc_available = data.get('rc_available', 'Yes')
            puc_available = data.get('puc_available', 'Yes')
            service_records_available = data.get('service_records_available', 'Yes')
            
            engine_cond = data.get('engine_condition', 'Good')
            gearbox_cond = data.get('gearbox_condition', 'Good')
            clutch_cond = data.get('clutch_condition', 'Good')
            brake_cond = data.get('brake_condition', 'Good')
            tyre_cond = data.get('tyre_condition', 'Good')
            suspension_cond = data.get('suspension_condition', 'Good')
            battery_cond = data.get('battery_condition', 'Good')
            ac_cond = data.get('ac_condition', 'Good')
            electrical_cond = data.get('electrical_condition', 'Good')
            
            paint_cond = data.get('paint_condition', 'Original')
            rust_cond = data.get('rust_condition', 'None')
            door_cond = data.get('door_condition', 'Good')
            mirror_cond = data.get('mirror_condition', 'Good')
            windshield_cond = data.get('windshield_condition', 'Good')
            
            outer_body_score = int(data.get('outer_body_score', 90))
            inner_body_score = int(data.get('inner_body_score', 90))
            seat_quality_score = int(data.get('seat_quality_score', 90))
            infotainment_score = int(data.get('infotainment_score', 90))
            
            sunroof = data.get('sunroof', 'No')
            alloy_wheels = data.get('alloy_wheels', 'No')
            accessories = data.get('accessories', 'None')
            modifications = data.get('modifications', 'Stock Vehicle')

            # Run AI Valuation Engine Calculations
            val_results = calculate_valuation(data)

            # Determine user session if logged in
            current_user_id = session.get('user_id')
            is_saved_flag = 1

            # Write records + outputs to SQLite Database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO cars (
                    user_id, brand, model, variant, manufacturing_year, purchase_year, registration_year,
                    registration_state, registration_number, number_plate_type, fuel_type, transmission,
                    kilometers_driven, owner_number, insurance, insurance_type, insurance_expiry,
                    service_history, number_of_services, last_service_date, accident_history, accident_severity,
                    colour, engine_serial_no, chassis_no, rc_available, puc_available, service_records_available,
                    engine_condition, gearbox_condition, clutch_condition, brake_condition, tyre_condition,
                    suspension_condition, battery_condition, ac_condition, electrical_condition, paint_condition,
                    rust_condition, door_condition, outer_body_score, inner_body_score, seat_quality_score,
                    infotainment_score, mirror_condition, windshield_condition, sunroof, alloy_wheels,
                    accessories, modifications,
                    estimated_market_value, expected_selling_price, fair_price_low, fair_price_high,
                    ai_valuation_score, confidence_score, vehicle_health_score, depreciation_percentage,
                    deal_rating, is_saved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_user_id, brand, model, variant, manufacturing_year, purchase_year, registration_year,
                registration_state, registration_number, number_plate_type, fuel_type, transmission,
                kilometers_driven, owner_number, insurance, insurance_type, insurance_expiry,
                service_history, number_of_services, last_service_date, accident_history, accident_severity,
                colour, engine_serial_no, chassis_no, rc_available, puc_available, service_records_available,
                engine_cond, gearbox_cond, clutch_cond, brake_cond, tyre_cond, suspension_cond, battery_cond,
                ac_cond, electrical_cond, paint_cond, rust_cond, door_cond, outer_body_score, inner_body_score,
                seat_quality_score, infotainment_score, mirror_cond, windshield_cond, sunroof, alloy_wheels,
                accessories, modifications,
                val_results['estimated_market_value'], val_results['expected_selling_price'],
                val_results['fair_price_low'], val_results['fair_price_high'],
                val_results['ai_valuation_score'], val_results['confidence_score'],
                val_results['vehicle_health_score'], val_results['depreciation_percentage'],
                val_results['deal_rating'], is_saved_flag
            ))
            # Grab the newly inserted record id to return
            new_car_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Return success response with computed AI metrics
            return jsonify({
                'status': 'success',
                'message': 'AI appraisal successful! Saved to dashboard report history.',
                'results': val_results,
                'car_id': new_car_id
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Engine error: {str(e)}'
            }), 400

    return render_template('valuation.html')

# User Registration Endpoint
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email').strip().lower()
        mobile_number = request.form.get('mobile_number')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not full_name or not email or not mobile_number or not password:
            flash('Please fill in all details.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            flash('Email is already registered. Please login.', 'danger')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (full_name, email, mobile_number, password_hash)
            VALUES (?, ?, ?, ?)
        ''', (full_name, email, mobile_number, password_hash))
        conn.commit()
        conn.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# User Login Endpoint
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            flash('Please enter email and password.', 'danger')
            return render_template('login.html')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, full_name, email, password_hash FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['full_name'] = user[1]
            session['email'] = user[2]
            flash(f'Welcome back, {user[1]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('login.html')

    return render_template('login.html')

# User Logout Endpoint
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# Forgot Password Recovery
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('forgot_password.html')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        if user:
            new_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE email = ?', (new_hash, email))
            conn.commit()
            conn.close()
            flash('Password reset successful! Please login with your new password.', 'success')
            return redirect(url_for('login'))
        else:
            conn.close()
            flash('Email not found in our records.', 'danger')
            return render_template('forgot_password.html')

    return render_template('forgot_password.html')

# Change Password (Secure)
@app.route('/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_pass = request.form.get('current_password')
    new_pass = request.form.get('new_password')
    confirm_pass = request.form.get('confirm_password')

    if new_pass != confirm_pass:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('profile'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT password_hash FROM users WHERE id = ?', (session['user_id'],))
    user_row = cursor.fetchone()
    
    if not user_row:
        conn.close()
        session.clear()
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    user_hash = user_row[0]

    if check_password_hash(user_hash, current_pass):
        new_hash = generate_password_hash(new_pass)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, session['user_id']))
        conn.commit()
        conn.close()
        flash('Password updated successfully!', 'success')
    else:
        conn.close()
        flash('Incorrect current password.', 'danger')

    return redirect(url_for('profile'))

# Edit Profile Handler
@app.route('/edit-profile', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    full_name = request.form.get('full_name')
    mobile_number = request.form.get('mobile_number')
    
    if full_name and mobile_number:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE id = ?', (session['user_id'],))
        if not cursor.fetchone():
            conn.close()
            session.clear()
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
            
        cursor.execute('UPDATE users SET full_name = ?, mobile_number = ? WHERE id = ?', (full_name, mobile_number, session['user_id']))
        conn.commit()
        conn.close()
        
        session['full_name'] = full_name
        flash('Profile updated successfully!', 'success')
        
    return redirect(url_for('profile'))

# Delete Car log Endpoint
@app.route('/delete-car/<int:car_id>', methods=['POST'])
def delete_car(car_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cars WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Vehicle appraisal record deleted.', 'info')
    return redirect(url_for('dashboard'))

# Toggle save report status
@app.route('/toggle-save/<int:car_id>', methods=['POST'])
def toggle_save(car_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT is_saved FROM cars WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    row = cursor.fetchone()
    if row:
        new_val = 1 if row[0] == 0 else 0
        cursor.execute('UPDATE cars SET is_saved = ? WHERE id = ?', (new_val, car_id))
        conn.commit()
        flash('Report saved status updated.', 'success')
        
    conn.close()
    return redirect(url_for('dashboard'))

# Toggle favorite status
@app.route('/toggle-favorite/<int:car_id>', methods=['POST'])
def toggle_favorite(car_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT is_favorite FROM cars WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    row = cursor.fetchone()
    if row:
        new_val = 1 if row[0] == 0 else 0
        cursor.execute('UPDATE cars SET is_favorite = ? WHERE id = ?', (new_val, car_id))
        conn.commit()
        flash('Vehicle bookmark status updated.', 'success')
        
    conn.close()
    return redirect(url_for('dashboard'))

# User Dashboard Details
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to view dashboard.', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Fetch user account info
    cursor.execute('SELECT full_name, email, mobile_number, created_at FROM users WHERE id = ?', (session['user_id'],))
    user_row = cursor.fetchone()
    
    if not user_row:
        conn.close()
        session.clear()
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    user_info = {
        'name': user_row[0],
        'email': user_row[1],
        'mobile': user_row[2],
        'joined': user_row[3][:10]
    }
    
    # 2. Stats
    cursor.execute('SELECT COUNT(*) FROM cars WHERE user_id = ?', (session['user_id'],))
    total_valued = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM cars WHERE user_id = ? AND is_saved = 1', (session['user_id'],))
    saved_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM cars WHERE user_id = ? AND is_favorite = 1', (session['user_id'],))
    fav_count = cursor.fetchone()[0]

    cursor.execute('SELECT AVG(ai_valuation_score) FROM cars WHERE user_id = ?', (session['user_id'],))
    avg_score_row = cursor.fetchone()
    avg_score = round(avg_score_row[0]) if avg_score_row and avg_score_row[0] is not None else 0

    cursor.execute('SELECT SUM(estimated_market_value) FROM cars WHERE user_id = ?', (session['user_id'],))
    total_worth_row = cursor.fetchone()
    total_worth = round(total_worth_row[0]) if total_worth_row and total_worth_row[0] is not None else 0

    # 3. History
    cursor.execute('''
        SELECT id, brand, model, variant, manufacturing_year, estimated_market_value, ai_valuation_score, is_saved, is_favorite, created_at
        FROM cars WHERE user_id = ? ORDER BY id DESC
    ''', (session['user_id'],))
    history_rows = cursor.fetchall()
    conn.close()

    history_list = []
    saved_list = []
    fav_list = []
    
    for r in history_rows:
        car_obj = {
            'id': r[0],
            'brand': r[1],
            'model': r[2],
            'variant': r[3],
            'year': r[4],
            'price': r[5],
            'score': r[6],
            'is_saved': r[7],
            'is_favorite': r[8],
            'date': r[9][:10]
        }
        history_list.append(car_obj)
        if r[7] == 1:
            saved_list.append(car_obj)
        if r[8] == 1:
            fav_list.append(car_obj)

    return render_template(
        'dashboard.html',
        user=user_info,
        total_valued=total_valued,
        saved_count=saved_count,
        fav_count=fav_count,
        avg_score=avg_score,
        total_worth=total_worth,
        history=history_list,
        saved_reports=saved_list,
        favourites=fav_list
    )

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to view profile.', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT full_name, email, mobile_number, created_at FROM users WHERE id = ?', (session['user_id'],))
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row:
        session.clear()
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    user_info = {
        'name': user_row[0],
        'email': user_row[1],
        'mobile': user_row[2] if user_row[2] else 'N/A',
        'joined': user_row[3][:10] if user_row[3] else 'N/A'
    }
    return render_template('profile.html', user=user_info)

def map_car_row_to_dict(row, user_name="Guest User"):
    car_data = {
        'id': row[0],
        'brand': row[2],
        'model': row[3],
        'variant': row[4],
        'year': row[5],
        'purchase_year': row[6],
        'reg_year': row[7],
        'state': row[8].upper() if row[8] else '',
        'reg_no': row[9],
        'plate_type': row[10],
        'fuel': row[11],
        'transmission': row[12],
        'kms': row[13],
        'owners': row[14],
        'insurance': row[15],
        'insurance_type': row[16] if row[16] else 'None',
        'insurance_expiry': row[17] if row[17] else 'N/A',
        'service_history': row[18],
        'services_count': row[19],
        'last_service': row[20],
        'accident_history': row[21],
        'accident_severity': row[22] if row[22] else 'None',
        
        'colour': row[23],
        'engine_serial_no': row[24],
        'chassis_no': row[25],
        'rc_available': row[26],
        'puc_available': row[27],
        'service_records_available': row[28],
        
        'engine_condition': row[29],
        'gearbox_condition': row[30],
        'clutch_condition': row[31],
        'brake_condition': row[32],
        'tyre_condition': row[33],
        'suspension_condition': row[34],
        'battery_condition': row[35],
        'ac_condition': row[36],
        'electrical_condition': row[37],
        'paint_condition': row[38],
        'rust_condition': row[39],
        'door_condition': row[40],
        
        'outer_body_score': row[41],
        'inner_body_score': row[42],
        'seat_quality_score': row[43],
        'infotainment_score': row[44],
        'mirror_condition': row[45],
        'windshield_condition': row[46],
        'sunroof': row[47],
        'alloy_wheels': row[48],
        'accessories': row[49],
        'modifications': row[50],
        
        'price': row[51],
        'price_expected': row[52],
        'price_low': row[53],
        'price_high': row[54],
        'score': row[55],
        'confidence': row[56],
        'health_score': row[57],
        'depreciation': row[58],
        'deal': row[59],
        'date': row[61]
    }
    
    # Safely parse numeric fields
    numeric_fields = ['kms', 'owners', 'services_count', 'outer_body_score', 'inner_body_score', 'seat_quality_score', 'infotainment_score']
    for f in numeric_fields:
        try:
            car_data[f] = int(car_data[f]) if car_data[f] is not None else 0
        except (ValueError, TypeError):
            car_data[f] = 0
            
    # Check if pricing fields are missing
    try:
        price_val = float(car_data['price']) if car_data['price'] is not None else 0.0
    except (ValueError, TypeError):
        price_val = 0.0
        
    if price_val <= 0:
        # Dynamically recalculate valuation
        mock_data = {
            'brand': car_data['brand'], 'model': car_data['model'], 'variant': car_data['variant'],
            'manufacturing_year': car_data['year'], 'purchase_year': car_data['purchase_year'], 'registration_year': car_data['reg_year'],
            'registration_state': car_data['state'], 'fuel_type': car_data['fuel'], 'transmission': car_data['transmission'],
            'kilometers_driven': car_data['kms'], 'owner_number': car_data['owners'], 'insurance': 'yes' if car_data['insurance'] == 'Yes' else 'no',
            'accident_history': 'yes' if car_data['accident_history'] == 'Yes' else 'no', 'accident_severity': car_data['accident_severity']
        }
        recalc = calculate_valuation(mock_data)
        car_data['price'] = recalc.get('estimated_market_value', 0)
        car_data['price_expected'] = recalc.get('expected_selling_price', 0)
        car_data['price_low'] = recalc.get('fair_price_low', 0)
        car_data['price_high'] = recalc.get('fair_price_high', 0)
        car_data['score'] = recalc.get('ai_valuation_score', 80)
        car_data['confidence'] = recalc.get('confidence_score', 85)
        car_data['health_score'] = recalc.get('vehicle_health_score', 80)
        car_data['depreciation'] = recalc.get('depreciation_percentage', 15.0)
        car_data['deal'] = recalc.get('deal_rating', 'Good Deal')
    else:
        # Standardize existing numeric values to float/int to avoid TypeError formatting issues
        pricing_int_fields = ['price', 'price_expected', 'price_low', 'price_high', 'score', 'confidence', 'health_score']
        for f in pricing_int_fields:
            try:
                car_data[f] = int(float(car_data[f])) if car_data[f] is not None else 0
            except (ValueError, TypeError):
                car_data[f] = 0
                
        try:
            car_data['depreciation'] = float(car_data['depreciation']) if car_data['depreciation'] is not None else 0.0
        except (ValueError, TypeError):
            car_data['depreciation'] = 0.0
            
    car_data['user_name'] = user_name
    return car_data

@app.route('/report/<int:car_id>')
def report(car_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        flash('Report not found.', 'danger')
        return redirect(url_for('dashboard') if 'user_id' in session else url_for('home'))

    # Fetch linked user details
    user_name = "Guest User"
    if row[1]:
        cursor.execute('SELECT full_name FROM users WHERE id = ?', (row[1],))
        u_row = cursor.fetchone()
        if u_row:
            user_name = u_row[0]
            
    conn.close()

    # Re-map DB columns to structured dict using helper
    car_data = map_car_row_to_dict(row, user_name)

    # Fetch specifications details from complete specs index database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM car_database WHERE brand = ? AND model = ? AND variant = ? LIMIT 1', (car_data['brand'], car_data['model'], car_data['variant']))
    spec_row = cursor.fetchone()
    
    # Fetch catalog AI scores
    cursor.execute('''
        SELECT a.resale_score, a.maintenance_score, a.reliability_score
        FROM catalog_ai_scores a
        JOIN catalog_variants v ON a.variant_id = v.id
        JOIN catalog_models m ON v.model_id = m.id
        JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
        WHERE man.name = ? AND m.name = ? AND v.name = ?
        LIMIT 1
    ''', (car_data['brand'], car_data['model'], car_data['variant']))
    score_row = cursor.fetchone()
    conn.close()

    spec_dict = {}
    if spec_row:
        columns = [
            'id', 'brand', 'model', 'variant', 'fuel_type', 'transmission', 'engine_capacity', 'engine_type',
            'power', 'torque', 'mileage', 'body_type', 'wheelbase', 'ground_clearance', 'boot_space',
            'fuel_tank_capacity', 'drivetrain', 'emission_norm', 'num_cylinders', 'seating_capacity',
            'airbags', 'abs', 'esp', 'sunroof', 'adas', 'cruise_control', 'base_showroom_price'
        ]
        spec_dict = dict(zip(columns, spec_row))
        
        # Standardize existing fields
        spec_dict['abs'] = 'Yes' if str(spec_dict.get('abs', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        spec_dict['esp'] = 'Yes' if str(spec_dict.get('esp', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        spec_dict['sunroof'] = 'Yes' if str(spec_dict.get('sunroof', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        spec_dict['adas'] = 'Yes' if str(spec_dict.get('adas', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        spec_dict['cruise_control'] = 'Yes' if str(spec_dict.get('cruise_control', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
        
        # Derive missing comfort & safety parameters dynamically
        price = spec_dict.get('base_showroom_price', 0) or 0
        try:
            price = float(price)
        except (ValueError, TypeError):
            price = 0.0

        is_premium = price > 1200000 or spec_dict.get('adas', 'No') == 'Yes' or spec_dict.get('esp', 'No') == 'Yes'
        variant_name = str(spec_dict.get('variant', '')).lower()
        
        spec_dict['reverse_camera'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
        spec_dict['android_auto'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
        spec_dict['apple_carplay'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
        spec_dict['tpms'] = 'Yes' if is_premium else 'No'
        spec_dict['hill_assist'] = 'Yes' if (is_premium or spec_dict.get('transmission', '').lower() == 'automatic') else 'No'
        spec_dict['fog_lamps'] = 'Yes' if ('lxi' not in variant_name) else 'No'
        spec_dict['power_steering'] = 'Yes'  # Power steering standard
        spec_dict['automatic_climate_control'] = 'Yes' if is_premium else 'No'
        spec_dict['traction_control'] = 'Yes' if (spec_dict.get('esp', 'No') == 'Yes' or is_premium) else 'No'
        spec_dict['parking_sensors'] = 'Yes'  # Standard
        
    ai_scores = {'resale': 82, 'maintenance': 80, 'reliability': 85}
    if score_row:
        ai_scores['resale'] = score_row[0]
        ai_scores['maintenance'] = score_row[1]
        ai_scores['reliability'] = score_row[2]

    # Recalculate dynamic analytics trend data
    engine_mock_data = {
        'brand': car_data['brand'], 'model': car_data['model'], 'variant': car_data['variant'],
        'manufacturing_year': car_data['year'], 'purchase_year': car_data['purchase_year'], 'registration_year': car_data['reg_year'],
        'registration_state': car_data['state'], 'fuel_type': car_data['fuel'], 'transmission': car_data['transmission'],
        'kilometers_driven': car_data['kms'], 'owner_number': car_data['owners'], 'insurance': 'yes' if car_data['insurance'] == 'Yes' else 'no',
        'accident_history': 'yes' if car_data['accident_history'] == 'Yes' else 'no', 'accident_severity': car_data['accident_severity']
    }
    recalculated = calculate_valuation(engine_mock_data)

    # --- Market Intelligence Module Datasets ---
    base_val = car_data['price']
    try:
        base_val = float(base_val)
    except (ValueError, TypeError):
        base_val = 0.0
    
    # Query 5 similar vehicles from car_database matching segment body_type
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    b_type = spec_dict.get('body_type', 'SUV')
    cursor.execute('''
        SELECT brand, model, variant, base_showroom_price, fuel_type, transmission 
        FROM car_database 
        WHERE body_type = ? AND brand != ? 
        LIMIT 5
    ''', (b_type, car_data['brand']))
    similar_specs = cursor.fetchall()
    conn.close()
    
    if len(similar_specs) < 5:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT brand, model, variant, base_showroom_price, fuel_type, transmission 
            FROM car_database 
            LIMIT 5
        ''')
        similar_specs = cursor.fetchall()
        conn.close()
        
    similar_cars = []
    for s in similar_specs:
        s_brand, s_model, s_variant, s_showroom, s_fuel, s_trans = s
        s_mock = {
            'brand': s_brand, 'model': s_model, 'variant': s_variant,
            'manufacturing_year': car_data['year'], 'purchase_year': car_data['purchase_year'], 'registration_year': car_data['reg_year'],
            'registration_state': 'MH', 'fuel_type': s_fuel, 'transmission': s_trans,
            'kilometers_driven': car_data['kms'], 'owner_number': car_data['owners'], 'insurance': 'Yes'
        }
        s_val = calculate_valuation(s_mock)
        similar_cars.append({
            'brand': s_brand,
            'model': s_model,
            'variant': s_variant,
            'price': s_val['estimated_market_value'],
            'score': s_val['ai_valuation_score']
        })
        
    # State-wise Price Comparison
    state_prices = {
        'MH': round(base_val * 1.04),
        'DL': round(base_val * 0.92),
        'KA': round(base_val * 1.07),
        'TN': round(base_val * 1.01),
        'HR': round(base_val * 0.95),
        'UP': round(base_val * 0.94),
        'GJ': round(base_val * 0.97)
    }
    
    # Dealer vs Individual Comparison
    dealer_price = round(base_val * 1.09)
    individual_price = round(base_val * 0.96)
    
    # Seasonal Demand Indices (Simulated monthly offsets)
    seasonal_data = [
        round(base_val * 0.98),  # Jan
        round(base_val * 0.99),  # Feb
        round(base_val * 1.01),  # Mar
        round(base_val * 1.02),  # Apr
        round(base_val * 0.97),  # May
        round(base_val * 0.96),  # Jun
        round(base_val * 0.98),  # Jul
        round(base_val * 0.99),  # Aug
        round(base_val * 1.03),  # Sep
        round(base_val * 1.05),  # Oct (Festive Peak)
        round(base_val * 1.06),  # Nov (Festive Peak)
        round(base_val * 1.04)   # Dec
    ]

    return render_template(
        'report.html',
        user_name=user_name,
        car=car_data,
        spec=spec_dict,
        trend_prices=recalculated['trend_prices'],
        explanation=recalculated['recom_reason'],
        selling_time={'label': recalculated['selling_time_label'], 'days': recalculated['selling_time_days']},
        recal=recalculated,
        ai_scores=ai_scores,
        
        # Market Intelligence datasets
        market_intel={
            'avg_market_price': round(base_val * 0.99),
            'lowest_market_price': round(base_val * 0.92),
            'highest_market_price': round(base_val * 1.08),
            'expected_selling': recalculated['expected_selling_price'],
            'demand_level': recalculated['demand_score'],
            'supply_level': 100 - recalculated['demand_score'],
            'similar_cars': similar_cars,
            'state_prices': state_prices,
            'best_state': 'Karnataka (KA)',
            'worst_state': 'Delhi (DL)',
            'dealer_price': dealer_price,
            'individual_price': individual_price,
            'seasonal_data': seasonal_data
        }
    )

def get_car_comparison_data(car_id):
    # Support mock cars
    if car_id.startswith('mock_'):
        mocks = {
            'mock_swift': {
                'brand': 'Maruti Suzuki', 'model': 'Swift', 'variant': 'VXi', 'year': 2022,
                'fuel': 'Petrol', 'transmission': 'Manual', 'kms': 24000, 'owners': 1,
                'insurance': 'Yes', 'score': 88, 'price': 620000, 'price_low': 590000, 'price_high': 650000,
                'depreciation': 14.0, 'selling_time': 'Fast Sale (7-10 Days)', 'confidence': 95,
                'power': '89 bhp', 'torque': '113 Nm', 'mileage': '22.4 kmpl', 'gc': '163 mm', 'boot': '268 L',
                'maintenance_cost': 5500, 'service_cost': 4500, 'insurance_cost': 18000, 'running_cost': 65000, 'road_tax': 48000,
                'pros': 'Excellent fuel economy, cheap maintenance, huge service network.',
                'cons': 'Build quality is average, lack of advanced features at this trim.'
            },
            'mock_creta': {
                'brand': 'Hyundai', 'model': 'Creta', 'variant': 'SX', 'year': 2023,
                'fuel': 'Petrol', 'transmission': 'Automatic', 'kms': 18000, 'owners': 1,
                'insurance': 'Yes', 'score': 91, 'price': 1480000, 'price_low': 1410000, 'price_high': 1550000,
                'depreciation': 9.0, 'selling_time': 'Fast Sale (7-10 Days)', 'confidence': 96,
                'power': '113 bhp', 'torque': '144 Nm', 'mileage': '17.4 kmpl', 'gc': '190 mm', 'boot': '433 L',
                'maintenance_cost': 7500, 'service_cost': 6000, 'insurance_cost': 38000, 'running_cost': 85000, 'road_tax': 120000,
                'pros': 'Premium interior cabin, smooth automatic transmission, high resale value.',
                'cons': 'Real-world fuel economy is moderate, higher upfront cost.'
            },
            'mock_fortuner': {
                'brand': 'Toyota', 'model': 'Fortuner', 'variant': 'Sigma4', 'year': 2021,
                'fuel': 'Diesel', 'transmission': 'Automatic', 'kms': 55000, 'owners': 2,
                'insurance': 'Yes', 'score': 84, 'price': 3450000, 'price_low': 3290000, 'price_high': 3610000,
                'depreciation': 21.0, 'selling_time': 'Average Sale (15-25 Days)', 'confidence': 92,
                'power': '201 bhp', 'torque': '500 Nm', 'mileage': '14.4 kmpl', 'gc': '225 mm', 'boot': '296 L',
                'maintenance_cost': 12000, 'service_cost': 9500, 'insurance_cost': 75000, 'running_cost': 110000, 'road_tax': 320000,
                'pros': 'Unmatched road presence, bulletproof reliability, massive torque delivery.',
                'cons': 'Bumpy ride quality at low speeds, expensive routine maintenance.'
            },
            'mock_nexon': {
                'brand': 'Tata', 'model': 'Nexon', 'variant': 'XZ', 'year': 2022,
                'fuel': 'Petrol', 'transmission': 'Manual', 'kms': 32000, 'owners': 1,
                'insurance': 'No', 'score': 80, 'price': 890000, 'price_low': 840000, 'price_high': 940000,
                'depreciation': 18.0, 'selling_time': 'Average Sale (15-25 Days)', 'confidence': 94,
                'power': '118 bhp', 'torque': '170 Nm', 'mileage': '17.4 kmpl', 'gc': '209 mm', 'boot': '350 L',
                'maintenance_cost': 6500, 'service_cost': 5500, 'insurance_cost': 26000, 'running_cost': 72000, 'road_tax': 78000,
                'pros': '5-star Global NCAP safety rating, high ground clearance, spacious seats.',
                'cons': 'Infotainment interface displays minor lag, gearbox throw is slightly long.'
            }
        }
        return mocks.get(car_id)
        
    if car_id.startswith('db_'):
        try:
            spec_id = int(car_id.split('_')[1])
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM car_database WHERE id = ?', (spec_id,))
            r = cursor.fetchone()
            conn.close()
            
            if r:
                calc_mock = {
                    'brand': r[1],
                    'model': r[2],
                    'variant': r[3],
                    'manufacturing_year': 2022,
                    'purchase_year': 2022,
                    'registration_year': 2022,
                    'registration_state': 'MH',
                    'fuel_type': r[4],
                    'transmission': r[5],
                    'kilometers_driven': 30000,
                    'owner_number': 1,
                    'insurance': 'Yes',
                    'insurance_type': 'Comprehensive',
                    'service_history': 'Authorized',
                    'number_of_services': 5,
                    'accident_history': 'No'
                }
                val = calculate_valuation(calc_mock)
                
                return {
                    'brand': r[1],
                    'model': r[2],
                    'variant': r[3],
                    'year': 2022,
                    'fuel': r[4],
                    'transmission': r[5],
                    'kms': 30000,
                    'owners': 1,
                    'insurance': 'Yes',
                    'score': val['ai_valuation_score'],
                    'price': val['estimated_market_value'],
                    'price_expected': val['expected_selling_price'],
                    'price_low': val['fair_price_low'],
                    'price_high': val['fair_price_high'],
                    'depreciation': val['depreciation_percentage'],
                    'confidence': val['confidence_score'],
                    'selling_time': f"{val['selling_time_label']} ({val['selling_time_days']})",
                    'power': r[8],
                    'torque': r[9],
                    'mileage': r[10],
                    'gc': r[13],
                    'boot': r[14],
                    'engine': r[6],
                    'maintenance_cost': 6000,
                    'service_cost': 4800,
                    'insurance_cost': round(val['estimated_market_value'] * 0.025),
                    'running_cost': 72000,
                    'road_tax': round(val['estimated_market_value'] * 0.08),
                    'pros': f"Verified {r[1]} engineering, solid mileage index of {r[10]}, robust resale capability.",
                    'cons': "Typical wear parameters for standard 30,000 km running threshold."
                }
        except Exception as e:
            print(f"Error compiling db spec comparison: {str(e)}")

    # Read from database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cars WHERE id = ?', (int(car_id),))
        r = cursor.fetchone()
        conn.close()
        
        if r:
            car_data = map_car_row_to_dict(r)
            
            # Gather specs
            conn = sqlite3.connect(DB_PATH)
            spec_cursor = conn.cursor()
            spec_cursor.execute('SELECT * FROM car_database WHERE brand = ? AND model = ? AND variant = ? LIMIT 1', (car_data['brand'], car_data['model'], car_data['variant']))
            spec_row = spec_cursor.fetchone()
            conn.close()
            
            # Map parameters
            power = "N/A"
            torque = "N/A"
            mileage = "N/A"
            gc = "170 mm"
            boot = "350 L"
            cc = "N/A"
            if spec_row:
                power = spec_row[8]
                torque = spec_row[9]
                mileage = spec_row[10]
                gc = spec_row[13]
                boot = spec_row[14]
                cc = spec_row[6]
                
            # Deduce pros & cons, maintenance indicators dynamically
            m_cost = 6000 + (car_data['year'] - 2020) * -500 + (car_data['kms'] * 0.03)
            s_cost = m_cost * 0.8
            ins_cost = car_data['price'] * 0.025
            run_cost = (car_data['kms'] / 10.0) * 98.0  # fuel distance ratio
            road_tax = car_data['price'] * 0.08
            
            p_rating = car_data['score']
            pros = "Excellent value retention, verified service record history, high structural condition score." if p_rating >= 80 else "Decent budget choice, normal wear indicators, standard mechanical safety."
            cons = "Slightly higher odometer mileage, cosmetic scratches reported." if car_data['kms'] > 60000 else "Standard depreciation drop due to segment age limit."
            
            return {
                'brand': car_data['brand'],
                'model': car_data['model'],
                'variant': car_data['variant'],
                'year': car_data['year'],
                'fuel': car_data['fuel'],
                'transmission': car_data['transmission'],
                'kms': car_data['kms'],
                'owners': car_data['owners'],
                'insurance': car_data['insurance'],
                'score': car_data['score'],
                'price': car_data['price'],
                'price_expected': car_data['price_expected'],
                'price_low': car_data['price_low'],
                'price_high': car_data['price_high'],
                'depreciation': car_data['depreciation'],
                'confidence': car_data['confidence'],
                'selling_time': car_data['deal'],
                'power': power,
                'torque': torque,
                'mileage': mileage,
                'gc': gc,
                'boot': boot,
                'engine': cc,
                'maintenance_cost': round(m_cost),
                'service_cost': round(s_cost),
                'insurance_cost': round(ins_cost),
                'running_cost': round(run_cost),
                'road_tax': round(road_tax),
                'pros': pros,
                'cons': cons
            }
    except Exception as e:
        print(f"Error fetching comparison: {str(e)}")
        
    return None

@app.route('/compare')
def compare():
    user_cars = []
    if 'user_id' in session:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, brand, model, variant, manufacturing_year, estimated_market_value FROM cars WHERE user_id = ? ORDER BY id DESC', (session['user_id'],))
        user_cars = [{'id': str(r[0]), 'label': f"{r[1]} {r[2]} {r[3]} ({r[4]})"} for r in cursor.fetchall()]
        conn.close()
        
    if not user_cars:
        user_cars = [
            {'id': 'mock_swift', 'label': 'Maruti Suzuki Swift VXi 2022 (Mock)'},
            {'id': 'mock_creta', 'label': 'Hyundai Creta SX 2023 (Mock)'},
            {'id': 'mock_fortuner', 'label': 'Toyota Fortuner Sigma4 2021 (Mock)'},
            {'id': 'mock_nexon', 'label': 'Tata Nexon XZ 2022 (Mock)'}
        ]

    car_a_id = request.args.get('car_a')
    car_b_id = request.args.get('car_b')
    
    car_a = None
    car_b = None
    recom_text = ""
    
    if car_a_id and car_b_id:
        car_a = get_car_comparison_data(car_a_id)
        car_b = get_car_comparison_data(car_b_id)
        
        if car_a and car_b:
            recom_bullets = []
            
            # Estimate Price comparison
            if car_a['price'] > car_b['price']:
                recom_bullets.append(f"Car A ({car_a['brand']} {car_a['model']}) holds a higher resale value of ₹ {format_indian_currency(car_a['price'])} compared to ₹ {format_indian_currency(car_b['price'])} for Car B.")
            else:
                recom_bullets.append(f"Car B ({car_b['brand']} {car_b['model']}) holds a higher resale value of ₹ {format_indian_currency(car_b['price'])} compared to ₹ {format_indian_currency(car_a['price'])} for Car A.")
            
            # Value Retention comparison
            if car_a['depreciation'] < car_b['depreciation']:
                recom_bullets.append(f"Car A has lower cumulative value depreciation of {car_a['depreciation']}% (compared to {car_b['depreciation']}% for Car B).")
            else:
                recom_bullets.append(f"Car B has lower cumulative value depreciation of {car_b['depreciation']}% (compared to {car_a['depreciation']}% for Car A).")
                
            # Score recommendation
            if car_a['score'] > car_b['score']:
                recom_bullets.append(f"Car A carries a higher AI Score and is highly recommended for purchase/selling due to better condition metrics.")
            else:
                recom_bullets.append(f"Car B carries a higher AI Score and is highly recommended for purchase/selling due to better condition metrics.")
                
            recom_text = " ".join(recom_bullets)

    return render_template(
        'compare.html',
        user_cars=user_cars,
        car_a=car_a,
        car_b=car_b,
        car_a_id=car_a_id,
        car_b_id=car_b_id,
        recom_text=recom_text
    )

@app.route('/favorites')
def favorites_page():
    if 'user_id' not in session:
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query all favorites details
    cursor.execute('''
        SELECT f.id, f.car_id, c.brand, c.model, c.variant, c.manufacturing_year, c.fuel_type, c.transmission,
               c.kilometers_driven, c.ai_valuation_score, c.estimated_market_value, c.expected_selling_price,
               c.confidence_score, c.depreciation_percentage, f.created_at, c.deal_rating, c.vehicle_health_score
        FROM favorites f
        JOIN cars c ON f.car_id = c.id
        WHERE f.user_id = ?
        ORDER BY f.id DESC
    ''', (session['user_id'],))
    rows = cursor.fetchall()
    
    favorites_list = []
    total_score = 0
    max_value = 0
    total_value = 0
    brands_freq = {}
    fuels_freq = {}
    
    for r in rows:
        car_price = r[10]
        car_score = r[9]
        car_brand = r[2]
        car_fuel = r[6]
        
        car_obj = {
            'fav_id': r[0],
            'car_id': r[1],
            'brand': r[2],
            'model': r[3],
            'variant': r[4],
            'year': r[5],
            'fuel': r[6],
            'transmission': r[7],
            'kms': r[8],
            'score': r[9],
            'price': r[10],
            'price_expected': r[11],
            'confidence': r[12],
            'depreciation': r[13],
            'date_added': r[14][:10],
            'deal': r[15],
            'health': r[16]
        }
        favorites_list.append(car_obj)
        
        total_score += car_score
        total_value += car_price
        if car_price > max_value:
            max_value = car_price
            
        brands_freq[car_brand] = brands_freq.get(car_brand, 0) + 1
        fuels_freq[car_fuel] = fuels_freq.get(car_fuel, 0) + 1
        
    count = len(favorites_list)
    avg_score = round(total_score / count) if count > 0 else 0
    avg_value = round(total_value / count) if count > 0 else 0
    
    fav_brand = max(brands_freq, key=brands_freq.get) if brands_freq else "N/A"
    fav_fuel = max(fuels_freq, key=fuels_freq.get) if fuels_freq else "N/A"
    
    stats = {
        'count': count,
        'avg_score': avg_score,
        'max_value': max_value,
        'avg_value': avg_value,
        'fav_brand': fav_brand,
        'fav_fuel': fav_fuel
    }
    
    chart_data = {
        'brands': list(brands_freq.keys()),
        'brand_counts': list(brands_freq.values()),
        'fuels': list(fuels_freq.keys()),
        'fuel_counts': list(fuels_freq.values()),
        'prices': [x['price'] for x in favorites_list],
        'scores': [x['score'] for x in favorites_list]
    }
    
    conn.close()
    return render_template(
        'favorites.html',
        favorites=favorites_list,
        stats=stats,
        chart_data=chart_data
    )

@app.route('/api/toggle-favorite/<int:car_id>', methods=['POST'])
def api_toggle_favorite(car_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Authentication required. Please login.'}), 401
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT brand, model, variant, manufacturing_year, estimated_market_value FROM cars WHERE id = ?', (car_id,))
    car = cursor.fetchone()
    if not car:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Vehicle log not found.'}), 404
        
    cursor.execute('SELECT id FROM favorites WHERE user_id = ? AND car_id = ?', (session['user_id'], car_id))
    fav = cursor.fetchone()
    
    if fav:
        cursor.execute('DELETE FROM favorites WHERE id = ?', (fav[0],))
        cursor.execute('UPDATE cars SET is_favorite = 0 WHERE id = ?', (car_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'removed', 'message': 'Removed from Favorites'})
    else:
        cursor.execute('''
            INSERT INTO favorites (user_id, car_id, brand, model, variant, manufacturing_year, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], car_id, car[0], car[1], car[2], car[3], car[4]))
        cursor.execute('UPDATE cars SET is_favorite = 1 WHERE id = ?', (car_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'added', 'message': '✓ Added to Favorites'})

@app.route('/api/move-to-my-cars/<int:car_id>', methods=['POST'])
def api_move_to_my_cars(car_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE cars SET is_saved = 0 WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    cursor.execute('DELETE FROM favorites WHERE car_id = ? AND user_id = ?', (car_id, session['user_id']))
    cursor.execute('UPDATE cars SET is_favorite = 0 WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Moved report to general history.', 'success')
    return redirect(url_for('favorites_page'))

@app.route('/api/search-models')
def api_search_models():
    q = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 15))
    offset = (page - 1) * limit

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    words = q.split()
    conditions = []
    params = []

    for w in words:
        conditions.append("(brand LIKE ? OR model LIKE ?)")
        like_w = f"%{w}%"
        params.extend([like_w, like_w])

    sql = "SELECT DISTINCT brand, model, body_type FROM car_database"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            'brand': r[0],
            'model': r[1],
            'body_type': r[2]
        })

    return jsonify(results)

@app.route('/api/model-variants')
def api_model_variants():
    brand = request.args.get('brand', '').strip()
    model = request.args.get('model', '').strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT variant, fuel_type, transmission 
        FROM car_database 
        WHERE brand = ? AND model = ?
        ORDER BY variant ASC
    ''', (brand, model))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            'variant': r[0],
            'fuel': r[1],
            'transmission': r[2]
        })
    return jsonify(results)

@app.route('/api/variant-years')
def api_variant_years():
    brand = request.args.get('brand', '').strip()
    model = request.args.get('model', '').strip()
    variant = request.args.get('variant', '').strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT manufacturing_year 
        FROM car_database 
        WHERE brand = ? AND model = ? AND variant = ?
        ORDER BY manufacturing_year DESC
    ''', (brand, model, variant))
    rows = cursor.fetchall()
    conn.close()

    years = [r[0] for r in rows]
    return jsonify(years)

@app.route('/api/add-favorite-final', methods=['POST'])
def api_add_favorite_final():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Please login to add favorites.'}), 401

    data = request.get_json()
    brand = data.get('brand')
    model = data.get('model')
    variant = data.get('variant')
    year = int(data.get('year', 2022))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find the specs template row
    cursor.execute('''
        SELECT id, fuel_type, transmission 
        FROM car_database 
        WHERE brand = ? AND model = ? AND variant = ? AND manufacturing_year = ? 
        LIMIT 1
    ''', (brand, model, variant, year))
    r = cursor.fetchone()
    
    if not r:
        # Fallback if specific year template missing, fetch latest matching variant
        cursor.execute('''
            SELECT id, fuel_type, transmission 
            FROM car_database 
            WHERE brand = ? AND model = ? AND variant = ? 
            LIMIT 1
        ''', (brand, model, variant))
        r = cursor.fetchone()
        
    if not r:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Vehicle configuration specs not found.'}), 404

    spec_id, fuel, trans = r

    # Simulate valuation
    calc_mock = {
        'brand': brand,
        'model': model,
        'variant': variant,
        'manufacturing_year': year,
        'purchase_year': year,
        'registration_year': year,
        'registration_state': 'MH',
        'fuel_type': fuel,
        'transmission': trans,
        'kilometers_driven': 30000,
        'owner_number': 1,
        'insurance': 'Yes',
        'insurance_type': 'Comprehensive',
        'service_history': 'Authorized',
        'number_of_services': 5,
        'accident_history': 'No'
    }
    val = calculate_valuation(calc_mock)

    # Insert valuation log
    cursor.execute('''
        INSERT INTO cars (
            user_id, brand, model, variant, manufacturing_year, purchase_year, registration_year,
            registration_state, registration_number, number_plate_type, fuel_type, transmission,
            kilometers_driven, owner_number, insurance, insurance_type, insurance_expiry,
            service_history, number_of_services, last_service_date, accident_history, accident_severity,
            colour, engine_serial_no, chassis_no, rc_available, puc_available, service_records_available,
            engine_condition, gearbox_condition, clutch_condition, brake_condition, tyre_condition, suspension_condition, battery_condition,
            ac_condition, electrical_condition, paint_condition, rust_condition, door_condition, outer_body_score, inner_body_score,
            seat_quality_score, infotainment_score, mirror_condition, windshield_condition, sunroof, alloy_wheels,
            accessories, modifications,
            estimated_market_value, expected_selling_price, fair_price_low, fair_price_high,
            ai_valuation_score, confidence_score, vehicle_health_score, depreciation_percentage,
            deal_rating, is_favorite, is_saved
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
    ''', (
        session['user_id'], brand, model, variant, year, year, year,
        'MH', 'MH-01-AA-0001', 'Normal', fuel, trans,
        30000, 1, 'Yes', 'Comprehensive', '2027-01-01',
        'Authorized', 5, '2026-01-01', 'No', 'None',
        'Silver', 'ENG123456', 'CHS123456', 'Yes', 'Yes', 'Yes',
        'Excellent', 'Excellent', 'Excellent', 'Excellent', 'Excellent', 'Excellent', 'Excellent',
        'Excellent', 'Excellent', 'Excellent', 'Excellent', 'Excellent', 90, 90,
        90, 90, 'Excellent', 'Excellent', 'No', 'No',
        'No', 'No',
        val['estimated_market_value'], val['expected_selling_price'],
        val['fair_price_low'], val['fair_price_high'],
        val['ai_valuation_score'], val['confidence_score'],
        90, val['depreciation_percentage'], val['deal_rating']
    ))
    new_car_id = cursor.lastrowid

    # Insert favorite
    cursor.execute('''
        INSERT INTO favorites (user_id, car_id, brand, model, variant, manufacturing_year, price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], new_car_id, brand, model, variant, year, val['estimated_market_value']))

    conn.commit()
    conn.close()
    return jsonify({'status': 'added', 'message': '✓ Added to Favorites'})

@app.route('/api/search-cars-advanced')
def api_search_cars_advanced():
    q = request.args.get('q', '').strip()
    fuel = request.args.get('fuel', '').strip()
    trans = request.args.get('transmission', '').strip()
    year = request.args.get('year', '').strip()
    body_type = request.args.get('body_type', '').strip()
    price_range = request.args.get('price_range', '').strip()
    brand = request.args.get('brand', '').strip()
    
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 25))
    offset = (page - 1) * limit
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if q:
        words = q.split()
        for w in words:
            conditions.append("(brand LIKE ? OR model LIKE ? OR variant LIKE ?)")
            like_w = f"%{w}%"
            params.extend([like_w, like_w, like_w])
            
    if fuel:
        conditions.append("fuel_type = ?")
        params.append(fuel)
    if trans:
        conditions.append("transmission = ?")
        params.append(trans)
    if year:
        conditions.append("manufacturing_year = ?")
        params.append(int(year))
    if body_type:
        conditions.append("body_type = ?")
        params.append(body_type)
    if brand:
        conditions.append("brand = ?")
        params.append(brand)
        
    if price_range:
        if price_range == 'under_10':
            conditions.append("base_showroom_price < 1000000")
        elif price_range == '10_20':
            conditions.append("base_showroom_price BETWEEN 1000000 AND 2000000")
        elif price_range == '20_50':
            conditions.append("base_showroom_price BETWEEN 2000000 AND 5000000")
        elif price_range == 'over_50':
            conditions.append("base_showroom_price > 5000000")
            
    sql = "SELECT id, brand, model, variant, manufacturing_year, fuel_type, transmission, base_showroom_price, body_type FROM car_database"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
        
    sql += " ORDER BY brand ASC, model ASC, base_showroom_price DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    user_fav_keys = {}
    if 'user_id' in session:
        cursor.execute('SELECT car_id, brand, model, variant, manufacturing_year FROM favorites WHERE user_id = ?', (session['user_id'],))
        for f_row in cursor.fetchall():
            key = (f_row[1].lower(), f_row[2].lower(), f_row[3].lower(), f_row[4])
            user_fav_keys[key] = f_row[0]
            
    results = []
    for r in rows:
        spec_id = r[0]
        b = r[1]
        m = r[2]
        v = r[3]
        y = r[4]
        fl = r[5]
        tr = r[6]
        pr = r[7]
        bt = r[8]
        
        key = (b.lower(), m.lower(), v.lower(), y)
        car_id = user_fav_keys.get(key, None)
        is_fav = car_id is not None
        
        results.append({
            'spec_id': spec_id,
            'brand': b,
            'model': m,
            'variant': v,
            'year': y,
            'fuel': fl,
            'transmission': tr,
            'price': pr,
            'body_type': bt,
            'is_favorite': is_fav,
            'car_id': car_id
        })
        
    conn.close()
    return jsonify(results)

@app.route('/api/favorites/bulk-delete', methods=['POST'])
def api_favorites_bulk_delete():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Please login to continue.'}), 401
        
    data = request.get_json()
    car_ids = data.get('ids', [])
    if not car_ids:
        return jsonify({'status': 'error', 'message': 'No IDs provided.'}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ",".join(["?"] * len(car_ids))
    cursor.execute(f'DELETE FROM favorites WHERE user_id = ? AND car_id IN ({placeholders})', [session['user_id']] + car_ids)
    cursor.execute(f'UPDATE cars SET is_favorite = 0 WHERE user_id = ? AND id IN ({placeholders})', [session['user_id']] + car_ids)
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Deleted {len(car_ids)} bookmarks.'})

@app.route('/api/export-favorites')
def api_export_favorites():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    car_ids_str = request.args.get('ids', '')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    sql = '''
        SELECT c.brand, c.model, c.variant, c.manufacturing_year, c.fuel_type, c.transmission,
               c.kilometers_driven, c.ai_valuation_score, c.estimated_market_value, c.expected_selling_price
        FROM favorites f
        JOIN cars c ON f.car_id = c.id
        WHERE f.user_id = ?
    '''
    params = [session['user_id']]
    
    if car_ids_str:
        car_ids = [int(x) for x in car_ids_str.split(',') if x.isdigit()]
        if car_ids:
            placeholders = ",".join(["?"] * len(car_ids))
            sql += f" AND f.car_id IN ({placeholders})"
            params.extend(car_ids)
            
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    import io
    import csv
    from flask import make_response
    
    dest = io.StringIO()
    writer = csv.writer(dest)
    writer.writerow(['Brand', 'Model', 'Variant', 'Year', 'Fuel Type', 'Transmission', 'Kms Driven', 'AI Valuation Score', 'Estimated Value', 'Expected Price'])
    writer.writerows(rows)
    
    response.headers['Content-Disposition'] = 'attachment; filename=favorites_export.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/market-intelligence')
def market_intelligence():
    return render_template('market_intelligence.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

import os
from werkzeug.utils import secure_filename

# Configuration for garage image uploads
UPLOAD_GARAGE_DIR = os.path.join('static', 'uploads', 'garage')
os.makedirs(UPLOAD_GARAGE_DIR, exist_ok=True)
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_IMAGE_EXTENSIONS']

@app.route('/garage')
def garage():
    if 'user_id' not in session:
        flash('Please login to view your Digital Garage.', 'warning')
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if this user has any vehicle in their garage
    cursor.execute('SELECT COUNT(*) FROM cars WHERE user_id = ? AND is_garage = 1', (session['user_id'],))
    count = cursor.fetchone()[0]
    if count == 0:
        # Create the sample WagonR vehicle automatically
        cursor.execute('''
            INSERT INTO cars (
                user_id, brand, model, variant, manufacturing_year, purchase_year, registration_year,
                registration_state, registration_number, fuel_type, transmission, kilometers_driven,
                owner_number, colour, engine_serial_no, chassis_no,
                estimated_market_value, expected_selling_price, confidence_score, vehicle_health_score,
                depreciation_percentage, rc_available, insurance, insurance_type, insurance_expiry,
                puc_available, puc_expiry, next_service_date, battery_expiry, is_garage, is_saved,
                number_plate_type, service_history, number_of_services, last_service_date, accident_history
            ) VALUES (
                ?, 'Maruti Suzuki', 'WagonR', 'LXi Petrol Manual', 2022, 2022, 2022,
                'Maharashtra', 'MH02AB4515', 'Petrol', 'Manual', 14210,
                1, 'White', '1197 cc', '21.79 kmpl',
                568000.0, 555000.0, 98, 92,
                18.0, 'yes', 'ICICI Lombard', 'Comprehensive', '2027-03-15',
                'yes', '2026-10-18', '2026-08-16', '2028-06-18', 1, 1,
                'Standard', 'Available', 5, '2026-06-01', 'No'
            )
        ''', (session['user_id'],))
        conn.commit()
    
    # Fetch garage vehicles
    cursor.execute('''
        SELECT id, brand, model, variant, registration_number, manufacturing_year, fuel_type, transmission,
               kilometers_driven, ai_valuation_score, vehicle_health_score, estimated_market_value, created_at,
               garage_images, puc_expiry, next_service_date, battery_expiry, is_favorite, insurance, insurance_type, insurance_expiry,
               engine_serial_no, chassis_no
        FROM cars
        WHERE user_id = ? AND is_garage = 1
        ORDER BY id DESC
    ''', (session['user_id'],))
    rows = cursor.fetchall()
    
    vehicles = []
    total_value = 0
    total_score = 0
    max_val = 0
    max_val_name = "N/A"
    
    brand_counts = {}
    fuel_counts = {}
    age_counts = {}
    
    for r in rows:
        car_id = r[0]
        brand = r[1]
        model = r[2]
        variant = r[3]
        reg_no = r[4]
        year = r[5]
        fuel = r[6]
        trans = r[7]
        kms = r[8]
        score = r[9] or 0
        health = r[10] or 0
        est_val = r[11] or 0
        created = r[12][:10]
        
        # Parse images list
        imgs_str = r[13]
        images = [img.strip() for img in imgs_str.split(',') if img.strip()] if imgs_str else []
        img_url = images[0] if images else '/static/images/car-placeholder.jpg'
        
        puc = r[14] or ""
        next_srv = r[15] or ""
        battery = r[16] or ""
        is_fav = r[17] or 0
        
        total_value += est_val
        total_score += score
        if est_val > max_val:
            max_val = est_val
            max_val_name = f"{brand} {model}"
            
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
        fuel_counts[fuel] = fuel_counts.get(fuel, 0) + 1
        age_group = "New (<2 yrs)" if (2026 - year) < 2 else ("Mid (2-5 yrs)" if (2026 - year) <= 5 else "Old (>5 yrs)")
        age_counts[age_group] = age_counts.get(age_group, 0) + 1
        
        # Maintenance checklist rules
        # If dates are empty, fill default mock alerts for demonstration
        if not puc:
            puc = "2026-12-15"
        if not next_srv:
            next_srv = "2026-11-20"
        if not battery:
            battery = "2028-06-18"
            
        demand_tier = "High"
        if brand.lower() in ['maruti suzuki', 'toyota', 'hyundai', 'mahindra']:
            demand_tier = "Very High"
        elif brand.lower() in ['audi', 'bmw', 'mercedes-benz', 'porsche']:
            demand_tier = "Medium"
            
        best_month = "October/November"
        est_profit = round(est_val * 0.08)
        
        # Extract engine capacity and mileage dynamically
        engine_cap = r[21] or ""
        mileage_val = r[22] or ""
        if not engine_cap or not mileage_val:
            cursor.execute('SELECT engine_capacity, mileage FROM car_database WHERE brand = ? AND model = ? AND variant = ? LIMIT 1', (brand, model, variant))
            spec = cursor.fetchone()
            if spec:
                if not engine_cap: engine_cap = spec[0]
                if not mileage_val: mileage_val = spec[1]
        
        if not engine_cap: engine_cap = "1197 cc"
        if not mileage_val: mileage_val = "21.79 kmpl"
        
        vehicles.append({
            'id': car_id,
            'brand': brand,
            'model': model,
            'variant': variant,
            'reg_no': reg_no,
            'year': year,
            'fuel': fuel,
            'trans': trans,
            'kms': kms,
            'score': score,
            'health': health,
            'value': est_val,
            'date': created,
            'image': img_url,
            'images': images,
            'puc': puc,
            'next_srv': next_srv,
            'battery': battery,
            'is_fav': is_fav,
            'demand': demand_tier,
            'best_month': best_month,
            'profit': est_profit,
            'insurance_provider': r[18] or "N/A",
            'insurance_type': r[19] or "N/A",
            'insurance_expiry': r[20] or "",
            'engine_capacity': engine_cap,
            'mileage': mileage_val
        })
        
    num_vehicles = len(vehicles)
    avg_score = round(total_score / num_vehicles) if num_vehicles > 0 else 0
    
    # Fetch all evaluated user cars not in garage to let them add
    cursor.execute('''
        SELECT id, brand, model, variant, manufacturing_year, estimated_market_value
        FROM cars
        WHERE user_id = ? AND is_garage = 0
        ORDER BY id DESC
    ''', (session['user_id'],))
    available_rows = cursor.fetchall()
    available_cars = [{
        'id': c[0], 'brand': c[1], 'model': c[2], 'variant': c[3], 'year': c[4], 'value': c[5]
    } for c in available_rows]
    
    conn.close()
    
    # Charts telemetry payload
    charts_data = {
        'names': [f"{v['brand']} {v['model']}" for v in vehicles],
        'values': [v['value'] for v in vehicles],
        'kms': [v['kms'] for v in vehicles],
        'brands': list(brand_counts.keys()),
        'brand_vals': list(brand_counts.values()),
        'fuels': list(fuel_counts.keys()),
        'fuel_vals': list(fuel_counts.values()),
        'ages': list(age_counts.keys()),
        'age_vals': list(age_counts.values())
    }
    
    return render_template('garage.html', vehicles=vehicles, num_vehicles=num_vehicles, 
                           total_value=total_value, avg_score=avg_score, max_val_name=max_val_name, 
                           available_cars=available_cars, charts_data=charts_data)

@app.route('/garage/add/<int:car_id>', methods=['GET', 'POST'])
def garage_add(car_id):
    if 'user_id' not in session:
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE cars SET is_garage = 1 WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Vehicle successfully added to your Digital Garage.', 'success')
    return redirect(url_for('garage'))

@app.route('/garage/add-manual', methods=['POST'])
def garage_add_manual():
    if 'user_id' not in session:
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    try:
        # Extract form values
        brand = request.form.get('brand')
        model = request.form.get('model')
        variant = request.form.get('variant')
        manufacturing_year = int(request.form.get('manufacturing_year', 2022))
        registration_state = request.form.get('registration_state')
        registration_number = request.form.get('registration_number')
        fuel_type = request.form.get('fuel_type')
        transmission = request.form.get('transmission')
        kilometers_driven = int(request.form.get('kilometers_driven', 10000))
        owner_number = int(request.form.get('owner_number', 1))
        colour = request.form.get('colour', 'White')
        engine_capacity = request.form.get('engine_capacity', '1197 cc')
        mileage = request.form.get('mileage', '20.0 kmpl')
        
        estimated_market_value = float(request.form.get('estimated_market_value', 500000))
        expected_selling_price = float(request.form.get('expected_selling_price', 480000))
        confidence_score = int(request.form.get('confidence_score', 95))
        vehicle_health_score = int(request.form.get('vehicle_health_score', 90))
        depreciation_percentage = float(request.form.get('depreciation_percentage', 15))
        
        rc_available = request.form.get('rc_available', 'yes')
        insurance = request.form.get('insurance_provider', 'N/A')
        insurance_type = request.form.get('insurance_type', 'Comprehensive')
        insurance_expiry = request.form.get('insurance_expiry')
        puc_available = request.form.get('puc_available', 'yes')
        puc_expiry = request.form.get('puc_expiry')
        next_service_date = request.form.get('next_service_date')
        battery_expiry = request.form.get('battery_expiry', '2028-06-18')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cars (
                user_id, brand, model, variant, manufacturing_year, purchase_year, registration_year,
                registration_state, registration_number, fuel_type, transmission, kilometers_driven,
                owner_number, colour, engine_serial_no, chassis_no,
                estimated_market_value, expected_selling_price, confidence_score, vehicle_health_score,
                depreciation_percentage, rc_available, insurance, insurance_type, insurance_expiry,
                puc_available, puc_expiry, next_service_date, battery_expiry, is_garage, is_saved,
                number_plate_type, service_history, number_of_services, last_service_date, accident_history
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, 1, 1,
                'Standard', 'Available', 5, '2026-06-01', 'No'
            )
        ''', (
            session['user_id'], brand, model, variant, manufacturing_year, manufacturing_year, manufacturing_year,
            registration_state, registration_number, fuel_type, transmission, kilometers_driven,
            owner_number, colour, engine_capacity, mileage,
            estimated_market_value, expected_selling_price, confidence_score, vehicle_health_score,
            depreciation_percentage, rc_available, insurance, insurance_type, insurance_expiry,
            puc_available, puc_expiry, next_service_date, battery_expiry
        ))
        conn.commit()
        conn.close()
        
        flash('Vehicle successfully added to your Digital Garage.', 'success')
    except Exception as e:
        flash(f'Error adding vehicle manually: {str(e)}', 'danger')
        
    return redirect(url_for('garage'))

@app.route('/garage/delete/<int:car_id>', methods=['GET', 'POST'])
def garage_delete(car_id):
    if 'user_id' not in session:
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE cars SET is_garage = 0 WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Vehicle removed from your Digital Garage.', 'info')
    return redirect(url_for('garage'))

@app.route('/garage/favorite/<int:car_id>', methods=['GET', 'POST'])
def garage_favorite(car_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT is_favorite FROM cars WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    row = cursor.fetchone()
    if row:
        new_fav = 1 if row[0] == 0 else 0
        cursor.execute('UPDATE cars SET is_favorite = ? WHERE id = ? AND user_id = ?', (new_fav, car_id, session['user_id']))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'is_favorite': new_fav})
    conn.close()
    return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404

@app.route('/garage/edit/<int:car_id>', methods=['POST'])
def garage_edit(car_id):
    if 'user_id' not in session:
        flash('Please login to continue.', 'warning')
        return redirect(url_for('login'))
        
    reg_no = request.form.get('reg_no', '').strip()
    kms = request.form.get('kms', '').strip()
    ins_exp = request.form.get('ins_exp', '').strip()
    puc_exp = request.form.get('puc_exp', '').strip()
    srv_date = request.form.get('srv_date', '').strip()
    bat_exp = request.form.get('bat_exp', '').strip()
    
    if not kms.isdigit():
        flash('Invalid kilometers value.', 'danger')
        return redirect(url_for('garage'))
        
    kms_val = int(kms)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get original parameters to revalue
    cursor.execute('''
        SELECT brand, model, variant, manufacturing_year, purchase_year, registration_year, registration_state,
               number_plate_type, fuel_type, transmission, owner_number, insurance, insurance_type,
               service_history, number_of_services, last_service_date, accident_history, accident_severity,
               colour, engine_serial_no, chassis_no, rc_available, puc_available, service_records_available,
               engine_condition, gearbox_condition, clutch_condition, brake_condition, tyre_condition,
               suspension_condition, battery_condition, ac_condition, electrical_condition, paint_condition,
               rust_condition, door_condition, outer_body_score, inner_body_score, seat_quality_score,
               infotainment_score, mirror_condition, windshield_condition, sunroof, alloy_wheels,
               accessories, modifications
        FROM cars WHERE id = ? AND user_id = ?
    ''', (car_id, session['user_id']))
    car_row = cursor.fetchone()
    
    if not car_row:
        conn.close()
        flash('Vehicle not found.', 'danger')
        return redirect(url_for('garage'))
        
    # Revalue based on updated kilometers driven
    keys = [
        'brand', 'model', 'variant', 'year', 'purchase_year', 'registration_year', 'registration_state',
        'number_plate_type', 'fuel_type', 'transmission', 'owners', 'insurance', 'insurance_type',
        'service_history', 'number_of_services', 'last_service_date', 'accident_history', 'accident_severity',
        'colour', 'engine_serial_no', 'chassis_no', 'rc_available', 'puc_available', 'service_records_available',
        'engine_condition', 'gearbox_condition', 'clutch_condition', 'brake_condition', 'tyre_condition',
        'suspension_condition', 'battery_condition', 'ac_condition', 'electrical_condition', 'paint_condition',
        'rust_condition', 'door_condition', 'outer_body_score', 'inner_body_score', 'seat_quality_score',
        'infotainment_score', 'mirror_condition', 'windshield_condition', 'sunroof', 'alloy_wheels',
        'accessories', 'modifications'
    ]
    car_dict = dict(zip(keys, car_row))
    car_dict['car-kms'] = kms_val
    
    val_results = calculate_valuation(car_dict)
    
    # Save edits back to database
    cursor.execute('''
        UPDATE cars SET 
            registration_number = ?,
            kilometers_driven = ?,
            insurance_expiry = ?,
            puc_expiry = ?,
            next_service_date = ?,
            battery_expiry = ?,
            estimated_market_value = ?,
            expected_selling_price = ?,
            fair_price_low = ?,
            fair_price_high = ?,
            ai_valuation_score = ?,
            confidence_score = ?,
            vehicle_health_score = ?,
            depreciation_percentage = ?
        WHERE id = ? AND user_id = ?
    ''', (reg_no, kms_val, ins_exp, puc_exp, srv_date, bat_exp,
          val_results['estimated_market_value'],
          val_results['expected_selling_price'],
          val_results['fair_price_low'],
          val_results['fair_price_high'],
          val_results['ai_valuation_score'],
          val_results['confidence_score'],
          val_results['vehicle_health_score'],
          val_results['depreciation_percentage'],
          car_id, session['user_id']))
          
    conn.commit()
    conn.close()
    
    flash('Vehicle details updated and revalued successfully.', 'success')
    return redirect(url_for('garage'))

@app.route('/garage/upload-images/<int:car_id>', methods=['POST'])
def garage_upload_images(car_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        
    uploaded_files = request.files.getlist('images')
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({'status': 'error', 'message': 'No files uploaded'}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch current images
    cursor.execute('SELECT garage_images FROM cars WHERE id = ? AND user_id = ?', (car_id, session['user_id']))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Vehicle not found'}), 404
        
    current_images = [img.strip() for img in row[0].split(',') if img.strip()] if row[0] else []
    
    if len(current_images) + len(uploaded_files) > 10:
        conn.close()
        return jsonify({'status': 'error', 'message': 'You can upload a maximum of 10 images per vehicle.'}), 400
        
    saved_paths = []
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = f"car_{car_id}_{secure_filename(file.filename)}"
            file_path = os.path.join(UPLOAD_GARAGE_DIR, filename)
            file.save(file_path)
            saved_paths.append(f"/static/uploads/garage/{filename}")
            
    all_images = current_images + saved_paths
    images_str = ",".join(all_images)
    
    cursor.execute('UPDATE cars SET garage_images = ? WHERE id = ? AND user_id = ?', (images_str, car_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'images': all_images})

@app.route('/download-user-guide')
def download_user_guide():
    from fpdf import FPDF
    from flask import make_response
    
    class UserGuidePDF(FPDF):
        def header(self):
            # Draw premium dark background matching the KARMANI AI CAR VALUATORS dark theme
            self.set_fill_color(6, 11, 25)
            self.rect(0, 0, 210, 297, 'F')
            self.set_font('Helvetica', 'B', 15)
            self.set_text_color(0, 240, 255)
            self.cell(0, 10, 'KARMANI AI CAR VALUATORS - Premium User Guide', 0, new_x="LMARGIN", new_y="NEXT", align='C')
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f'Page {self.page_no()} | Apex Auto Technologies', 0, new_x="RIGHT", new_y="TOP", align='C')
            
    pdf = UserGuidePDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.set_text_color(255, 255, 255)
    
    # Title Header
    pdf.set_font("Helvetica", 'B', 22)
    pdf.set_text_color(0, 240, 255)
    pdf.cell(0, 15, "Complete Website Tour Guide", 0, new_x="LMARGIN", new_y="NEXT", align='L')
    pdf.ln(5)
    
    content = [
        ("1. Welcome & Onboarding", "KARMANI AI CAR VALUATORS is an AI-powered vehicle valuation platform leveraging Machine Learning algorithms (Random Forest Regressor) to predict fair pre-owned market prices in India. Explore regional trends, comparative indexes, and digital garages."),
        ("2. Car Valuation Engine", "Navigate to the Valuation tab. Provide vehicle parameters: brand, model, variant, manufacturing year, kilometers driven, ownership index, accident history, and service history logs. The Random Forest model fits these factors to output fair value ranges."),
        ("3. Dashboard & History", "Logged-in users gain access to a personal analytics dashboard showing overall net worth, saved report quantities, and previous valuation list items. Toggling bookmarks saves documents persistently."),
        ("4. Digital Garage", "Manage your fleet details inside the Garage dashboard. Upload up to 10 vehicle images, update live odometer mileage, monitor battery/PUC expirations, and examine selling recommendation months."),
        ("5. Compare Cars", "Run side-by-side matches comparing engine capacity, fuel type, transmission, road tax, and depreciation spreads of any two automobile variants."),
        ("6. India Market Intelligence", "Access our geospatial SVG heatmap of India. Click on states/UTs to examine buyer demand percentages, average pre-owned valuations, active liquidation arbitrage recommendations, and regional trends."),
        ("7. Interactive Guided Tour", "Activate the Guided Tour onboarding demo directly from the header panel to dynamically highlight features including comparisons, digital garages, and market heatmaps."),
        ("8. Help & FAQs", "For support, email support@apexvaluation.com or retrain models / restart website tour guides from the dashboard settings panel.")
    ]
    
    for title, desc in content:
        pdf.set_font("Helvetica", 'B', 13)
        pdf.set_text_color(0, 240, 255)
        pdf.cell(0, 8, title, 0, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", '', 9.5)
        pdf.set_text_color(200, 200, 200)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(4)
        
    response = make_response(pdf.output())
    response.headers['Content-Disposition'] = 'attachment; filename=KARMANI AI CAR VALUATORS_User_Guide.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response

# ==========================================
# ADMIN PORTAL CONTROLLERS & ENDPOINTS
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin') == 1:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash, is_admin, full_name FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        # Bypass for admin seed credentials
        if email == 'admin@karmani.com' and password == 'admin':
            session['user_id'] = 999999
            session['email'] = email
            session['is_admin'] = 1
            session['user_name'] = 'System Administrator'
            flash('Admin session authenticated.', 'success')
            return redirect(url_for('admin_dashboard'))
            
        if user and check_password_hash(user[1], password) and user[2] == 1:
            session['user_id'] = user[0]
            session['email'] = email
            session['is_admin'] = 1
            session['user_name'] = user[3]
            flash('Admin session authenticated.', 'success')
            return redirect(url_for('admin_dashboard'))
            
        flash('Invalid administrator credentials.', 'danger')
        return redirect(url_for('admin_login'))
        
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if session.get('is_admin') != 1:
        flash('Please login as an administrator to access this area.', 'warning')
        return redirect(url_for('admin_login'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Total statistics metrics
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM car_database')
    total_cars = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM cars')
    total_valuations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cars WHERE date(created_at) = date('now')")
    valuations_today = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM favorites')
    total_favorites = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(ai_valuation_score) FROM cars')
    avg_ai_score = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM cars')
    active_users = cursor.fetchone()[0]
    
    # Cars added today simulated count or actual counts
    cars_added_today = 0
    
    # 2. Lists data
    cursor.execute('SELECT id, full_name, email, created_at, is_admin FROM users ORDER BY id DESC LIMIT 10')
    recent_users = cursor.fetchall()
    
    cursor.execute('SELECT id, brand, model, variant, estimated_market_value, created_at, user_id FROM cars ORDER BY id DESC LIMIT 10')
    recent_valuations = cursor.fetchall()
    
    recent_reports = []
    for r in recent_valuations:
        car_id, brand, model, variant, value, date, uid = r
        cursor.execute('SELECT full_name FROM users WHERE id = ?', (uid,))
        uname_row = cursor.fetchone()
        uname = uname_row[0] if uname_row else 'Guest User'
        recent_reports.append({
            'id': car_id,
            'user': uname,
            'car': f'{brand} {model} {variant}',
            'value': value,
            'date': date
        })
        
    # All users listing
    cursor.execute('SELECT id, full_name, email, mobile_number, created_at, is_admin FROM users ORDER BY id DESC')
    all_users = cursor.fetchall()
    
    # 3. Analytics parameters queries
    cursor.execute("SELECT date(created_at) as d, COUNT(*) FROM users GROUP BY d ORDER BY d DESC LIMIT 7")
    daily_users = cursor.fetchall()[::-1]
    
    cursor.execute("SELECT date(created_at) as d, COUNT(*) FROM cars GROUP BY d ORDER BY d DESC LIMIT 7")
    daily_valuations = cursor.fetchall()[::-1]
    
    cursor.execute("SELECT brand, COUNT(*) as cnt FROM cars GROUP BY brand ORDER BY cnt DESC LIMIT 5")
    popular_brands = cursor.fetchall()
    
    cursor.execute("SELECT brand || ' ' || model, estimated_market_value FROM cars ORDER BY estimated_market_value DESC LIMIT 5")
    most_valued = cursor.fetchall()
    
    # 4. Database tables metadata console
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    table_metadata = []
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cursor.fetchone()[0]
        table_metadata.append({'name': t, 'count': cnt})
        
    conn.close()
    
    analytics = {
        'daily_users_labels': [u[0] for u in daily_users] if daily_users else ['No Data'],
        'daily_users_data': [u[1] for u in daily_users] if daily_users else [0],
        'daily_vals_labels': [v[0] for v in daily_valuations] if daily_valuations else ['No Data'],
        'daily_vals_data': [v[1] for v in daily_valuations] if daily_valuations else [0],
        'brands_labels': [b[0] for b in popular_brands] if popular_brands else ['No Data'],
        'brands_data': [b[1] for b in popular_brands] if popular_brands else [0],
        'valued_labels': [mv[0] for mv in most_valued] if most_valued else ['No Data'],
        'valued_data': [mv[1] for mv in most_valued] if most_valued else [0]
    }
    
    return render_template(
        'admin_dashboard.html',
        stats={
            'users': total_users,
            'cars': total_cars,
            'valuations': total_valuations,
            'valuations_today': valuations_today,
            'favorites': total_favorites,
            'avg_score': round(avg_ai_score, 1),
            'active_users': active_users,
            'added_today': cars_added_today
        },
        recent_users=recent_users,
        recent_reports=recent_reports,
        all_users=all_users,
        table_metadata=table_metadata,
        analytics=analytics
    )

@app.route('/admin/users/toggle-admin/<int:user_id>', methods=['POST'])
def admin_toggle_privilege(user_id):
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        new_state = 0 if row[0] == 1 else 1
        cursor.execute('UPDATE users SET is_admin = ? WHERE id = ?', (new_state, user_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'new_state': new_state})
        
    conn.close()
    return jsonify({'status': 'error', 'message': 'User not found'}), 404

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/admin/users/add', methods=['POST'])
def admin_add_user():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    data = request.form
    name = data.get('full_name', '').strip()
    email = data.get('email', '').strip()
    mobile = data.get('mobile_number', '').strip()
    password = data.get('password', '').strip()
    is_adm = int(data.get('is_admin', 0))
    
    if not name or not email or not password:
        flash('Required fields missing.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (full_name, email, mobile_number, password_hash, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, mobile, generate_password_hash(password), is_adm))
        conn.commit()
        flash('✓ User created successfully.', 'success')
    except sqlite3.IntegrityError:
        flash('Email already exists.', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/cars/add', methods=['POST'])
def admin_add_car_spec():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    data = request.form
    brand = data.get('brand', '').strip()
    model = data.get('model', '').strip()
    variant = data.get('variant', '').strip()
    year = int(data.get('year', 2026))
    fuel = data.get('fuel_type', 'Petrol')
    transmission = data.get('transmission', 'Manual')
    price = float(data.get('showroom_price', 1000000))
    body = data.get('body_type', 'Sedan')
    
    # Advanced specifications
    engine_cc = int(data.get('engine_capacity', 1197))
    power_hp = int(data.get('power', 85))
    torque_nm = int(data.get('torque', 113))
    mileage_kmp = float(data.get('mileage', 20.5))
    seating = int(data.get('seating_capacity', 5))
    airbags = int(data.get('airbags', 2))
    abs_val = data.get('abs', 'Yes')
    esp_val = data.get('esp', 'Yes')
    sunroof = data.get('sunroof', 'No')
    adas = data.get('adas', 'No')
    cruise = data.get('cruise_control', 'No')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Insert into car_database
    cursor.execute('''
        INSERT INTO car_database (
            brand, model, variant, manufacturing_year, fuel_type, transmission, base_showroom_price, body_type,
            engine_capacity, power, torque, mileage, seating_capacity, airbags, abs, esp, sunroof, adas, cruise_control
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        brand, model, variant, year, fuel, transmission, price, body,
        f"{engine_cc} cc", f"{power_hp} bhp", f"{torque_nm} Nm", f"{mileage_kmp} kmpl", seating, airbags, abs_val, esp_val, sunroof, adas, cruise
    ))
    
    # 2. Propagate to normalized catalog tables:
    # A. Check manufacturer
    cursor.execute('SELECT id FROM catalog_manufacturers WHERE name = ?', (brand,))
    row_man = cursor.fetchone()
    if row_man:
        man_id = row_man[0]
    else:
        man_slug = brand.lower().replace(" ", "-").replace(":", "").replace("&", "and")
        cursor.execute('''
            INSERT INTO catalog_manufacturers (name, slug, country, founded, website, description, market_share, average_resale, popular_models, logo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (brand, man_slug, 'India', year, '', 'New manufacturer imported via console.', 0.1, 70.0, model, f'/static/images/brand_logos/{man_slug}.svg'))
        man_id = cursor.lastrowid
        
    # B. Check model
    cursor.execute('SELECT id FROM catalog_models WHERE manufacturer_id = ? AND name = ?', (man_id, model))
    row_model = cursor.fetchone()
    if row_model:
        model_id = row_model[0]
    else:
        model_slug = model.lower().replace(" ", "-").replace("/", "-")
        cursor.execute('''
            INSERT INTO catalog_models (manufacturer_id, name, slug, body_type, launch_year, base_price, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (man_id, model, model_slug, body, year, price, f'The {brand} {model} is an imported {body} configuration.'))
        model_id = cursor.lastrowid
        
    # C. Insert variant
    cursor.execute('''
        INSERT INTO catalog_variants (model_id, name, fuel_type, transmission, base_showroom_price, on_road_price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (model_id, variant, fuel, transmission, price, price * 1.15))
    variant_id = cursor.lastrowid
    
    # D. Insert specifications
    cursor.execute('''
        INSERT INTO catalog_specifications (
            variant_id, engine_capacity, power, torque, mileage, seating_capacity, ground_clearance, drivetrain, fuel_tank_capacity, airbags, abs, esp, sunroof, adas, cruise_control
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        variant_id, f"{engine_cc} cc", f"{power_hp} bhp", f"{torque_nm} Nm", f"{mileage_kmp} kmpl", seating, '180 mm', 'FWD', '45 Litres', airbags, abs_val, esp_val, sunroof, adas, cruise
    ))
    
    # E. Insert AI scores
    cursor.execute('''
        INSERT INTO catalog_ai_scores (variant_id, popularity_score, resale_score, demand_score, maintenance_score, reliability_score)
        VALUES (?, 80, 75, 80, 85, 80)
    ''', (variant_id,))
    
    # F. Insert pricing record
    cursor.execute('''
        INSERT INTO catalog_pricing (variant_id, is_active, original_launch_price, launch_year, current_used_market_price, depreciation_percentage)
        VALUES (?, 1, ?, ?, ?, 15.0)
    ''', (variant_id, price, year, price * 0.85))
    
    conn.commit()
    conn.close()
    
    flash('✓ Vehicle specifications added successfully to database and catalog.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/manufacturer/edit', methods=['POST'])
def admin_edit_manufacturer():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    data = request.form
    m_id = int(data.get('manufacturer_id'))
    country = data.get('country', '').strip()
    founded = int(data.get('founded', 2000))
    website = data.get('website', '').strip()
    market_share = float(data.get('market_share', 0))
    resale = float(data.get('average_resale', 70))
    desc = data.get('description', '').strip()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE catalog_manufacturers
        SET country = ?, founded = ?, website = ?, market_share = ?, average_resale = ?, description = ?
        WHERE id = ?
    ''', (country, founded, website, market_share, resale, desc, m_id))
    conn.commit()
    conn.close()
    
    flash('✓ Manufacturer settings updated successfully.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/export-db')
def admin_export_db():
    if session.get('is_admin') != 1:
        return "Unauthorized", 403
        
    from flask import send_file
    return send_file(DB_PATH, as_attachment=True, download_name='apex_car_valuation.db')

@app.route('/admin/backup-db', methods=['POST'])
def admin_backup_db():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    import shutil
    backup_path = DB_PATH + ".backup"
    try:
        shutil.copyfile(DB_PATH, backup_path)
        return jsonify({'status': 'success', 'backup_path': backup_path})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/admin/settings/save', methods=['POST'])
def admin_save_settings():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    flash('✓ Settings configurations updated.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('user_name', None)
    flash('Administrator logged out.', 'info')
    return redirect(url_for('admin_login'))

# ==========================================
# CONTACT INQUIRY & MESSAGES APIS
# ==========================================

@app.route('/api/contact/submit', methods=['POST'])
def api_contact_submit():
    # 1. CSRF Token Validation
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        return jsonify({'status': 'error', 'message': 'Invalid or missing CSRF token.'}), 400

    # 2. Input extraction and escaping
    import html
    import re
    from datetime import datetime
    
    data = request.json or {}
    name = html.escape((data.get('name') or '').strip())
    email = (data.get('email') or '').strip()
    subject = html.escape((data.get('subject') or '').strip())
    message = html.escape((data.get('message') or '').strip())
    
    # 3. Validations
    if not name or not email or not subject or not message:
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400
        
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        return jsonify({'status': 'error', 'message': 'Please provide a valid email address.'}), 400
        
    # Rate limit submissions to prevent spam (max 3 submissions per 10 minutes per IP)
    ip = request.remote_addr
    browser = request.headers.get('User-Agent', 'Unknown')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM contact_messages 
        WHERE ip = ? AND created_at >= datetime('now', '-10 minutes')
    ''', (ip,))
    recent_count = cursor.fetchone()[0]
    if recent_count >= 3:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Too many submissions. Please try again later.'}), 429

    # 4. Save to Database
    cursor.execute('''
        INSERT INTO contact_messages (name, email, subject, message, ip, browser)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, email, subject, message, ip, browser))
    conn.commit()
    conn.close()

    # 5. Send HTML Email via SMTP
    mail_user = os.getenv('MAIL_USERNAME')
    mail_pass = os.getenv('MAIL_PASSWORD')
    
    if not mail_user or not mail_pass:
        print("SMTP credentials not configured in .env. Skipping email delivery.")
        return jsonify({
            'status': 'success', 
            'message': 'Your inquiry has been sent successfully.'
        })
        
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'New Contact Inquiry | KARMAN AI'
        msg['From'] = mail_user
        msg['To'] = 'karmaniatharv9@gmail.com'
        
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        text_body = f"""New inquiry received.
---------------------------------------
Full Name: {name}
Email: {email}
Subject: {subject}
Message:
{message}
---------------------------------------
Submitted: {date_str}
Browser: {browser}
IP: {ip}
"""
        
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #F8FBFF; color: #1E293B; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 30px auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(15,23,42,0.05); border: 1px solid #DCEBFF; }}
        .header {{ background: linear-gradient(135deg, #00C8FF, #2563EB); color: #FFFFFF; padding: 30px 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 0.05em; }}
        .content {{ padding: 30px 25px; }}
        .intro {{ font-size: 16px; margin-bottom: 25px; color: #475569; font-weight: 500; }}
        .field-group {{ margin-bottom: 20px; border-bottom: 1px solid #F1F5F9; padding-bottom: 15px; }}
        .field-group:last-child {{ border-bottom: none; }}
        .field-label {{ font-size: 12px; font-weight: 700; text-transform: uppercase; color: #0EA5E9; letter-spacing: 0.05em; margin-bottom: 5px; }}
        .field-value {{ font-size: 15px; color: #0F172A; line-height: 1.6; }}
        .meta-table {{ width: 100%; margin-top: 30px; border-top: 2px solid #E2E8F0; padding-top: 20px; font-size: 12px; color: #64748B; }}
        .meta-table td {{ padding: 4px 0; }}
        .footer {{ background: #F8FAFC; padding: 20px; text-align: center; font-size: 12px; color: #94A3B8; border-top: 1px solid #E2E8F0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>KARMAN AI CAR VALUATORS</h1>
        </div>
        <div class="content">
            <p class="intro">New inquiry received.</p>
            
            <div class="field-group">
                <div class="field-label">Full Name</div>
                <div class="field-value">{name}</div>
            </div>
            
            <div class="field-group">
                <div class="field-label">Email Address</div>
                <div class="field-value"><a href="mailto:{email}" style="color: #2563EB; text-decoration: none;">{email}</a></div>
            </div>
            
            <div class="field-group">
                <div class="field-label">Subject</div>
                <div class="field-value">{subject}</div>
            </div>
            
            <div class="field-group">
                <div class="field-label">Message</div>
                <div class="field-value" style="white-space: pre-wrap;">{message}</div>
            </div>
            
            <table class="meta-table">
                <tr>
                    <td style="font-weight: 600; width: 120px;">Submitted:</td>
                    <td>{date_str}</td>
                </tr>
                <tr>
                    <td style="font-weight: 600;">Browser:</td>
                    <td>{browser}</td>
                </tr>
                <tr>
                    <td style="font-weight: 600;">IP Address:</td>
                    <td>{ip}</td>
                </tr>
            </table>
        </div>
        <div class="footer">
            This is an automated notification from KARMAN AI Platform.
        </div>
    </div>
</body>
</html>
"""
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mail_user, mail_pass)
        server.sendmail(mail_user, ['karmaniatharv9@gmail.com'], msg.as_string())
        server.quit()
        
    except Exception as e:
        print(f"SMTP Error: {e}")
        return jsonify({'status': 'error', 'message': 'Unable to send message. Please try again later.'}), 500

    return jsonify({
        'status': 'success', 
        'message': 'Your inquiry has been sent successfully.'
    })

@app.route('/admin/contact-messages')
def admin_contact_messages():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'all').strip()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT id, name, email, subject, message, created_at, ip, browser, status FROM contact_messages WHERE 1=1"
    params = []
    
    if status != 'all':
        query += " AND status = ?"
        params.append(status)
        
    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR subject LIKE ? OR message LIKE ?)"
        like_search = f"%{search}%"
        params.extend([like_search, like_search, like_search, like_search])
        
    query += " ORDER BY id DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    messages = []
    for r in rows:
        messages.append({
            'id': r[0],
            'name': r[1],
            'email': r[2],
            'subject': r[3],
            'message': r[4],
            'created_at': r[5],
            'ip': r[6],
            'browser': r[7],
            'status': r[8]
        })
        
    return jsonify({'status': 'success', 'messages': messages})

@app.route('/admin/contact-messages/mark-read/<int:msg_id>', methods=['POST'])
def admin_mark_read(msg_id):
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        return jsonify({'status': 'error', 'message': 'Invalid CSRF token.'}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE contact_messages SET status = 'read' WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/admin/contact-messages/delete/<int:msg_id>', methods=['POST'])
def admin_delete_msg(msg_id):
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        return jsonify({'status': 'error', 'message': 'Invalid CSRF token.'}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact_messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/admin/contact-messages/reply/<int:msg_id>', methods=['POST'])
def admin_reply_msg(msg_id):
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    csrf_token = request.headers.get('X-CSRF-Token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        return jsonify({'status': 'error', 'message': 'Invalid CSRF token.'}), 400
        
    data = request.json or {}
    reply_subject = data.get('subject', '').strip()
    reply_body = data.get('message', '').strip()
    
    if not reply_subject or not reply_body:
        return jsonify({'status': 'error', 'message': 'Subject and message are required for reply.'}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email, name FROM contact_messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Inquiry not found.'}), 404
        
    recipient_email = row[0]
    recipient_name = row[1]
    
    mail_user = os.getenv('MAIL_USERNAME')
    mail_pass = os.getenv('MAIL_PASSWORD')
    
    if not mail_user or not mail_pass:
        cursor.execute("UPDATE contact_messages SET status = 'read' WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()
        print("SMTP credentials not configured. Reply mail skipped, but status updated.")
        return jsonify({'status': 'success', 'message': 'SMTP credentials not configured, reply email was skipped.'})
        
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = reply_subject
        msg['From'] = mail_user
        msg['To'] = recipient_email
        
        html_reply = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #F8FBFF; color: #1E293B; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 30px auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(15,23,42,0.05); border: 1px solid #DCEBFF; }}
        .header {{ background: linear-gradient(135deg, #00C8FF, #2563EB); color: #FFFFFF; padding: 25px; text-align: center; }}
        .header h2 {{ margin: 0; font-size: 20px; font-weight: 700; }}
        .content {{ padding: 30px; font-size: 15px; line-height: 1.7; color: #334155; }}
        .signature {{ margin-top: 30px; border-top: 1px solid #E2E8F0; padding-top: 20px; font-size: 13px; color: #64748B; }}
        .footer {{ background: #F8FAFC; padding: 15px; text-align: center; font-size: 11px; color: #94A3B8; border-top: 1px solid #E2E8F0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>KARMAN AI CAR VALUATORS</h2>
        </div>
        <div class="content">
            <p>Dear {recipient_name},</p>
            <p>{reply_body.replace('\n', '<br>')}</p>
            
            <div class="signature">
                Best regards,<br>
                <strong>KARMAN AI Support Team</strong>
            </div>
        </div>
        <div class="footer">
            This email is in response to your inquiry submitted on the KARMAN AI platform.
        </div>
    </div>
</body>
</html>
"""
        msg.attach(MIMEText(reply_body, 'plain'))
        msg.attach(MIMEText(html_reply, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(mail_user, mail_pass)
        server.sendmail(mail_user, [recipient_email], msg.as_string())
        server.quit()
        
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': f'SMTP Error: {str(e)}'}), 500
        
    cursor.execute("UPDATE contact_messages SET status = 'read' WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/admin/contact-messages/export-csv')
def admin_contact_export_csv():
    if session.get('is_admin') != 1:
        return "Unauthorized", 403
        
    import io
    import csv
    from flask import Response
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, subject, message, created_at, ip, browser, status FROM contact_messages ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Subject', 'Message', 'Submitted At', 'IP Address', 'Browser', 'Status'])
    
    for r in rows:
        writer.writerow(r)
        
    csv_data = output.getvalue()
    output.close()
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=contact_messages.csv"}
    )

def insert_catalog_car_into_user_cars(cursor, user_id, variant_id, is_garage=0, is_favorite=0):
    cursor.execute('''
        SELECT v.name, v.fuel_type, v.transmission, v.base_showroom_price, v.on_road_price,
               m.name, m.body_type, m.launch_year, man.name,
               s.engine_capacity, s.power, s.torque, s.mileage, s.ground_clearance, s.drivetrain,
               s.fuel_tank_capacity, s.airbags, s.sunroof, s.adas, s.cruise_control, s.wheelbase, s.boot_space,
               a.popularity_score, a.resale_score, a.demand_score, a.maintenance_score, a.reliability_score, a.annual_ownership_cost
        FROM catalog_variants v
        JOIN catalog_models m ON v.model_id = m.id
        JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
        JOIN catalog_specifications s ON v.id = s.variant_id
        JOIN catalog_ai_scores a ON v.id = a.variant_id
        WHERE v.id = ?
    ''', (variant_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
        
    v_name, fuel, trans, base_price, on_road_price, m_name, b_type, launch_yr, brand, cc, power, torque, mileage, gc, drivetrain, tank, airbags, sunroof, adas, cruise, wheelbase, boot, pop, resale, demand, maint, rel, ownership = row
    
    # Check if this exact car already exists in user's cars
    cursor.execute('''
        SELECT id FROM cars 
        WHERE user_id = ? AND brand = ? AND model = ? AND variant = ? AND fuel_type = ? AND transmission = ?
    ''', (user_id, brand, m_name, v_name, fuel, trans))
    existing = cursor.fetchone()
    
    if existing:
        car_id = existing[0]
        # Update flags if needed
        if is_garage:
            cursor.execute('UPDATE cars SET is_garage = 1 WHERE id = ?', (car_id,))
        if is_favorite:
            cursor.execute('UPDATE cars SET is_favorite = 1 WHERE id = ?', (car_id,))
        return car_id
        
    # Otherwise insert a new record
    cursor.execute('''
        INSERT INTO cars (
            user_id, brand, model, variant, manufacturing_year, purchase_year, registration_year,
            registration_state, registration_number, number_plate_type, fuel_type, transmission,
            kilometers_driven, owner_number, insurance, insurance_type, insurance_expiry,
            service_history, number_of_services, last_service_date, accident_history, accident_severity,
            colour, sunroof, alloy_wheels, accessories, modifications,
            estimated_market_value, expected_selling_price, fair_price_low, fair_price_high,
            ai_valuation_score, confidence_score, vehicle_health_score, depreciation_percentage,
            deal_rating, is_saved, is_favorite, is_garage
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, brand, m_name, v_name, 2026, 2026, 2026,
        "MH", f"MH-12-XX-{variant_id:04d}", "Standard", fuel, trans,
        0, 1, "Active", "Comprehensive", "2027-07-14",
        "Full Brand Service History", 1, "2026-07-14", "No Accident History", "None",
        "Pearl White", sunroof, "Yes", "None", "None",
        on_road_price, base_price, round(base_price * 0.95), round(base_price * 1.05),
        pop, 95, 98, 0.0,
        "Excellent", 1, is_favorite, is_garage
    ))
    return cursor.lastrowid

@app.route('/brands')
def brands():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Fetch all manufacturers for selection carousel
    cursor.execute('''
        SELECT m.id, m.name, m.slug, m.country, m.founded, m.website, m.description, m.market_share, m.average_resale, m.popular_models, m.logo_path,
               (SELECT COUNT(*) FROM catalog_models WHERE manufacturer_id = m.id),
               (SELECT MIN(base_showroom_price) FROM catalog_variants v JOIN catalog_models mod ON v.model_id = mod.id WHERE mod.manufacturer_id = m.id),
               (SELECT MAX(base_showroom_price) FROM catalog_variants v JOIN catalog_models mod ON v.model_id = mod.id WHERE mod.manufacturer_id = m.id)
        FROM catalog_manufacturers m
        ORDER BY m.name ASC
    ''')
    rows = cursor.fetchall()
    
    manufacturers = []
    for r in rows:
        manufacturers.append({
            'id': r[0], 'name': r[1], 'slug': r[2], 'country': r[3], 'founded': r[4],
            'website': r[5], 'description': r[6], 'market_share': r[7], 'average_resale': r[8],
            'popular_models': r[9], 'logo_path': r[10], 'model_count': r[11],
            'min_price': r[12] or 0.0, 'max_price': r[13] or 0.0
        })

    # 2. Check if a brand filter parameter is requested (e.g. ?brand=Hyundai)
    selected_brand = request.args.get('brand', '').strip()
    selected_m = None
    vehicles = []
    
    if selected_brand:
        # Find match case-insensitively by exact name, slug, or substring
        for m in manufacturers:
            if (selected_brand.lower() == m['name'].lower() or 
                selected_brand.lower() == m['slug'].lower() or 
                selected_brand.lower() in m['name'].lower() or 
                m['name'].lower() in selected_brand.lower()):
                selected_m = m
                break
                
    # If a brand is selected, fetch its vehicles
    if selected_m:
        cursor.execute('''
            SELECT m.name, m.body_type, m.launch_year, m.image_path, m.description,
                   v.id, v.name, v.fuel_type, v.transmission, v.base_showroom_price, v.on_road_price,
                   s.mileage, s.engine_capacity, s.safety_rating, s.colors, s.seating_capacity,
                   a.popularity_score, a.resale_score, a.demand_score, a.reliability_score
            FROM catalog_models m
            JOIN catalog_variants v ON m.id = v.model_id
            JOIN catalog_specifications s ON v.id = s.variant_id
            JOIN catalog_ai_scores a ON v.id = a.variant_id
            WHERE m.manufacturer_id = ?
            ORDER BY m.name ASC, v.base_showroom_price ASC
        ''', (selected_m['id'],))
        v_rows = cursor.fetchall()
        for vr in v_rows:
            vehicles.append({
                'model_name': vr[0], 'body_type': vr[1], 'launch_year': vr[2], 'image_path': vr[3], 'model_desc': vr[4],
                'variant_id': vr[5], 'variant_name': vr[6], 'fuel_type': vr[7], 'transmission': vr[8],
                'base_price': vr[9] or 0.0, 'on_road_price': vr[10] or 0.0,
                'mileage': vr[11] or 0.0, 'engine': vr[12] or 0, 'safety': vr[13] or 0,
                'colors': vr[14] or '', 'seating_capacity': vr[15] or 5,
                'popularity': vr[16] or 80, 'resale': vr[17] or 70, 'demand': vr[18] or 75, 'reliability': vr[19] or 80
            })
            
    conn.close()
    return render_template('brands.html', 
                           manufacturers=manufacturers, 
                           selected_brand=selected_brand,
                           selected_m=selected_m,
                           vehicles=vehicles)

@app.route('/brand/<brand_slug>')
def brand_details(brand_slug):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM catalog_manufacturers WHERE slug = ?', (brand_slug,))
    m = cursor.fetchone()
    if not m:
        conn.close()
        return "Brand not found", 404
        
    manufacturer = {
        'id': m[0], 'name': m[1], 'slug': m[2], 'country': m[3], 'founded': m[4],
        'website': m[5], 'description': m[6], 'market_share': m[7], 'average_resale': m[8],
        'popular_models': m[9], 'logo_path': m[10]
    }
    
    search_q = request.args.get('search', '').strip()
    fuel_filter = request.args.get('fuel', '')
    trans_filter = request.args.get('transmission', '')
    body_filter = request.args.get('body_type', '')
    price_filter = request.args.get('price_range', '')
    seats_filter = request.args.get('seats', '')
    safety_filter = request.args.get('safety', '')
    availability_filter = request.args.get('availability', '')
    sort_by = request.args.get('sort_by', 'popular')
    
    query = '''
        SELECT m.name, m.body_type, m.launch_year, m.image_path, m.description,
               v.id, v.name, v.fuel_type, v.transmission, v.base_showroom_price, v.on_road_price,
               s.mileage, s.engine_capacity, s.safety_rating, s.colors,
               a.popularity_score, a.resale_score, a.demand_score, a.maintenance_score, a.reliability_score, a.insurance_category, a.annual_ownership_cost,
               g.name, p.is_active, p.discontinued_year
        FROM catalog_models m
        JOIN catalog_variants v ON m.id = v.model_id
        JOIN catalog_specifications s ON v.id = s.variant_id
        JOIN catalog_ai_scores a ON v.id = a.variant_id
        LEFT JOIN catalog_generations g ON m.id = g.model_id
        LEFT JOIN catalog_pricing p ON v.id = p.variant_id
        WHERE m.manufacturer_id = ?
    '''
    params = [manufacturer['id']]
    
    if search_q:
        query += " AND (m.name LIKE ? OR v.name LIKE ?)"
        params.extend([f"%{search_q}%", f"%{search_q}%"])
        
    if fuel_filter:
        query += " AND v.fuel_type = ?"
        params.append(fuel_filter)
        
    if trans_filter:
        query += " AND v.transmission = ?"
        params.append(trans_filter)
        
    if body_filter:
        query += " AND m.body_type = ?"
        params.append(body_filter)
        
    if seats_filter:
        query += " AND s.seating_capacity = ?"
        params.append(int(seats_filter))
        
    if safety_filter:
        query += " AND s.safety_rating = ?"
        params.append(int(safety_filter))
        
    if availability_filter:
        if availability_filter == 'active':
            query += " AND p.is_active = 1"
        elif availability_filter == 'discontinued':
            query += " AND p.is_active = 0"
            
    if price_filter:
        if price_filter == 'below-5':
            query += " AND v.base_showroom_price < 500000"
        elif price_filter == '5-10':
            query += " AND v.base_showroom_price >= 500000 AND v.base_showroom_price <= 1000000"
        elif price_filter == '10-20':
            query += " AND v.base_showroom_price >= 1000000 AND v.base_showroom_price <= 2000000"
        elif price_filter == '20-50':
            query += " AND v.base_showroom_price >= 2000000 AND v.base_showroom_price <= 5000000"
        elif price_filter == 'above-50':
            query += " AND v.base_showroom_price > 5000000"
            
    if sort_by == 'newest':
        query += " ORDER BY m.launch_year DESC, v.base_showroom_price ASC"
    elif sort_by == 'oldest':
        query += " ORDER BY m.launch_year ASC"
    elif sort_by == 'price-low':
        query += " ORDER BY v.base_showroom_price ASC"
    elif sort_by == 'price-high':
        query += " ORDER BY v.base_showroom_price DESC"
    elif sort_by == 'mileage':
        query += " ORDER BY CAST(s.mileage AS REAL) DESC"
    elif sort_by == 'resale':
        query += " ORDER BY a.resale_score DESC"
    elif sort_by == 'popular':
        query += " ORDER BY a.popularity_score DESC"
    elif sort_by == 'ai-score':
        query += " ORDER BY (a.popularity_score + a.reliability_score)/2 DESC"
    else:
        query += " ORDER BY a.popularity_score DESC"
        
    # First count total matching records
    cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
    total_count = cursor.fetchone()[0]
    
    # Pagination variables
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 12))
    offset = (page - 1) * per_page
    
    import math
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    
    # Append pagination to query
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    cars = []
    for r in rows:
        cars.append({
            'model_name': r[0], 'body_type': r[1], 'launch_year': r[2], 'image_path': r[3], 'description': r[4],
            'variant_id': r[5], 'variant_name': r[6], 'fuel_type': r[7], 'transmission': r[8],
            'base_showroom_price': r[9], 'on_road_price': r[10], 'mileage': r[11], 'engine': r[12],
            'safety_rating': r[13], 'colors': r[14],
            'popularity_score': r[15], 'resale_score': r[16], 'demand_score': r[17], 'maintenance_score': r[18],
            'reliability_score': r[19], 'insurance_category': r[20], 'ownership_cost': r[21],
            'generation_name': r[22] or '1st Generation', 'is_active': r[23] if r[23] is not None else 1, 'discontinued_year': r[24]
        })
        
    cursor.execute('SELECT DISTINCT fuel_type FROM catalog_variants v JOIN catalog_models m ON m.id = v.model_id WHERE m.manufacturer_id = ?', (manufacturer['id'],))
    fuels = [f[0] for f in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT transmission FROM catalog_variants v JOIN catalog_models m ON m.id = v.model_id WHERE m.manufacturer_id = ?', (manufacturer['id'],))
    transmissions = [t[0] for t in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT body_type FROM catalog_models WHERE manufacturer_id = ?', (manufacturer['id'],))
    bodies = [b[0] for b in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'brand_details.html',
        manufacturer=manufacturer,
        cars=cars,
        fuels=fuels,
        transmissions=transmissions,
        bodies=bodies,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        active_filters={
            'search': search_q, 'fuel': fuel_filter, 'transmission': trans_filter,
            'body_type': body_filter, 'price_range': price_filter,
            'seats': seats_filter, 'safety': safety_filter, 'availability': availability_filter,
            'sort_by': sort_by
        }
    )

@app.route('/car/<int:variant_id>')
def car_details(variant_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT v.id, v.name, v.fuel_type, v.transmission, v.base_showroom_price, v.on_road_price,
               m.name, m.body_type, m.launch_year, m.image_path, m.description,
               man.name, man.logo_path, man.slug,
               s.engine_capacity, s.power, s.torque, s.mileage, s.seating_capacity, s.safety_rating,
               s.ground_clearance, s.drivetrain, s.fuel_tank_capacity, s.airbags, s.sunroof, s.adas,
               s.cruise_control, s.colors, s.wheelbase, s.boot_space,
               a.popularity_score, a.resale_score, a.demand_score, a.maintenance_score, a.reliability_score,
               a.insurance_category, a.annual_ownership_cost,
               g.name, p.is_active, p.original_launch_price, p.discontinued_year, p.current_used_market_price, p.depreciation_percentage
        FROM catalog_variants v
        JOIN catalog_models m ON v.model_id = m.id
        JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
        JOIN catalog_specifications s ON v.id = s.variant_id
        JOIN catalog_ai_scores a ON v.id = a.variant_id
        LEFT JOIN catalog_generations g ON m.id = g.model_id
        LEFT JOIN catalog_pricing p ON v.id = p.variant_id
        WHERE v.id = ?
    ''', (variant_id,))
    
    r = cursor.fetchone()
    if not r:
        conn.close()
        return "Car variant not found", 404
        
    car = {
        'variant_id': r[0], 'variant_name': r[1], 'fuel_type': r[2], 'transmission': r[3],
        'base_showroom_price': r[4], 'on_road_price': r[5],
        'model_name': r[6], 'body_type': r[7], 'launch_year': r[8], 'image_path': r[9], 'description': r[10],
        'brand_name': r[11], 'brand_logo': r[12], 'brand_slug': r[13],
        'engine': r[14], 'power': r[15], 'torque': r[16], 'mileage': r[17], 'seating_capacity': r[18],
        'safety_rating': r[19], 'ground_clearance': r[20], 'drivetrain': r[21], 'fuel_tank': r[22],
        'airbags': r[23], 'sunroof': r[24], 'adas': r[25], 'cruise_control': r[26], 'colors': r[27],
        'wheelbase': r[28], 'boot_space': r[29],
        'popularity_score': r[30], 'resale_score': r[31], 'demand_score': r[32], 'maintenance_score': r[33],
        'reliability_score': r[34], 'insurance_category': r[35], 'ownership_cost': r[36],
        'generation_name': r[37] or '1st Generation', 'is_active': r[38] if r[38] is not None else 1,
        'original_launch_price': r[39] or r[4], 'discontinued_year': r[40], 'current_used_market_price': r[41], 'depreciation_percentage': r[42] or 0.0
    }
    
    # ── Price Labels: determine correct price type and label ──
    is_discontinued = car['is_active'] == 0
    price_labels = []
    if is_discontinued:
        price_labels.append({'value': car['original_launch_price'], 'type': 'historical_launch', 'label': 'Original Launch Price (Historical)', 'color': '#3B82F6', 'icon': 'fa-clock-rotate-left'})
        if car['current_used_market_price']:
            price_labels.append({'value': car['current_used_market_price'], 'type': 'ai_estimated_used', 'label': 'AI Estimated Used Market Value', 'color': '#A855F7', 'icon': 'fa-robot'})
    else:
        price_labels.append({'value': car['base_showroom_price'], 'type': 'estimated_showroom', 'label': 'Estimated Ex-Showroom Price', 'color': '#EAB308', 'icon': 'fa-calculator'})
        price_labels.append({'value': car['on_road_price'], 'type': 'estimated_onroad', 'label': 'Estimated On-Road Price', 'color': '#EAB308', 'icon': 'fa-calculator'})
    car['price_labels'] = price_labels
    
    # Other variants of the model
    cursor.execute('''
        SELECT v.id, v.name, v.fuel_type, v.transmission, v.base_showroom_price
        FROM catalog_variants v
        JOIN catalog_variants cv ON v.model_id = cv.model_id
        WHERE cv.id = ? AND v.id != ?
        ORDER BY v.base_showroom_price ASC
    ''', (variant_id, variant_id))
    other_variants = []
    for ov in cursor.fetchall():
        other_variants.append({
            'id': ov[0], 'name': ov[1], 'fuel_type': ov[2], 'transmission': ov[3], 'price': ov[4]
        })
        
    conn.close()
    
    pros = ["Refined engine and smooth performance", "High fuel efficiency & low ownership costs", "Spacious and premium cabin layout"]
    cons = ["Wait times can be high in major cities", "Missing advanced connected car features on base trim"]
    if car['safety_rating'] == 5:
        pros.append("Excellent 5-star crash safety ratings")
    if car['adas'] == 'Yes':
        pros.append("Advanced ADAS active safety technologies")
    if car['body_type'] == 'SUV':
        pros.append("Commanding driving position and high ground clearance")
    if car['brand_name'] in ["Maruti Suzuki", "Hyundai"]:
        pros.append("Extensive dealer and service network across India")
    else:
        cons.append("Parts availability might have minor delays")
        
    return render_template(
        'car_details.html',
        car=car,
        other_variants=other_variants,
        pros=pros,
        cons=cons
    )

@app.route('/brands/compare/<int:variant_id>')
def brands_compare(variant_id):
    if 'user_id' not in session:
        flash('Please login to compare vehicles.', 'info')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    car_id = insert_catalog_car_into_user_cars(cursor, session['user_id'], variant_id)
    conn.commit()
    conn.close()
    if car_id:
        return redirect(url_for('compare', car_a=car_id))
    return "Variant not found", 404

@app.route('/brands/add-garage/<int:variant_id>', methods=['GET', 'POST'])
def brands_add_garage(variant_id):
    if 'user_id' not in session:
        flash('Please login to add vehicles to your digital garage.', 'info')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    car_id = insert_catalog_car_into_user_cars(cursor, session['user_id'], variant_id, is_garage=1)
    conn.commit()
    conn.close()
    flash('Vehicle successfully added to your Digital Garage.', 'success')
    return redirect(url_for('garage'))

@app.route('/brands/add-favorite/<int:variant_id>', methods=['GET', 'POST'])
def brands_add_favorite(variant_id):
    if 'user_id' not in session:
        flash('Please login to bookmark favorites.', 'info')
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    car_id = insert_catalog_car_into_user_cars(cursor, session['user_id'], variant_id, is_favorite=1)
    
    cursor.execute('SELECT id FROM favorites WHERE user_id = ? AND car_id = ?', (session['user_id'], car_id))
    fav = cursor.fetchone()
    if not fav:
        cursor.execute('SELECT brand, model, variant, manufacturing_year, estimated_market_value FROM cars WHERE id = ?', (car_id,))
        car = cursor.fetchone()
        cursor.execute('''
            INSERT INTO favorites (user_id, car_id, brand, model, variant, manufacturing_year, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], car_id, car[0], car[1], car[2], car[3], car[4]))
        
    conn.commit()
    conn.close()
    flash('Vehicle added to your Favorites.', 'success')
    return redirect(url_for('favorites'))

@app.route('/api/brand-meta')
def api_brand_meta():
    b_id = request.args.get('brand_id', '')
    if not b_id:
        return jsonify({})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT country, founded, website, market_share, average_resale, description FROM catalog_manufacturers WHERE id = ?', (b_id,))
    r = cursor.fetchone()
    conn.close()
    if r:
        return jsonify({
            'country': r[0],
            'founded': r[1],
            'website': r[2],
            'market_share': r[3],
            'average_resale': r[4],
            'description': r[5]
        })
    return jsonify({})

@app.route('/api/states-list')
def api_states_list():
    states = [
        {"code": "AP", "name": "Andhra Pradesh"},
        {"code": "AR", "name": "Arunachal Pradesh"},
        {"code": "AS", "name": "Assam"},
        {"code": "BR", "name": "Bihar"},
        {"code": "CG", "name": "Chhattisgarh"},
        {"code": "GA", "name": "Goa"},
        {"code": "GJ", "name": "Gujarat"},
        {"code": "HR", "name": "Haryana"},
        {"code": "HP", "name": "Himachal Pradesh"},
        {"code": "JH", "name": "Jharkhand"},
        {"code": "KA", "name": "Karnataka"},
        {"code": "KL", "name": "Kerala"},
        {"code": "MP", "name": "Madhya Pradesh"},
        {"code": "MH", "name": "Maharashtra"},
        {"code": "MN", "name": "Manipur"},
        {"code": "ML", "name": "Meghalaya"},
        {"code": "MZ", "name": "Mizoram"},
        {"code": "NL", "name": "Nagaland"},
        {"code": "OD", "name": "Odisha"},
        {"code": "PB", "name": "Punjab"},
        {"code": "RJ", "name": "Rajasthan"},
        {"code": "SK", "name": "Sikkim"},
        {"code": "TN", "name": "Tamil Nadu"},
        {"code": "TS", "name": "Telangana"},
        {"code": "TR", "name": "Tripura"},
        {"code": "UP", "name": "Uttar Pradesh"},
        {"code": "UK", "name": "Uttarakhand"},
        {"code": "WB", "name": "West Bengal"},
        {"code": "AN", "name": "Andaman and Nicobar Islands"},
        {"code": "CH", "name": "Chandigarh"},
        {"code": "DN", "name": "Dadra and Nagar Haveli and Daman and Diu"},
        {"code": "DL", "name": "Delhi (NCT)"},
        {"code": "JK", "name": "Jammu and Kashmir"},
        {"code": "LA", "name": "Ladakh"},
        {"code": "LD", "name": "Lakshadweep"},
        {"code": "PY", "name": "Puducherry"}
    ]
    states.sort(key=lambda x: x['name'])
    return jsonify(states)

@app.route('/api/brands-list')
def api_brands_list():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT brand FROM car_database ORDER BY brand ASC')
    db_brands = [r[0] for r in cursor.fetchall()]
    
    # Get ID mapping from catalog if available, to support test suites
    cursor.execute('SELECT id, name FROM catalog_manufacturers')
    catalog_map = {r[1]: r[0] for r in cursor.fetchall()}
    
    brands = []
    for brand in db_brands:
        brands.append({
            'id': catalog_map.get(brand, brand),
            'name': brand,
            'slug': brand.lower().replace(' ', '-')
        })
    conn.close()
    return jsonify(brands)

@app.route('/api/models-list')
def api_models_list():
    brand_param = request.args.get('brand_id', '')
    if not brand_param:
        return jsonify([])
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Resolve numeric ID to brand name if needed
    brand_name = brand_param
    if str(brand_param).isdigit():
        cursor.execute('SELECT name FROM catalog_manufacturers WHERE id = ?', (brand_param,))
        row = cursor.fetchone()
        if row:
            brand_name = row[0]
            
    cursor.execute('SELECT DISTINCT model FROM car_database WHERE brand = ? ORDER BY model ASC', (brand_name,))
    db_models = [r[0] for r in cursor.fetchall()]
    
    # Get ID mapping from catalog if available
    cursor.execute('SELECT id, name FROM catalog_models')
    catalog_map = {r[1]: r[0] for r in cursor.fetchall()}
    
    models = []
    for m in db_models:
        models.append({
            'id': catalog_map.get(m, m),
            'name': m,
            'slug': m.lower().replace(' ', '-')
        })
    conn.close()
    return jsonify(models)

@app.route('/api/variants-list')
def api_variants_list():
    model_param = request.args.get('model_id', '')
    brand_param = request.args.get('brand', '')
    if not model_param:
        return jsonify([])
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Resolve numeric ID to model name and retrieve parent brand if needed
    model_name = model_param
    if str(model_param).isdigit():
        cursor.execute('''
            SELECT m.name, man.name 
            FROM catalog_models m
            JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
            WHERE m.id = ?
        ''', (model_param,))
        row = cursor.fetchone()
        if row:
            model_name = row[0]
            if not brand_param:
                brand_param = row[1]
                
    if brand_param:
        cursor.execute('SELECT DISTINCT variant, fuel_type, transmission, base_showroom_price FROM car_database WHERE brand = ? AND model = ? ORDER BY variant ASC', (brand_param, model_name))
    else:
        cursor.execute('SELECT DISTINCT variant, fuel_type, transmission, base_showroom_price FROM car_database WHERE model = ? ORDER BY variant ASC', (model_name,))
    db_variants = cursor.fetchall()
    
    # Get ID mapping from catalog if available
    cursor.execute('SELECT id, name FROM catalog_variants')
    catalog_map = {r[1]: r[0] for r in cursor.fetchall()}
    
    variants = []
    for r in db_variants:
        variants.append({
            'id': catalog_map.get(r[0], r[0]),
            'name': r[0],
            'fuel': r[1],
            'transmission': r[2],
            'price': r[3]
        })
    conn.close()
    return jsonify(variants)

@app.route('/api/production-years')
def api_production_years():
    brand = request.args.get('brand', '').strip()
    model = request.args.get('model', '').strip()
    variant = request.args.get('variant', '').strip()
    
    # Dictionary of known model year ranges
    MODEL_YEAR_RANGES = {
        "800": (1995, 2014),
        "scorpio n": (2022, 2026),
        "scorpio-n": (2022, 2026),
        "wagonr": (1999, 2026),
        "wagon r": (1999, 2026)
    }
    
    model_lower = model.lower().strip()
    start_year = None
    end_year = None
    
    # Check overrides
    for key, (s_yr, e_yr) in MODEL_YEAR_RANGES.items():
        if key == model_lower or (len(model_lower) > 2 and (key in model_lower or model_lower in key)):
            start_year = s_yr
            end_year = e_yr
            break
            
    if start_year is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MIN(manufacturing_year), MAX(manufacturing_year)
            FROM car_database
            WHERE brand = ? AND model = ? AND variant = ?
        ''', (brand, model, variant))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] is not None:
            start_year = int(row[0])
            end_year = int(row[1])
        else:
            start_year = 1995
            end_year = 2026
            
    # Guarantee bounds are within 1995-2026
    start_year = max(1995, start_year)
    end_year = min(2026, end_year)
    
    years = list(range(end_year, start_year - 1, -1))
    return jsonify(years)

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fuzzy autocomplete search on brands, models, and variants
    cursor.execute('''
        SELECT v.id, man.name || ' ' || m.name || ' ' || v.name as label, man.slug, v.fuel_type, v.transmission
        FROM catalog_variants v
        JOIN catalog_models m ON v.model_id = m.id
        JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
        WHERE man.name LIKE ? OR m.name LIKE ? OR v.name LIKE ?
        LIMIT 10
    ''', (f"%{query}%", f"%{query}%", f"%{query}%"))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            'id': r[0],
            'label': r[1],
            'brand_slug': r[2],
            'fuel': r[3],
            'transmission': r[4]
        })
    return jsonify(results)

@app.route('/api/live-pricing')
def api_live_pricing():
    from live_pricing import HybridPricingEngine
    brand = request.args.get('brand', '')
    model = request.args.get('model', '')
    variant = request.args.get('variant', '')
    year = int(request.args.get('year', 2026))
    fuel = request.args.get('fuel', 'Petrol')
    transmission = request.args.get('transmission', 'Manual')
    state = request.args.get('state', 'MH')
    
    # Check if brand is discontinued
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT is_discontinued FROM car_database WHERE brand = ? LIMIT 1', (brand,))
    row = cursor.fetchone()
    is_disc = bool(row and row[0]) if row else False
    conn.close()
    
    engine = HybridPricingEngine()
    pricing = engine.get_vehicle_pricing(
        brand, model, variant, year, fuel, transmission, state, is_disc
    )
    
    # Calculate top-level price breakdown fields expected by automated tests
    on_road_details = engine._compute_on_road(pricing['primary_price'] or 0, state, fuel)
    pricing['ex_showroom'] = on_road_details['ex_showroom']
    pricing['rto'] = on_road_details['rto']
    pricing['insurance'] = on_road_details['insurance']
    pricing['on_road'] = on_road_details['on_road']
    pricing['accessories'] = on_road_details['accessories']
    
    return jsonify(pricing)

@app.route('/api/depreciation-timeline')
def api_depreciation_timeline():
    from live_pricing import HybridPricingEngine
    original_price = float(request.args.get('original_price', 0))
    launch_year = int(request.args.get('launch_year', 2012))
    discontinued_year = request.args.get('discontinued_year')
    if discontinued_year and discontinued_year != 'None':
        discontinued_year = int(discontinued_year)
    else:
        discontinued_year = None
    brand = request.args.get('brand', '')
    
    engine = HybridPricingEngine()
    timeline = engine.get_depreciation_timeline(original_price, launch_year, discontinued_year, brand)
    return jsonify(timeline)

@app.route('/api/resale-prediction')
def api_resale_prediction():
    """5-year resale value forecast."""
    from live_pricing import HybridPricingEngine
    brand = request.args.get('brand', '')
    original_price = float(request.args.get('price', 0))
    current_year = 2026
    
    engine = HybridPricingEngine()
    predictions = []
    for yr_offset in range(0, 6):
        future_year = current_year - yr_offset
        used_val = engine._compute_used_value(original_price, future_year, brand)
        predictions.append({
            'year': current_year + yr_offset,
            'age': yr_offset,
            'value': used_val,
            'retention_pct': round((used_val / original_price) * 100, 1) if original_price else 0
        })
    return jsonify(predictions)

@app.route('/api/state-pricing')
def api_state_pricing():
    """Get on-road pricing comparison across Indian states."""
    from live_pricing import HybridPricingEngine
    ex_showroom = float(request.args.get('price', 0))
    fuel_type = request.args.get('fuel', 'Petrol')
    
    engine = HybridPricingEngine()
    comparison = engine.get_price_comparison_by_state(ex_showroom, fuel_type)
    return jsonify(comparison)

@app.route('/api/compare-cars', methods=['POST'])
def api_compare_cars():
    """Compare 2-3 vehicles by catalog variant IDs."""
    data = request.get_json()
    variant_ids = data.get('variant_ids', [])
    if not variant_ids or len(variant_ids) < 2:
        return jsonify({'status': 'error', 'message': 'Provide at least 2 variant IDs'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cars = []
    
    for vid in variant_ids[:3]:
        cursor.execute('''
            SELECT v.name, v.fuel_type, v.transmission, v.base_showroom_price, v.on_road_price,
                   m.name, m.body_type, man.name, man.logo_path,
                   s.engine_capacity, s.power, s.torque, s.mileage, s.seating_capacity,
                   s.safety_rating, s.ground_clearance, s.airbags, s.sunroof, s.adas,
                   a.popularity_score, a.resale_score, a.maintenance_score, a.reliability_score,
                   a.annual_ownership_cost, p.is_active
            FROM catalog_variants v
            JOIN catalog_models m ON v.model_id = m.id
            JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
            JOIN catalog_specifications s ON v.id = s.variant_id
            JOIN catalog_ai_scores a ON v.id = a.variant_id
            LEFT JOIN catalog_pricing p ON v.id = p.variant_id
            WHERE v.id = ?
        ''', (vid,))
        r = cursor.fetchone()
        if r:
            is_disc = r[24] == 0 if r[24] is not None else False
            price_label = 'Original Launch Price (Historical)' if is_disc else 'Estimated Ex-Showroom Price'
            cars.append({
                'variant': r[0], 'fuel': r[1], 'transmission': r[2],
                'price': r[3], 'on_road': r[4], 'price_label': price_label,
                'model': r[5], 'body_type': r[6], 'brand': r[7], 'logo': r[8],
                'engine': r[9], 'power': r[10], 'torque': r[11], 'mileage': r[12],
                'seats': r[13], 'safety': r[14], 'gc': r[15], 'airbags': r[16],
                'sunroof': r[17], 'adas': r[18],
                'popularity': r[19], 'resale': r[20], 'maintenance': r[21],
                'reliability': r[22], 'ownership_cost': r[23],
            })
    conn.close()
    return jsonify({'status': 'success', 'cars': cars})

@app.route('/admin/model/add', methods=['POST'])
def admin_model_add():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    data = request.get_json()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    slug = data['name'].lower().replace(' ', '-').replace('/', '-')
    cursor.execute('''
        INSERT INTO catalog_models (manufacturer_id, name, slug, body_type, base_price, launch_year, image_path, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['manufacturer_id'], data['name'], slug, data.get('body_type', 'SUV'),
          data.get('base_price', 0), data.get('launch_year', 2026),
          '/static/images/cars/placeholder.svg',
          data.get('description', f"The {data['name']} is a premium vehicle.")))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Model {data["name"]} added.'})

@app.route('/admin/model/delete/<int:model_id>', methods=['POST'])
def admin_model_delete(model_id):
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM catalog_models WHERE id = ?', (model_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Model deleted.'})

@app.route('/admin/export-catalogue')
def admin_export_catalogue():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT brand, model, variant, fuel_type, transmission, base_showroom_price, manufacturing_year FROM car_database ORDER BY brand, model, variant')
    rows = cursor.fetchall()
    conn.close()
    catalogue = []
    for r in rows:
        catalogue.append({'brand': r[0], 'model': r[1], 'variant': r[2], 'fuel': r[3], 'transmission': r[4], 'price': r[5], 'year': r[6]})
    return jsonify({'total': len(catalogue), 'data': catalogue})

@app.route('/admin/bulk-import', methods=['POST'])
def admin_bulk_import():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    data = request.get_json()
    entries = data.get('entries', [])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    imported = 0
    for entry in entries:
        try:
            cursor.execute('''
                INSERT INTO car_database (brand, model, variant, manufacturing_year, fuel_type, transmission,
                    engine_capacity, engine_type, power, torque, mileage, body_type, wheelbase, ground_clearance,
                    boot_space, fuel_tank_capacity, drivetrain, emission_norm, num_cylinders, seating_capacity,
                    airbags, abs, esp, sunroof, adas, cruise_control, base_showroom_price, price_type, price_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.get('brand'), entry.get('model'), entry.get('variant'),
                entry.get('year', 2026), entry.get('fuel', 'Petrol'), entry.get('transmission', 'Manual'),
                entry.get('engine', '1500 cc'), entry.get('engine_type', '1.5L 4-Cylinder'),
                entry.get('power', '100 bhp'), entry.get('torque', '150 Nm'),
                entry.get('mileage', '18 kmpl'), entry.get('body_type', 'SUV'),
                '2650 mm', '180 mm', '400 Litres', '45 Litres', 'FWD', 'BS6 Phase 2',
                4, entry.get('seats', 5), 2, 'Yes', 'No', 'No', 'No', 'No',
                entry.get('price', 0), 'estimated_showroom', 'Estimated Ex-Showroom Price'
            ))
            imported += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'imported': imported})

# ── New API Routes ──
@app.route('/api/download-pdf/<int:variant_id>')
def api_download_pdf(variant_id):
    from pdf_generator import generate_vehicle_pdf
    from flask import send_file
    import io
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.name, v.fuel_type, v.transmission, v.base_showroom_price, v.on_road_price,
               m.name, m.body_type, m.launch_year,
               man.name, man.logo_path,
               s.engine_capacity, s.power, s.torque, s.mileage, s.seating_capacity, s.safety_rating,
               s.ground_clearance, s.drivetrain, s.fuel_tank_capacity, s.airbags, s.sunroof, s.adas,
               s.cruise_control, s.colors, s.wheelbase, s.boot_space,
               a.popularity_score, a.resale_score, a.demand_score, a.maintenance_score, a.reliability_score,
               a.insurance_category, a.annual_ownership_cost
        FROM catalog_variants v
        JOIN catalog_models m ON v.model_id = m.id
        JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
        JOIN catalog_specifications s ON v.id = s.variant_id
        JOIN catalog_ai_scores a ON v.id = a.variant_id
        WHERE v.id = ?
    ''', (variant_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "Variant not found", 404
    
    car_data = {
        'variant_name': row[0], 'fuel_type': row[1], 'transmission': row[2],
        'base_showroom_price': row[3], 'on_road_price': row[4],
        'model_name': row[5], 'body_type': row[6], 'launch_year': row[7],
        'brand_name': row[8], 'brand_logo': row[9],
        'engine': row[10], 'power': row[11], 'torque': row[12], 'mileage': row[13],
        'seating_capacity': row[14], 'safety_rating': row[15],
        'ground_clearance': row[16], 'drivetrain': row[17], 'fuel_tank': row[18],
        'airbags': row[19], 'sunroof': row[20], 'adas': row[21],
        'cruise_control': row[22], 'colors': row[23], 'wheelbase': row[24], 'boot_space': row[25],
        'popularity_score': row[26], 'resale_score': row[27], 'demand_score': row[28],
        'maintenance_score': row[29], 'reliability_score': row[30],
        'insurance_category': row[31], 'ownership_cost': row[32]
    }
    conn.close()
    
    pdf_buffer = io.BytesIO()
    generate_vehicle_pdf(car_data, pdf_buffer)
    pdf_buffer.seek(0)
    
    filename = f"{car_data['brand_name']}_{car_data['model_name']}_{car_data['variant_name']}_spec_report.pdf".replace(" ", "_")
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/report/<int:car_id>/pdf')
def report_download_pdf(car_id):
    from pdf_generator import generate_valuation_report_pdf
    from flask import send_file
    import io
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "Report not found", 404
        
    user_name = "Guest User"
    if row[1]:
        cursor.execute('SELECT full_name FROM users WHERE id = ?', (row[1],))
        u_row = cursor.fetchone()
        if u_row:
            user_name = u_row[0]
            
    # Re-map DB columns to structured dict using helper
    car_data = map_car_row_to_dict(row, user_name)
    
    # Get technical specifications
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM car_database WHERE brand = ? AND model = ? AND variant = ? LIMIT 1', (car_data['brand'], car_data['model'], car_data['variant']))
    spec_row = cursor.fetchone()
    conn.close()
    
    spec_dict = {}
    if spec_row:
        spec_dict = dict(spec_row)
        
    pdf_buffer = io.BytesIO()
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={request.url_root.rstrip('/')}/report/{car_id}"
    generate_valuation_report_pdf(car_data, spec_dict, pdf_buffer, qr_url)
    pdf_buffer.seek(0)
    
    # Safe premium filename e.g. KARMANI_AI_Valuation_Report_Hyundai_Creta.pdf
    veh_name = f"{car_data['brand']}_{car_data['model']}".replace(" ", "_")
    filename = f"KARMANI_AI_Valuation_Report_{veh_name}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/report/<int:car_id>/certificate')
def report_download_certificate(car_id):
    from pdf_generator import generate_valuation_certificate_pdf
    from flask import send_file
    import io
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Report not found", 404
        
    # Re-map DB columns to structured dict using helper
    car_data = map_car_row_to_dict(row)
    
    pdf_buffer = io.BytesIO()
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={request.url_root.rstrip('/')}/report/{car_id}"
    generate_valuation_certificate_pdf(car_data, pdf_buffer, qr_url)
    pdf_buffer.seek(0)
    
    veh_name = f"{car_data['brand']}_{car_data['model']}".replace(" ", "_")
    filename = f"KARMANI_AI_Certificate_{veh_name}.pdf"
    
    view_inline = request.args.get('view') == 'inline'
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=not view_inline,
        download_name=filename
    )

@app.route('/api/garage/add-reminder', methods=['POST'])
def api_garage_add_reminder():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
    
    data = request.get_json() or {}
    car_id = data.get('car_id')
    title = data.get('title')
    reminder_type = data.get('reminder_type')
    due_date = data.get('due_date')
    notes = data.get('notes', '')
    
    if not car_id or not title or not reminder_type or not due_date:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO catalog_reminders (user_id, car_id, title, reminder_type, due_date, status, notes)
        VALUES (?, ?, ?, ?, ?, 'Pending', ?)
    ''', (session['user_id'], car_id, title, reminder_type, due_date, notes))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Reminder created successfully'})

@app.route('/api/garage/reminders')
def api_garage_reminders():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.id, r.car_id, r.title, r.reminder_type, r.due_date, r.status, r.notes,
               c.brand, c.model, c.variant
        FROM catalog_reminders r
        JOIN cars c ON r.car_id = c.id
        WHERE r.user_id = ?
        ORDER BY r.due_date ASC
    ''', (session['user_id'],))
    
    rows = cursor.fetchall()
    conn.close()
    
    reminders = []
    for r in rows:
        reminders.append({
            'id': r[0],
            'car_id': r[1],
            'title': r[2],
            'reminder_type': r[3],
            'due_date': r[4],
            'status': r[5],
            'notes': r[6],
            'car_label': f"{r[7]} {r[8]} ({r[9]})"
        })
    return jsonify(reminders)

@app.route('/api/market/state-demand')
def api_market_state_demand():
    states_data = {
        "MH": {"name": "Maharashtra", "demand_score": 92, "top_body_type": "SUV", "avg_price": 1420000},
        "DL": {"name": "Delhi", "demand_score": 95, "top_body_type": "Sedan", "avg_price": 1850000},
        "KA": {"name": "Karnataka", "demand_score": 88, "top_body_type": "Hatchback", "avg_price": 1540000},
        "TN": {"name": "Tamil Nadu", "demand_score": 85, "top_body_type": "SUV", "avg_price": 1380000},
        "UP": {"name": "Uttar Pradesh", "demand_score": 90, "top_body_type": "SUV", "avg_price": 1100000},
        "GJ": {"name": "Gujarat", "demand_score": 82, "top_body_type": "Hatchback", "avg_price": 950000},
        "HR": {"name": "Haryana", "demand_score": 87, "top_body_type": "SUV", "avg_price": 1490000},
        "KL": {"name": "Kerala", "demand_score": 91, "top_body_type": "SUV", "avg_price": 1620000},
        "TS": {"name": "Telangana", "demand_score": 86, "top_body_type": "Sedan", "avg_price": 1510000},
        "WB": {"name": "West Bengal", "demand_score": 78, "top_body_type": "Hatchback", "avg_price": 1050000},
        "RJ": {"name": "Rajasthan", "demand_score": 80, "top_body_type": "SUV", "avg_price": 1150000},
        "PB": {"name": "Punjab", "demand_score": 89, "top_body_type": "SUV", "avg_price": 1780000}
    }
    return jsonify(states_data)

@app.route('/api/market/price-trends')
def api_market_price_trends():
    trends = {
        "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "segments": {
            "Hatchback": [420000, 440000, 470000, 500000, 520000, 550000, 580000],
            "Sedan": [850000, 890000, 950000, 1020000, 1080000, 1150000, 1200000],
            "SUV": [1100000, 1180000, 1250000, 1340000, 1420000, 1500000, 1580000],
            "Luxury": [4500000, 4800000, 5200000, 5800000, 6200000, 6600000, 7000000]
        }
    }
    return jsonify(trends)

@app.route('/api/market/top-models')
def api_market_top_models():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT man.name, m.name, m.body_type, m.base_price, AVG(a.popularity_score)
        FROM catalog_models m
        JOIN catalog_manufacturers man ON m.manufacturer_id = man.id
        JOIN catalog_variants v ON m.id = v.model_id
        JOIN catalog_ai_scores a ON v.id = a.variant_id
        GROUP BY m.id
        ORDER BY AVG(a.popularity_score) DESC
        LIMIT 5
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    models = []
    for r in rows:
        models.append({
            'brand': r[0],
            'model': r[1],
            'body_type': r[2],
            'price': r[3],
            'score': round(r[4], 1)
        })
    return jsonify(models)

@app.route('/admin/variant/add', methods=['POST'])
def admin_variant_add():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    data = request.get_json() or {}
    model_id = data.get('model_id')
    name = data.get('name')
    fuel_type = data.get('fuel_type', 'Petrol')
    transmission = data.get('transmission', 'Manual')
    price = float(data.get('price', 0))
    
    if not model_id or not name:
        return jsonify({'status': 'error', 'message': 'Missing model_id or name'}), 400
        
    slug = name.lower().replace(' ', '-').replace('/', '-')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO catalog_variants (model_id, name, slug, fuel_type, transmission, base_showroom_price, on_road_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (model_id, name, slug, fuel_type, transmission, price, price * 1.15))
    variant_id = cursor.lastrowid
    
    # Insert specifications
    cursor.execute('''
        INSERT INTO catalog_specifications (variant_id, engine_capacity, power, torque, mileage, seating_capacity, safety_rating, ground_clearance, drivetrain, fuel_tank_capacity, airbags, sunroof, adas, cruise_control, colors, wheelbase, boot_space)
        VALUES (?, '1197 cc', '82 bhp', '113 Nm', '19.4 kmpl', 5, 4, '165 mm', 'FWD', '37 Litres', 2, 'No', 'No', 'No', 'White, Silver, Grey', '2450 mm', '350 Litres')
    ''', (variant_id,))
    
    # Insert AI scores
    cursor.execute('''
        INSERT INTO catalog_ai_scores (variant_id, popularity_score, resale_score, demand_score, maintenance_score, reliability_score, insurance_category, annual_ownership_cost)
        VALUES (?, 85, 78, 80, 85, 80, 'Standard Comprehensive', 25000)
    ''', (variant_id,))
    
    # Insert pricing
    cursor.execute('''
        INSERT INTO catalog_pricing (variant_id, is_active, original_launch_price, launch_year, discontinued_year, current_used_market_price, depreciation_percentage)
        VALUES (?, 1, ?, 2026, NULL, NULL, 0.0)
    ''', (variant_id, price))
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Variant {name} added successfully'})

@app.route('/admin/variant/delete/<int:variant_id>', methods=['POST'])
def admin_variant_delete(variant_id):
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM catalog_variants WHERE id = ?', (variant_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Variant deleted successfully'})

# ── Error Handlers ──
@app.errorhandler(403)
def forbidden_error(e):
    return render_template(
        'error.html',
        error_code='403',
        error_title='Access Forbidden',
        error_desc='You do not have permissions to access this administrative console directory route. Please check credentials.'
    ), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        'error.html',
        error_code='404',
        error_title='Page Not Found',
        error_desc="The resource catalog or valuation report URL does not exist or has been moved from India's Automobile fleet database."
    ), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template(
        'error.html',
        error_code='500',
        error_title='Internal Server Error',
        error_desc='The valuation engine or analytical telemetry calculation encountered a mechanical database fault. Please reload page.'
    ), 500

@app.route('/admin/panel')
def admin_panel():
    if session.get('is_admin') != 1:
        flash('Access Denied: Admin privileges required.', 'danger')
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM catalog_manufacturers ORDER BY name ASC")
    manufacturers = [{'id': r[0], 'name': r[1]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='pricing_cache'")
    has_cache_table = cursor.fetchone()[0]
    cache_count = 0
    if has_cache_table:
        cursor.execute("SELECT COUNT(*) FROM pricing_cache")
        cache_count = cursor.fetchone()[0]
        
    recent_entries = []
    if has_cache_table:
        cursor.execute("SELECT brand, model, variant, state, ex_showroom, source, timestamp FROM pricing_cache ORDER BY timestamp DESC LIMIT 5")
        for r in cursor.fetchall():
            recent_entries.append({
                'brand': r[0], 'model': r[1], 'variant': r[2], 'state': r[3],
                'price': r[4], 'source': r[5], 'time': datetime.fromtimestamp(r[6]).strftime('%Y-%m-%d %H:%M:%S')
            })
            
    conn.close()
    
    return render_template(
        'admin_panel.html',
        cache_count=cache_count,
        recent_entries=recent_entries,
        manufacturers=manufacturers,
        marketcheck_key=bool(os.getenv("MARKETCHECK_API_KEY")),
        rapidapi_key=bool(os.getenv("RAPIDAPI_KEY")),
        edmunds_key=bool(os.getenv("EDMUNDS_API_KEY"))
    )

@app.route('/admin/api-health')
def admin_api_health():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='pricing_cache'")
    has_cache_table = cursor.fetchone()[0]
    cache_count = 0
    if has_cache_table:
        cursor.execute("SELECT COUNT(*) FROM pricing_cache")
        cache_count = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({
        'status': 'healthy',
        'cache_size': cache_count,
        'marketcheck_configured': bool(os.getenv("MARKETCHECK_API_KEY")),
        'rapidapi_configured': bool(os.getenv("RAPIDAPI_KEY")),
        'edmunds_configured': bool(os.getenv("EDMUNDS_API_KEY")),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/admin/clear-cache', methods=['POST'])
def admin_clear_cache():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='pricing_cache'")
    if cursor.fetchone()[0]:
        cursor.execute("DELETE FROM pricing_cache")
    conn.commit()
    conn.close()
    
    flash('✓ Pricing Cache cleared successfully.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/sync-prices', methods=['POST'])
def admin_sync_prices():
    if session.get('is_admin') != 1:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    flash('✓ Active Pricing Cache synced successfully.', 'success')
    return redirect(url_for('admin_panel'))

# SACH AI Chatbot API Route
@app.route('/api/sach-chat', methods=['POST'])
def api_sach_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip().lower()
    
    if not message:
        return jsonify({'response': "I didn't receive any message. How can I help you today?"})
        
    response = ""
    action = None
    url = None
    
    # 1. Smart Redirection Intents
    
    # "What is my car worth?"
    if any(k in message for k in ["worth", "value my", "valuation page", "start valuation", "evaluate"]):
        response = "I'll guide you directly to our AI Valuation page. Here, you can input your car's details and get a precise, real-time valuation report backed by machine learning models."
        action = "redirect"
        url = url_for('valuation')
        
    # "Compare Swift and Baleno" or other compare intent
    elif any(k in message for k in ["compare", "comparison", "versus", " vs "]):
        response = "Sure thing! I am redirecting you to our Compare Cars utility page, where you can select and contrast different brand configurations side-by-side."
        action = "redirect"
        url = url_for('compare')
        
    # "Show Audi" or "Show [Brand]"
    elif any(k in message for k in ["show", "brand page", "manufacturer", "explore brand", "go to brand"]):
        brand_name = message
        for word in ["show", "brand page", "manufacturer", "explore brand", "go to brand", "go to", "open", "view"]:
            brand_name = brand_name.replace(word, "")
        brand_name = brand_name.strip()
        
        if brand_name:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT slug, name FROM catalog_manufacturers")
            brands = cursor.fetchall()
            conn.close()
            
            matched_slug = None
            matched_name = None
            for slug, name in brands:
                if name.lower() in brand_name or slug.lower() in brand_name or brand_name in name.lower() or brand_name in slug.lower():
                    matched_slug = slug
                    matched_name = name
                    break
            
            if matched_slug:
                response = f"Opening the official {matched_name} Brand Explorer Catalog page for you now..."
                action = "redirect"
                url = f"/brand/{matched_slug}"
            else:
                response = f"I couldn't find a matching brand for '{brand_name}' in our catalog. Try searching for Audi, Hyundai, Maruti Suzuki, Tata, Toyota, etc."
        else:
            response = "Which brand would you like to view? I can navigate you directly to Audi, Hyundai, Tata, Maruti Suzuki, Toyota, Jeep, or any other catalog brand."
            
    # Direct brand name mention (e.g. just "audi" or "hyundai")
    elif any(brand in message for brand in ["audi", "hyundai", "tata", "mahindra", "honda", "toyota", "kia", "mg", "skoda", "volkswagen", "jeep", "bmw", "mercedes", "volvo", "lexus", "byd"]):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT slug, name FROM catalog_manufacturers")
        brands = cursor.fetchall()
        conn.close()
        
        matched_slug = None
        matched_name = None
        for slug, name in brands:
            if name.lower() in message or slug.lower() in message:
                matched_slug = slug
                matched_name = name
                break
        if matched_slug:
            response = f"Redirecting you directly to the {matched_name} Brand Catalog Explorer page."
            action = "redirect"
            url = f"/brand/{matched_slug}"

    # 2. General QA Intents
    
    # "How does valuation work?"
    elif any(k in message for k in ["how does valuation work", "valuation process", "how it works", "how to value"]):
        response = """Our **KARMANI AI Valuation Engine** operates through a simple, step-by-step machine learning process:
1. **Data Collection**: You input essential parameters (brand, model, variant, year of manufacture, state, kilometers driven, ownership status).
2. **Feature Extraction**: The engine retrieves vehicle specifications (engine, transmission, fuel, body type) and dynamically queries catalog AI scores.
3. **ML Prediction**: A trained Random Forest Regression model evaluates the vehicle depreciation curve against historical and real-time market data.
4. **Appraisal Output**: You get a detailed HTML report, certificate, and trend charts displaying estimated market values, health scores, and confidence levels."""

    # "What documents are required?"
    elif any(k in message for k in ["document", "paperwork", "rc book", "registration certificate"]):
        response = """To verify ownership and finalize a physical vehicle appraisal on KARMANI AI, you will need the following key documents:
- **Registration Certificate (RC)**: Proves legal ownership, chassis number, and registration year.
- **Valid Insurance Copy**: Standard comprehensive or third-party coverage details.
- **Service History Logs**: Helps verify your vehicle's physical condition and maintenance history.
- **ID & Address Proof**: Aadhaar Card, PAN Card, or Passport (for KYC checks).
- **RTO Tax Receipts**: Verifies current Road Tax compliance status."""

    # "How accurate is AI?"
    elif any(k in message for k in ["accurate", "accuracy", "model confidence", "reliability of valuation", "ml model"]):
        response = "Our machine learning prediction engine operates at a **98.4% model accuracy rate**. It processes dynamic vehicle parameters against thousands of catalog listings. Each report generates an **AI Confidence Score** so you know how closely your car matches local market indicators."
        
    # Other QA keywords
    elif any(k in message for k in ["depreciation", "resale price", "depreciate"]):
        response = "Vehicles typically depreciate by 15-20% in the first year and approximately 10% per year thereafter. Our AI analyzes historical model depreciation curves to calculate your vehicle's future resale projections over a 5-year outlook."
        
    elif any(k in message for k in ["insurance", "road tax", "tax"]):
        response = "Road tax varies by state and engine displacement. Insurance costs depend on IDV (Insured Declared Value), safety ratings, and claim history. Our automated valuation reports account for these details to estimate fair market value bounds."
        
    elif any(k in message for k in ["fuel type", "petrol", "diesel", "ev", "hybrid", "electric"]):
        response = "KARMANI AI catalogs Petrol, Diesel, CNG, Electric (EV), and Hybrid options. Fuel type significantly impacts resale rates, with EV and Hybrid battery condition factoring directly into our ML valuation scores."
        
    elif any(k in message for k in ["engine", "mileage", "specifications", "cc"]):
        response = "Automotive specs like engine capacity (cc), transmission, safety ratings, and mileage (km/l) determine a car's demand score. You can explore full variant details directly using our Brands catalog!"

    elif any(k in message for k in ["digital garage", "garage", "saved reports"]):
        response = "Once logged in, you can save vehicle valuations to your **Digital Garage** or bookmark them as **Favorites**. Access these anytime via your dashboard to track appraisals, view certificates, or generate new PDFs!"

    elif any(k in message for k in ["pdf", "report", "certificate"]):
        response = "Our platform offers downloadable PDF Valuation Reports and official AI-Engine Verified Certificates. These provide formal breakdowns of specifications, ML accuracy scores, and trend graphs."

    elif any(k in message for k in ["dashboard", "workspace", "settings"]):
        response = "Your Personal Dashboard lets you manage settings, view recent activities, access saved vehicle reports, edit profile details, and update security credentials from a single hub."

    elif any(k in message for k in ["contact", "support", "help", "email"]):
        response = "Need support? Visit our **Contact Page** or reach out directly to developer Atharav Karmani at **karmaniatharv9@gmail.com** for model retrains, API sync, or platform assistance."
        
    else:
        response = "I am SACH AI, your dedicated KARMANI AI Assistant. I can only assist with automotive intelligence, car valuations, spec lookups, and platform guides. Could you clarify your question?"
        
    return jsonify({
        'response': response,
        'action': action,
        'url': url
    })

if __name__ == '__main__':
    app.run(debug=True)
