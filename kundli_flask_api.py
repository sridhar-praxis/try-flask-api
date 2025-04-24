from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import pytz
import swisseph as swe
import numpy as np
from geopy.geocoders import Nominatim

app = Flask(__name__)
CORS(app)

fallback_locations = {
    "Bangalore, India": (12.9716, 77.5946),
    "Chennai, India": (13.0827, 80.2707),
    "Delhi, India": (28.6139, 77.2090),
    "Mumbai, India": (19.0760, 72.8777),
    "Kolkata, India": (22.5726, 88.3639),
}

def get_coordinates(city, country):
    key = f"{city.strip()}, {country.strip()}"
    try:
        geolocator = Nominatim(user_agent="kundli-api")
        loc = geolocator.geocode(key, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
        elif key in fallback_locations:
            return fallback_locations[key]
        else:
            return None, None
    except:
        return fallback_locations.get(key, (None, None))

def get_planet_positions(dt, city, country):
    utc_dt = dt.astimezone(pytz.utc)
    jd = swe.utc_to_jd(utc_dt.year, utc_dt.month, utc_dt.day,
                       utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600)

    lat, lon = get_coordinates(city, country)
    if lat is None:
        return {"error": "Could not resolve location"}

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    delta = 0.88
    ayan = swe.get_ayanamsa_ut(jd[1])
    hous = swe.houses(jd[1], lat, lon, b'P')
    apos = hous[0][0] - ayan + delta - 1.0
    if apos < 0:
        apos += 360

    graha = ['Lagna']
    graha_pos = [apos]
    formatted = []

    Q = int(apos / 30)
    D = int(apos % 30)
    M = int((apos % 1) * 60)
    formatted.append(f"{Q}s {D}d {M}m")

    for i in np.arange(13):
        graham = swe.get_planet_name(i)
        pos, err = swe.calc(jd[1], i)
        pos = pos[0] - ayan + delta - 1.0
        if pos < 0:
            pos += 360

        if graham == 'true Node':
            ketu_pos = (pos + 180) % 360
            Q = int(ketu_pos / 30)
            D = int(ketu_pos % 30)
            M = int((ketu_pos % 1) * 60)
            graha.append("Ketu")
            graha_pos.append(ketu_pos)
            formatted.append(f"{Q}s {D}d {M}m")
            graham = "Rahu"

        graha.append(graham)
        graha_pos.append(pos)
        Q = int(pos / 30)
        D = int(pos % 30)
        M = int((pos % 1) * 60)
        formatted.append(f"{Q}s {D}d {M}m")

    return {
        "graha": graha,
        "longitude": graha_pos,
        "formatted": formatted
    }

@app.route('/api/kundli', methods=['POST'])
def kundli_api():
    try:
        data = request.get_json()
        dt = datetime.strptime(f"{data['dob']} {data['tob']}", "%Y-%m-%d %H:%M:%S")
        dt = pytz.timezone("Asia/Kolkata").localize(dt)
        result = get_planet_positions(dt, data['city'], data['country'])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(port=5000)
