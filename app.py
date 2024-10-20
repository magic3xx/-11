from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///licenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    expiration_date = db.Column(db.DateTime, nullable=False)
    subscription_type = db.Column(db.String(20), nullable=False)
    support_name = db.Column(db.String(50))
    device_id = db.Column(db.String(50))
    activated = db.Column(db.Boolean, default=False)
    key_type = db.Column(db.String(20), nullable=False)

@app.route('/')
def index():
    licenses = License.query.all()
    return render_template('index.html', licenses=licenses)

@app.route('/add', methods=['POST'])
def add_license():
    key = request.form['key']
    days = int(request.form['days'])
    hours = int(request.form['hours'])
    subscription_type = request.form['subscription_type']
    support_name = request.form['support_name']
    key_type = request.form['key_type']

    expiration_date = datetime.now() + timedelta(days=days, hours=hours)

    if subscription_type == "1 Week":
        expiration_date += timedelta(weeks=1)
    elif subscription_type == "1 Month":
        expiration_date += timedelta(weeks=4)
    elif subscription_type == "3 Months":
        expiration_date += timedelta(weeks=12)
    elif subscription_type == "6 Months":
        expiration_date += timedelta(weeks=24)
    elif subscription_type == "1 Year":
        expiration_date += timedelta(weeks=52)

    new_license = License(
        key=key,
        expiration_date=expiration_date,
        subscription_type=subscription_type,
        support_name=support_name,
        key_type=key_type
    )

    db.session.add(new_license)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/list_licenses', methods=['GET'])
def list_licenses():
    licenses = License.query.all()
    return jsonify([{
        'key': license.key,
        'active': license.active,
        'expiration_date': license.expiration_date.isoformat(),
        'subscription_type': license.subscription_type,
        'device_id': license.device_id,
        'activated': license.activated
    } for license in licenses])

@app.route('/reset_key', methods=['POST'])
def reset_key():
    key = request.form['key']
    license = License.query.filter_by(key=key).first()
    if license:
        license.device_id = None
        license.activated = False
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/toggle_active/<int:id>')
def toggle_active(id):
    license = License.query.get(id)
    if license:
        license.active = not license.active
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_license(id):
    license = License.query.get(id)
    if license:
        db.session.delete(license)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/check_key_details', methods=['POST'])
def check_key_details():
    data = request.json
    key = data.get('key')
    device_id = data.get('device_id')

    license = License.query.filter_by(key=key).first()
    if license:
        if license.activated and license.device_id != device_id:
            return jsonify({'valid': False, 'reason': 'This key is already used on another device.'})

        if not license.activated:
            license.device_id = device_id
            license.activated = True
            db.session.commit()

        if license.active and license.expiration_date > datetime.now():
            remaining_time = license.expiration_date - datetime.now()
            remaining_minutes = (remaining_time.days * 24 * 60) + (remaining_time.seconds // 60)

            return jsonify({
                'valid': True,
                'expiration_date': license.expiration_date.strftime('%Y-%m-%d'),
                'subscription_type': license.subscription_type,
                'support_name': license.support_name,
                'remaining_time': {
                    'days': remaining_time.days,
                    'hours': remaining_time.seconds // 3600,
                    'minutes': remaining_minutes % 60
                }
            })
        else:
            return jsonify({'valid': False, 'reason': 'The key is either inactive or expired.'})

    return jsonify({'valid': False, 'reason': 'Key not found.'})

# Entry point for uWSGI
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Remove the app.run() line

# Expose the app for uWSGI
app = app
