"""
Main Flask app for license API
"""
from flask import Flask, request, jsonify
import json
import os
import psycopg2

app = Flask(__name__)

@app.route('/api/validate', methods=['GET', 'POST'])
def validate():
    """Validate license and register device"""
    try:
        # Handle both GET and POST requests
        if request.method == 'POST':
            data = request.get_json()
            license_key = data.get('license_key')
            device_id = data.get('device_id')
        else:
            license_key = request.args.get('license_key')
            device_id = request.args.get('device_id')
        
        if not license_key or not device_id:
            return jsonify({"error": "Missing license_key or device_id"}), 400
        
        # Connect to Supabase
        conn = psycopg2.connect(
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            dbname=os.environ.get('DB_NAME')
        )
        
        cursor = conn.cursor()
        
        # Check if license exists and is active
        cursor.execute("""
            SELECT id, device_ids, max_devices, is_active, license_type, expires_at
            FROM licenses
            WHERE license_key = %s
        """, (license_key,))
        
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return jsonify({
                "valid": False,
                "message": "Invalid license key"
            })
        
        license_id, device_ids_json, max_devices, is_active, license_type, expires_at = result
        
        if not is_active:
            cursor.close()
            conn.close()
            return jsonify({
                "valid": False,
                "message": "License is not active"
            })
        
        # Parse device IDs - PostgreSQL might return as string or list
        if isinstance(device_ids_json, str):
            device_ids = json.loads(device_ids_json) if device_ids_json else []
        elif isinstance(device_ids_json, list):
            device_ids = device_ids_json
        else:
            device_ids = []
        
        # Check if device is already registered
        if device_id in device_ids:
            cursor.execute("""
                INSERT INTO license_usage (license_key, device_id, last_validated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (license_key, device_id) 
                DO UPDATE SET last_validated = NOW()
            """, (license_key, device_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                "valid": True,
                "license_type": license_type,
                "message": "License validated"
            })
        
        # Check device limit
        if len(device_ids) >= max_devices:
            cursor.close()
            conn.close()
            return jsonify({
                "valid": False,
                "message": f"Device limit reached ({max_devices} devices maximum)"
            })
        
        # Add new device
        device_ids.append(device_id)
        cursor.execute("""
            UPDATE licenses
            SET device_ids = %s::text[]
            WHERE license_key = %s
        """, (device_ids, license_key))
        
        cursor.execute("""
            INSERT INTO license_usage (license_key, device_id, last_validated)
            VALUES (%s, %s, NOW())
        """, (license_key, device_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "valid": True,
            "license_type": license_type,
            "message": "Device registered successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/version')
def version():
    """Get latest app version"""
    try:
        conn = psycopg2.connect(
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            dbname=os.environ.get('DB_NAME')
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT version, release_date, download_url, changelog, is_required
            FROM app_versions
            WHERE is_latest = TRUE
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({
                "latest_version": "1.0.0",
                "message": "No updates available"
            })
        
        version, release_date, download_url, changelog, is_required = result
        
        return jsonify({
            "latest_version": version,
            "release_date": str(release_date),
            "download_url": download_url,
            "changelog": changelog,
            "is_required": is_required
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run()