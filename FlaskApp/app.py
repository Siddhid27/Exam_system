from flask import Flask, render_template, request, redirect, session, url_for,flash 
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'exam_secret'

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'siddhi'
app.config['MYSQL_DB'] = 'exam_system'

mysql = MySQL(app)

# ============================== Home
@app.route('/')
def home():
    return render_template('index.html')

# ============================== Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        if role == 'student':
            cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
            student = cursor.fetchone()
            if student and student['password'] == password:
                session['id'] = student['id']
                session['role'] = 'student'
                session['name'] = student['name']
                session['loggedin'] = True
                print(f"Student Logged In: {session['name']}")  # Debugging
                return redirect('/student_dashboard')
            else:
                flash('Invalid credentials for student. Please try again.', 'error')

        elif role == 'teacher':
            cursor.execute("SELECT * FROM teachers WHERE email=%s", (email,))
            teacher = cursor.fetchone()
            if teacher and teacher['password'] == password:
                session['id'] = teacher['id']
                session['role'] = 'teacher'
                session['name'] = teacher['name']  # Store teacher's name
                session['subject_id'] = teacher['subject_id']
                session['loggedin'] = True
                print(f"Teacher Logged In: {session['name']}")  # Debugging
                return redirect('/teacher_dashboard')
            else:
                flash('Invalid credentials for teacher. Please try again.', 'error')

        else:
            flash('Invalid role selected. Please choose either student or teacher.', 'error')

    return render_template('login.html')


# ============================== Student Dashboard
@app.route("/student_dashboard")
def student_dashboard():
    if "id" not in session or session["role"] != "student":
        return redirect("/login")

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM subjects")
    subjects = cursor.fetchall()

    subjects_with_tests = []
    for subject in subjects:
        cursor.execute("SELECT * FROM tests WHERE subject_id = %s AND is_published = 1", (subject["id"],))
        tests = cursor.fetchall()
        subjects_with_tests.append({"id": subject["id"], "name": subject["name"], "tests": tests})

    cursor.close()
    return render_template("student_dashboard.html", subjects=subjects_with_tests)

# ============================== Teacher Dashboard
@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'role' in session and session['role'] == 'teacher':
        teacher_id = session['id']
        subject_id = session['subject_id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch teacher's name
        cursor.execute("SELECT name FROM teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()
        teacher_name = teacher['name'] if teacher else "Unknown Teacher"

        # Fetch tests for this teacher and subject
        cursor.execute("""
            SELECT tests.*, subjects.name AS subject_name 
            FROM tests 
            JOIN subjects ON tests.subject_id = subjects.id 
            WHERE tests.teacher_id = %s AND tests.subject_id = %s
        """, (teacher_id, subject_id))
        tests = cursor.fetchall()

        # Fetch the subject for display in the form
        cursor.execute("SELECT * FROM subjects WHERE id = %s", (subject_id,))
        subjects = cursor.fetchall()

        cursor.close()

        return render_template("teacher_dashboard.html", tests=tests, subjects=subjects, teacher_name=teacher_name)

    return redirect('/login')

# ============================== Redirect Dashboard
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        if session['role'] == 'teacher':
            return redirect('/teacher_dashboard')
        else:
            return redirect('/student_dashboard')
    return redirect('/login')

# ============================== Create Test

@app.route('/create_test', methods=['GET', 'POST'])
def create_test():
    if 'loggedin' in session and session['role'] == 'teacher':
        if request.method == 'POST':
            title = request.form['title']
            duration = int(request.form['duration'])
            subject_id = int(request.form['subject_id'])
            teacher_id = session['id']

            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO tests (subject_id, teacher_id, title, duration, is_published)
                VALUES (%s, %s, %s, %s, %s)
            """, (subject_id, teacher_id, title, duration, 0))
            mysql.connection.commit()

            # Use DictCursor for fetching
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute("""
                SELECT tests.*, subjects.name AS subject_name 
                FROM tests 
                JOIN subjects ON tests.subject_id = subjects.id 
                WHERE tests.teacher_id = %s AND tests.subject_id = %s
            """, (teacher_id, subject_id))
            tests = cursor.fetchall()

            cursor.execute("SELECT * FROM subjects WHERE id = %s", (subject_id,))
            subjects = cursor.fetchall()

            return render_template('teacher_dashboard.html', tests=tests, subjects=subjects, teacher_name=session['name'])

        return render_template('add_questions.html')
    return redirect('/login')


# ============================== Add Question
@app.route('/add_questions/<int:test_id>', methods=['GET', 'POST'])
def add_questions(test_id):
    if 'loggedin' in session and session['role'] == 'teacher':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch the test details
        cursor.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cursor.fetchone()

        # Fetch the existing questions for the test
        cursor.execute("SELECT * FROM questions WHERE test_id = %s", (test_id,))
        questions = cursor.fetchall()

        if request.method == 'POST':
            question = request.form['question']
            options = [request.form['option1'], request.form['option2'],
                       request.form['option3'], request.form['option4']]
            correct_option = int(request.form['correct_option'])

            cursor.execute("""
                INSERT INTO questions (test_id, question, option1, option2, option3, option4, correct_option)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (test_id, question, *options, correct_option))
            mysql.connection.commit()

            # Redirect to the same page to show the newly added question
            return redirect(url_for('add_questions', test_id=test_id))

        # Pass the test details and questions to the template
        return render_template('add_questions.html', test=test, test_id=test_id, questions=questions)

    return redirect('/login')

# Delete Question
@app.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    if 'loggedin' in session and session['role'] == 'teacher':
        cursor = mysql.connection.cursor()

        # Delete the question from the database
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        mysql.connection.commit()

        # Redirect back to the same page to refresh the questions list
        return redirect(url_for('edit_test', test_id=request.form['test_id']))

    return redirect('/login')

# Edit Test
@app.route('/edit_test/<int:test_id>', methods=['GET', 'POST'])
def edit_test(test_id):
    if 'loggedin' in session and session['role'] == 'teacher':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch the test data for editing
        cursor.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cursor.fetchone()

        if request.method == 'POST':
            # Update the test details
            title = request.form['title']
            duration = int(request.form['duration'])
            cursor.execute("""
                UPDATE tests
                SET title = %s, duration = %s
                WHERE id = %s
            """, (title, duration, test_id))
            mysql.connection.commit()

            return redirect(url_for('teacher_dashboard'))

        # Fetch the questions for this test
        cursor.execute("SELECT * FROM questions WHERE test_id = %s", (test_id,))
        questions = cursor.fetchall()

        return render_template('edit_test.html', test=test, questions=questions)

    return redirect('/login')
@app.route('/delete_test/<int:test_id>', methods=['POST'])
def delete_test(test_id):
    if 'loggedin' in session and session['role'] == 'teacher':
        cursor = mysql.connection.cursor()

        # Delete the test from the database
        cursor.execute("DELETE FROM tests WHERE id = %s", (test_id,))
        mysql.connection.commit()

        return redirect(url_for('teacher_dashboard'))

    return redirect('/login')

@app.route('/register', methods=['GET', 'POST']) 
def register():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name FROM subjects")
    subjects_raw = cursor.fetchall()
    subjects = [{'id': s[0], 'name': s[1]} for s in subjects_raw]

    if request.method == 'POST':
        name = request.form['name']  # Getting the name from the form
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']  # Keep password in plain text

        if role == 'student':
            cursor.execute("INSERT INTO students (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        elif role == 'teacher':
            subject_id = request.form.get('subject_id')
            if not subject_id:
                flash("Please select a subject.", "error")
                return render_template('register.html', subjects=subjects)
            cursor.execute("INSERT INTO teachers (name, email, password, subject_id) VALUES (%s, %s, %s, %s)", (name, email, password, subject_id))

        mysql.connection.commit()
        cursor.close()
        return redirect('/login')

    cursor.close()
    return render_template('register.html', subjects=subjects)


# ============================== Available Tests
@app.route('/available_tests')
def available_tests():
    if 'loggedin' in session and session['role'] == 'student':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM tests WHERE is_published = 1")
        tests = cursor.fetchall()
        return render_template('student_tests.html', tests=tests)
    return redirect('/login')

# ============================== Take Test
@app.route('/take_test/<int:test_id>')
def take_test(test_id):
    if 'loggedin' not in session or session['role'] != 'student':
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get test info
    cursor.execute("SELECT id, title FROM tests WHERE id = %s", (test_id,))
    test = cursor.fetchone()
    if not test:
        return "Test not found", 404

    # Get all questions for this test
    cursor.execute("""
        SELECT id, question, option1, option2, option3, option4
        FROM questions
        WHERE test_id = %s
    """, (test_id,))
    questions = cursor.fetchall()

    return render_template('attempt_test.html', test=test, questions=questions, test_id=test_id)

# ==============================
# ✅ Publish/Unpublish Test
# ==============================
@app.route('/publish_test/<int:test_id>', methods=['POST'])
def publish_test(test_id):
    if 'loggedin' in session and session['role'] == 'teacher':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Toggle the publish state
        cursor.execute("SELECT is_published FROM tests WHERE id = %s", (test_id,))
        test = cursor.fetchone()

        if test:
            new_state = not test['is_published']  # Toggle the publish state
            cursor.execute("UPDATE tests SET is_published = %s WHERE id = %s", (new_state, test_id))
            mysql.connection.commit()

        return redirect(url_for('teacher_dashboard'))  # Redirect back to the teacher dashboard

    return redirect('/login')  # Redirect to login if not logged in


# ==============================
# ✅ Submit Test
# ==============================
@app.route("/submit_test/<int:test_id>", methods=["POST"])
def submit_test(test_id):
    if "id" not in session or session["role"] != "student":
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()
    score = 0

    cursor.execute("SELECT id, correct_option FROM questions WHERE test_id = %s", (test_id,))
    questions = cursor.fetchall()

    for question in questions:
        q_id = str(question[0])
        selected_option = request.form.get(f"q{q_id}")
        if selected_option and int(selected_option) == question[1]:
            score += 1

    total = len(questions)  # ✅ add this line

    cursor.execute("INSERT INTO results (student_id, test_id, score) VALUES (%s, %s, %s)", 
                   (session["id"], test_id, score))
    mysql.connection.commit()
    cursor.close()

    return render_template("score.html", score=score, total=total)

@app.route("/view_scores/<int:test_id>")
def view_scores(test_id):
    # Check if teacher is logged in
    if "id" not in session or session["role"] != "teacher":
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the test details
    cursor.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
    test = cursor.fetchone()

    if not test:
        return "Test not found", 404

    # Fetch scores for the given test and display student names from the 'students' table
    cursor.execute("""
        SELECT students.password AS student_id, students.name AS student_name, results.score, results.taken_at
        FROM results
        JOIN students ON results.student_id = students.id
        WHERE results.test_id = %s
        ORDER BY results.score DESC;
    """, (test_id,))
    
    scores = cursor.fetchall()

    cursor.close()
    return render_template("teacher_results.html", test=test, scores=scores)



@app.route('/attempt_test/<int:test_id>')
def attempt_test(test_id):
    if 'loggedin' not in session or session['role'] != 'student':
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch the test
    cursor.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
    test = cursor.fetchone()
    if not test:
        return "Test not found."

    # Get subject name
    cursor.execute("SELECT name FROM subjects WHERE id = %s", (test['subject_id'],))
    subject_data = cursor.fetchone()
    subject_name = subject_data['name'] if subject_data else 'Unknown'

    # Get questions
    cursor.execute("SELECT * FROM questions WHERE test_id = %s", (test_id,))
    questions = cursor.fetchall()

    duration = test['duration']  # in minutes

    return render_template('attempt_test.html', test=test, subject_name=subject_name, questions=questions, duration=duration)


# ============================== Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ============================== Run App
if __name__ == '__main__':
    app.run(debug=True)
