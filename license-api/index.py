"""
Main Flask app for license API
"""
from flask import Flask, request, jsonify
import json
import os
import psycopg2

app = Flask(__name__)

@app.route('/api/webhook/gumroad', methods=['POST'])
def gumroad_webhook():
    """Receive purchase notifications from Gumroad"""
    try:
        # Get form data from Gumroad webhook
        data = request.form.to_dict()
        
        # Extract purchase info
        email = data.get('email')
        product_name = data.get('product_name', '')
        sale_id = data.get('sale_id')
        license_key = data.get('license_key')  # Gumroad generates this
        
        if not email or not license_key:
            return jsonify({"error": "Missing email or license_key"}), 400
        
        # Determine license type from product name
        license_type = 'annual' if 'annual' in product_name.lower() else 'monthly'
        
        # Connect to Supabase
        conn = psycopg2.connect(
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            dbname=os.environ.get('DB_NAME')
        )
        
        cursor = conn.cursor()
        
        # Calculate expiration date
        from datetime import datetime, timedelta
        if license_type == 'annual':
            expires_at = datetime.utcnow() + timedelta(days=365)
        else:  # monthly
            expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Insert new license (or update if exists)
        cursor.execute("""
            INSERT INTO licenses (
                purchase_email, 
                license_key, 
                license_type, 
                is_active, 
                max_devices, 
                device_ids,
                expires_at,
                created_at,
                gumroad_sale_id
            ) VALUES (%s, %s, %s, %s, %s, ARRAY[]::text[], %s, NOW(), %s)
            ON CONFLICT (license_key) 
            DO UPDATE SET 
                purchase_email = EXCLUDED.purchase_email,
                is_active = EXCLUDED.is_active,
                expires_at = EXCLUDED.expires_at,
                gumroad_sale_id = EXCLUDED.gumroad_sale_id
        """, (email, license_key, license_type, True, 1, expires_at, sale_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "License created successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/activate', methods=['POST'])
def activate():
    """Activate license with email and license type"""
    try:
        data = request.get_json()
        email = data.get('email')
        license_type = data.get('license_type', 'monthly')
        
        if not email:
            return jsonify({"error": "Missing email"}), 400
        
        # Connect to Supabase
        conn = psycopg2.connect(
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            dbname=os.environ.get('DB_NAME')
        )
        
        cursor = conn.cursor()
        
        # Check if there's an active license for this email
        cursor.execute("""
            SELECT license_key, license_type, expires_at, is_active
            FROM licenses
            WHERE purchase_email = %s AND license_type = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (email, license_type))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({
                "success": False,
                "message": "No license found for this email and license type"
            }), 404
        
        license_key, lic_type, expires_at, is_active = result
        
        if not is_active:
            return jsonify({
                "success": False,
                "message": "License is not active"
            }), 403
        
        return jsonify({
            "success": True,
            "license_key": license_key,
            "license_type": lic_type,
            "expires_at": str(expires_at) if expires_at else None,
            "message": "License activated successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        
        # Check expiration
        if expires_at:
            from datetime import datetime, timezone
            try:
                # PostgreSQL returns timezone-aware datetime
                now_utc = datetime.now(timezone.utc)
                # If expires_at is naive, make it UTC-aware
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                
                if now_utc > expires_at:
                    cursor.close()
                    conn.close()
                    return jsonify({
                        "valid": False,
                        "message": "License has expired. Please renew your subscription."
                    })
            except Exception as exp_error:
                # If expiration check fails, log and continue (don't block valid licenses)
                print(f"Expiration check error: {exp_error}")
                pass
        
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
        import traceback
        error_details = traceback.format_exc()
        print(f"Validation error: {str(e)}")
        print(f"Traceback: {error_details}")
        return jsonify({"valid": False, "message": f"Validation error: {str(e)}"}), 500


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


@app.route('/api/ping', methods=['POST'])
def ping():
    """Track anonymous usage - called when app opens"""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id', 'unknown')
        app_version = data.get('app_version', 'unknown')
        action = data.get('action', 'app_open')
        platform = data.get('platform', 'unknown')
        details = data.get('details')
        
        # Connect to Supabase
        conn = psycopg2.connect(
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            dbname=os.environ.get('DB_NAME')
        )
        
        cursor = conn.cursor()

        # 1) Append-only event stream (best-effort)
        # This table might not exist in older deployments; ignore failures.
        try:
            cursor.execute(
                """
                INSERT INTO app_usage_events (device_id, app_version, action, platform, created_at, details)
                VALUES (%s, %s, %s, %s, NOW(), %s::jsonb)
                """,
                (device_id, app_version, action, platform, json.dumps(details) if details is not None else None),
            )
        except Exception:
            # Keep legacy behavior even if the events table isn't there.
            pass
        
        # Insert usage record (upsert - update if same device today)
        cursor.execute("""
            INSERT INTO app_usage (device_id, app_version, action, platform, created_at, last_seen)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (device_id) 
            DO UPDATE SET 
                app_version = EXCLUDED.app_version,
                action = EXCLUDED.action,
                last_seen = NOW(),
                open_count = COALESCE(app_usage.open_count, 0) + 1
        """, (device_id, app_version, action, platform))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True})
        
    except Exception as e:
        # Never fail on ping - just return success
        print(f"Ping error (non-fatal): {e}")
        return jsonify({"success": True})


@app.route('/api/ping/debug/last', methods=['GET'])
def ping_debug_last():
    """Debug helper to inspect recent telemetry events.

    Returns 200 with a list when app_usage_events exists; otherwise returns an empty list.
    Never throws.
    """
    try:
        limit = int(request.args.get('limit', '50'))
        limit = max(1, min(limit, 500))

        conn = psycopg2.connect(
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            dbname=os.environ.get('DB_NAME')
        )
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT device_id, app_version, action, platform, created_at
                FROM app_usage_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall() or []
        except Exception:
            rows = []

        cursor.close()
        conn.close()

        events = []
        for r in rows:
            events.append({
                "device_id": r[0],
                "app_version": r[1],
                "action": r[2],
                "platform": r[3],
                "created_at": str(r[4])
            })
        return jsonify({"success": True, "events": events})
    except Exception as e:
        print(f"ping_debug_last error (non-fatal): {e}")
        return jsonify({"success": True, "events": []})


if __name__ == '__main__':
    app.run()