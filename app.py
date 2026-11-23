from functools import wraps
from pathlib import Path
import sqlite3
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

BASE = Path(__file__).resolve().parent
DB = BASE / 'hw13.db'
app = Flask(__name__)
app.secret_key = 'classroom-demo-change-this-key'


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def initialize():
    with connect() as db:
        db.executescript((BASE / 'schema.sql').read_text(encoding='utf-8'))
        if db.execute('SELECT COUNT(*) FROM students').fetchone()[0] == 0 and db.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0] == 0:
            sid = db.execute('INSERT INTO students (first_name, last_name) VALUES (?, ?)', ('John', 'Smith')).lastrowid
            qid = db.execute('INSERT INTO quizzes (subject, questions, quiz_date) VALUES (?, ?, ?)', ('Python Basics', 5, '2015-02-05')).lastrowid
            db.execute('INSERT INTO results (student_id, quiz_id, score) VALUES (?, ?, ?)', (sid, qid, 85))


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'password':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Incorrect username or password.')
    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    with connect() as db:
        students = db.execute('SELECT * FROM students ORDER BY id').fetchall()
        quizzes = db.execute('SELECT * FROM quizzes ORDER BY id').fetchall()
    return render_template('dashboard.html', students=students, quizzes=quizzes)


@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        first = request.form.get('first_name', '').strip()
        last = request.form.get('last_name', '').strip()
        if first and last:
            with connect() as db:
                db.execute('INSERT INTO students (first_name, last_name) VALUES (?, ?)', (first, last))
            return redirect(url_for('dashboard'))
        flash('Please enter both first and last name.')
    return render_template('student_add.html')


@app.route('/quiz/add', methods=['GET', 'POST'])
@login_required
def add_quiz():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        try:
            questions = int(request.form.get('questions', ''))
            quiz_date = date.fromisoformat(request.form.get('quiz_date', ''))
            if not subject or questions < 1:
                raise ValueError()
        except ValueError:
            flash('Enter a subject, a positive number of questions, and a valid date.')
        else:
            with connect() as db:
                db.execute('INSERT INTO quizzes (subject, questions, quiz_date) VALUES (?, ?, ?)', (subject, questions, quiz_date.isoformat()))
            return redirect(url_for('dashboard'))
    return render_template('quiz_add.html')


@app.route('/student/<int:id>')
@login_required
def student_results(id):
    with connect() as db:
        student = db.execute('SELECT * FROM students WHERE id = ?', (id,)).fetchone()
        if student is None:
            abort(404)
        results = db.execute('''SELECT quiz_id, score FROM results WHERE student_id = ? ORDER BY quiz_id''', (id,)).fetchall()
    return render_template('student_results.html', student=student, results=results)


@app.route('/results/add', methods=['GET', 'POST'])
@login_required
def add_result():
    with connect() as db:
        students = db.execute('SELECT * FROM students ORDER BY last_name').fetchall()
        quizzes = db.execute('SELECT * FROM quizzes ORDER BY id').fetchall()
        if request.method == 'POST':
            try:
                sid = int(request.form.get('student_id', ''))
                qid = int(request.form.get('quiz_id', ''))
                score = int(request.form.get('score', ''))
                if not 0 <= score <= 100:
                    raise ValueError()
                db.execute('INSERT INTO results (student_id, quiz_id, score) VALUES (?, ?, ?)', (sid, qid, score))
            except (ValueError, sqlite3.IntegrityError):
                flash('Choose a valid student and quiz, and a score from 0 to 100. Duplicate results are not allowed.')
            else:
                return redirect(url_for('dashboard'))
    return render_template('result_add.html', students=students, quizzes=quizzes)


initialize()

if __name__ == '__main__':
    app.run(debug=True)
