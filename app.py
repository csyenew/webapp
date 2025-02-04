from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

# Initialize Flask, SQLAlchemy, and Migrate
app = Flask(__name__)
app.config.from_object('config.Config')  # Make sure to have a 'Config' class in your config module
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define the HealthCheck model
class HealthCheck(db.Model):
    __tablename__ = 'health_check'
    check_id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Home page route
@app.route('/')
def home():
    return "Welcome to the Health Check API"

# Health check route
@app.route('/healthz', methods=['GET'])
def health_check():
    if request.content_length and request.content_length > 0:
        return jsonify({'error': 'Bad Request'}), 400
    
    try:
        # Insert a health check record
        health_check = HealthCheck()
        db.session.add(health_check)
        db.session.commit()
        
        return jsonify({'status': 'healthy'}), 200  # Include content in the response
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Service Unavailable'}), 503

# Error handling for method not allowed
@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method Not Allowed'}), 405

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
