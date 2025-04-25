from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import pytz
import swisseph as swe
import numpy as np
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

app = Flask(__name__)
CORS(app)

def get_timezone_name(lat, lon):
    tf = TimezoneFinder()
    return tf.timezone_at(lat=lat, lng=lon)

def get_coordinates(city, country):
    try:
        geolocator = Nominatim(user_agent="kundli-api")
        loc = geolocator.geocode(f"{city.strip()}, {country.strip()}", timeout=10)
        if loc:
            return loc.latitude, loc.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Geocoding failed: {e}")
        return None, None


def get_planet_positions(dt, city, country):
    lat, lon = get_coordinates(city, country)
    if lat is None:
        return {"error": "Could not resolve location"}

    # Convert to UTC from local timezone of the given location
    tz_name = get_timezone_name(lat, lon)
    if not tz_name:
        return {"error": f"Could not determine timezone for {city}, {country}"}

    local_tz = pytz.timezone(tz_name)
    local_dt = local_tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)

    jd = swe.utc_to_jd(utc_dt.year, utc_dt.month, utc_dt.day,
                       utc_dt.hour, utc_dt.minute, utc_dt.second)

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

        Q = int(pos / 30)
        D = int(pos % 30)
        M = int((pos % 1) * 60)
        graha.append(graham)
        graha_pos.append(pos)
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
        result = get_planet_positions(dt, data['city'], data['country'])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(port=5000)
