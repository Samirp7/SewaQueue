from flask import Flask, render_template, request, redirect, url_for
import pymysql

app = Flask(__name__)

# Database Configuration Configuration
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",  # Kept empty based on your local database configuration setup
        database="sewa_queue_db",
        cursorclass=pymysql.cursors.DictCursor
    )

# 📱 Route 1: Citizen Entry Form Screen
@app.route('/')
def citizen_portal():
    return render_template('citizen.html')

# 🎟️ Action Route: Generate Next Digital Token
@app.route('/issue-token', methods=['POST'])
def issue_token():
    phone = request.form['phone']
    service_id = int(request.form['service_id'])
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Fetch service specifications and prefix rules
            cursor.execute("SELECT service_prefix FROM services WHERE id = %s", (service_id,))
            service = cursor.fetchone()
            prefix = service['service_prefix']
            
            # 2. Count current group volume to increment token sequential digit
            cursor.execute("SELECT COUNT(*) as total FROM tokens WHERE service_id = %s", (service_id,))
            count = cursor.fetchone()['total']
            token_number = f"{prefix}-{101 + count}"
            
            # 3. Insert fresh token log into pipeline
            cursor.execute(
                "INSERT INTO tokens (token_number, citizen_phone, service_id) VALUES (%s, %s, %s)",
                (token_number, phone, service_id)
            )
        connection.commit()
    finally:
        connection.close()
        
    return f"""
    <div style="font-family:sans-serif; text-align:center; padding:50px; background:#f8fafc; min-height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center;">
        <div style="background:white; padding:40px; border-radius:20px; box-shadow:0 10px 25px -5px rgba(0,0,0,0.1); max-w:400px; width:100%;">
            <h2 style="color:#0f172a; margin-bottom:5px;">Token Issued Successfully!</h2>
            <p style="color:#64748b; font-size:14px; margin-top:0;">Please note your number or take a screenshot.</p>
            <div style="font-size:64px; font-weight:900; color:#2563eb; font-family:monospace; margin:30px 0; letter-spacing:2px;">{token_number}</div>
            <p style="color:#475569; font-size:14px;">Proceed to the main hall waiting lounge area.</p>
            <a href="/" style="display:inline-block; margin-top:20px; padding:12px 24px; background:#2563eb; color:white; text-decoration:none; font-weight:600; border-radius:10px; font-size:14px;">Go Back</a>
        </div>
    </div>
    """

# 🖥️ Route 2: Live Department Hall Matrix Display Board
@app.route('/monitor')
def monitor_display():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Gather state configs for every active desk counter locations
            cursor.execute("""
                SELECT c.counter_number, c.officer_name, 
                       (SELECT t.token_number FROM tokens t 
                        WHERE t.counter_id = c.id AND t.status = 'Serving' 
                        ORDER BY t.updated_at DESC LIMIT 1) AS current_token
                FROM counters c
            """)
            active_counters = cursor.fetchall()
    finally:
        connection.close()
    return render_template('monitor.html', active_counters=active_counters)

# 💼 Route 3: Internal Counter Officer Interface Control Room
@app.route('/officer')
def officer_portal():
    current_counter = int(request.args.get('counter_id', 1))
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. Fetch pending tokens currently waiting in line
            cursor.execute("""
                SELECT t.token_number, t.citizen_phone, s.service_name 
                FROM tokens t 
                JOIN services s ON t.service_id = s.id 
                WHERE t.status = 'Pending' 
                ORDER BY t.created_at ASC
            """)
            pending_tokens = cursor.fetchall()
    finally:
        connection.close()
    return render_template('officer.html', current_counter=current_counter, pending_tokens=pending_tokens)

# 🔄 Action Route: Dropdowns Counter Selection Event Handler
@app.route('/select-counter', methods=['POST'])
def select_counter():
    counter_id = request.form['counter_id']
    return redirect(url_for('officer_portal', counter_id=counter_id))

from twilio.rest import Client  # Add this import at the very top of your app.py file

# Twilio API Credentials (Use sandbox placeholders for local testing)
TWILIO_ACCOUNT_SID = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
TWILIO_AUTH_TOKEN = "your_auth_token_here"
TWILIO_PHONE_NUMBER = "+1234567890"  # Your assigned Twilio trial number

@app.route('/call-next', methods=['POST'])
def call_next():
    counter_id = int(request.form['counter_id'])
    connection = get_db_connection()
    sms_sent = False
    alert_phone = None
    alert_token = None
    
    try:
        with connection.cursor() as cursor:
            # 1. Complete the current token active at this counter
            cursor.execute(
                "UPDATE tokens SET status = 'Completed' WHERE counter_id = %s AND status = 'Serving'",
                (counter_id,)
            )
            
            # 2. Grab the oldest pending token, its phone number, and service details
            cursor.execute("""
                SELECT t.id, t.token_number, t.citizen_phone, s.service_name 
                FROM tokens t
                JOIN services s ON t.service_id = s.id
                WHERE t.status = 'Pending' 
                ORDER BY t.created_at ASC, t.id ASC LIMIT 1
            """)
            next_token = cursor.fetchone()
            
            # 3. If someone is waiting, assign them to this counter and activate them
            if next_token:
                token_id = next_token['id']
                alert_token = next_token['token_number']
                alert_phone = next_token['citizen_phone']
                service_name = next_token['service_name']
                
                cursor.execute(
                    "UPDATE tokens SET status = 'Serving', counter_id = %s WHERE id = %s",
                    (counter_id, token_id)
                )
        connection.commit()
        
        # 4. Trigger the External SMS Gateway API outside the DB lock
        if alert_phone and alert_token:
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=f"SewaQueue Alert: Token {alert_token} for {service_name} is now being served at Counter {counter_id}. Please proceed inside immediately.",
                    from_=TWILIO_PHONE_NUMBER,
                    to=alert_phone  # Sends directly to the number they typed at the kiosk!
                )
                sms_sent = True
                print(f"📡 API Success: Dispatched SMS alert to {alert_phone}")
            except Exception as e:
                # If credentials are placeholders, print it to the console gracefully without crashing the app
                print(f"⚠️ SMS Gateway Simulation: Text would send to {alert_phone}. Error: {e}")

    finally:
        connection.close()
    return redirect(url_for('officer_portal', counter_id=counter_id))

if __name__ == '__main__':
    app.run(debug=True, port=5000)