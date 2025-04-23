from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import os

app = Flask(__name__, static_folder='public')
CORS(app)

# MySQL connection
con = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="user"
)
cursor = con.cursor(dictionary=True)

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    child_id INT,
    parent_email VARCHAR(100),
    month INT,
    q1 VARCHAR(10),
    q2 VARCHAR(10),
    q3 VARCHAR(10),
    q4 VARCHAR(10),
    q5 VARCHAR(10),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS children (
    id INT AUTO_INCREMENT PRIMARY KEY,
    parent_email VARCHAR(100),
    child_name VARCHAR(100),
    dob DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
con.commit()

@app.route('/')
@app.route('/login.html')
def serve_login():
    return send_from_directory('public', 'login.html')

@app.route('/signup.html')
def serve_signup():
    return send_from_directory('public', 'signup.html')

@app.route('/dashboard.html')
def serve_dashboard():
    return send_from_directory('public', 'dashboard.html')

@app.route('/questionnaire.html')
def serve_questionnaire():
    return send_from_directory('public', 'questionnaire.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.form
    cursor.execute("SELECT * FROM std_login WHERE email = %s AND password = %s", (data['email'], data['password']))
    user = cursor.fetchone()
    if user:
        return jsonify({
            'success': True,
            'redirectTo': '/dashboard.html',
            'parentEmail': user['email'],
            'parentName': user['username']
        })
    return jsonify({'success': False, 'error': 'Incorrect Email and/or Password!'}), 401

@app.route('/signup', methods=['POST'])
def signup():
    data = request.form
    if data['password'] != data['confirm-password']:
        return 'Passwords do not match!'
    cursor.execute("INSERT INTO std_login (username, email, password) VALUES (%s, %s, %s)",
                   (data['username'], data['email'], data['password']))
    con.commit()
    return f"User registered successfully with ID: {cursor.lastrowid}"

@app.route('/submit-questionnaire', methods=['POST'])
def submit_questionnaire():
    data = request.form
    answers = [data.get(f'q{i}') for i in range(1, 6)]
    cursor.execute('''
        INSERT INTO questionnaire_responses (child_id, parent_email, month, q1, q2, q3, q4, q5)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (data['childId'], data['parent_email'], data['month'], *answers))
    con.commit()
    return f"<h2>Thank you! Your Month {data['month']} responses have been saved successfully.</h2>"

@app.route('/get-children')
def get_children():
    parentEmail = request.args.get('parentEmail')
    if not parentEmail:
        return jsonify({'error': 'Parent email required'}), 400
    cursor.execute("SELECT * FROM children WHERE parent_email = %s", (parentEmail,))
    return jsonify({'children': cursor.fetchall()})

@app.route('/add-children', methods=['POST'])
def add_children():
    data = request.json
    parentEmail = data.get('parentEmail')
    children = data.get('children')
    if not parentEmail or not children:
        return jsonify({'error': 'Invalid input data.'}), 400
    values = [(parentEmail, c['childName'], c['dob']) for c in children]
    cursor.executemany("INSERT INTO children (parent_email, child_name, dob) VALUES (%s, %s, %s)", values)
    con.commit()
    return jsonify({'message': 'Children added successfully!', 'inserted': cursor.rowcount})

@app.route('/get-progress')
def get_progress():
    childId = request.args.get('childId')
    if not childId:
        return jsonify({'error': 'Child ID is required'}), 400
    cursor.execute("SELECT DISTINCT month FROM questionnaire_responses WHERE child_id = %s", (childId,))
    return jsonify({'submittedMonths': [row['month'] for row in cursor.fetchall()]})

@app.route('/get-answers')
def get_answers():
    childId = request.args.get('childId')
    month = request.args.get('month')
    if not childId or not month:
        return jsonify({'error': 'childId and month are required'}), 400
    cursor.execute('''
        SELECT q1, q2, q3, q4, q5 FROM questionnaire_responses
        WHERE child_id = %s AND month = %s ORDER BY submitted_at DESC LIMIT 1
    ''', (childId, month))
    result = cursor.fetchone()
    return jsonify({'answers': result if result else None})

@app.route('/get-autism-score')
def get_autism_score():
    childId = request.args.get('childId')
    if not childId:
        return jsonify({'error': 'childId is required'}), 400
    cursor.execute("SELECT q1, q2, q3, q4, q5 FROM questionnaire_responses WHERE child_id = %s", (childId,))
    results = cursor.fetchall()
    yesCount = sum(row[q].lower() == 'yes' for row in results for q in ['q1', 'q2', 'q3', 'q4', 'q5'] if row[q])
    totalQuestions = sum(1 for row in results for q in ['q1', 'q2', 'q3', 'q4', 'q5'] if row[q])
    score = round((yesCount / totalQuestions) * 10) if totalQuestions else 0
    return jsonify({'score': score})

if __name__ == '__main__':
    app.run(debug=True, port=3001)