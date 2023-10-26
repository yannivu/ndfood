from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

app = Flask(__name__)
app.secret_key = 'yvu'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'yvu'
app.config['MYSQL_PASSWORD'] = 'goirish'
app.config['MYSQL_DB'] = 'yvu'

# Initialize MySQL
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT username, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and user[1] == password:
            flash('Login successful', 'success')
            return redirect(url_for('admin_page'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/admin_page', methods=['GET', 'POST'])
def admin_page():
    # Retrieve the list of users from the database
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT username FROM users")
    user_list = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        # Handle user deletion
        user_to_delete = request.form['user_to_delete']
        if user_to_delete:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM users WHERE username = %s", (user_to_delete,))
            mysql.connection.commit()
            cursor.close()

    return render_template('admin_page.html', user_list=user_list)

@app.route('/add_user', methods=['POST'])
def add_user():
    cur = mysql.connection.cursor()
    user = request.form['username']
    pw = request.form['password']
    # Check if the username already exists in the table
    cur.execute("SELECT * FROM users WHERE username = %s", (user,))
    existing_user = cur.fetchone()

    if existing_user:
        # If the user already exists, redirect to the confirmation page
        return redirect(url_for('confirm_update', user=user, pw=pw))
    else:
        # If the user doesn't exist, insert a new user
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pw))
        mysql.connection.commit()
        cur.close()
        return f"{user} added with password: {pw}"


@app.route('/confirm_update', methods=['GET'])
def confirm_update():
    user = request.args.get('user')
    pw = request.args.get('pw')
    return render_template('confirm_update.html', user=user, pw=pw)

@app.route('/add_item', methods=['POST'])
def add_item():
    name = request.form['food_name']
    cals = request.form['calories']
    protein = request.form['protein']
    fat = request.form['fat']
    carbs = request.form['carbs']
    
    # Retrieve the selected source
    source = request.form['source']

    if source == "Dining Hall":
        # Item is from Dining Hall
        # Add your logic here
        pass
    elif source == "Grubhub":
        # Item is from Grubhub
        # Add your logic here
        pass

    # Rest of your code
    return "Record updated successfully"

@app.route('/search_user', methods=['POST'])
def search_user():
    username = request.form['username']

    if not username:
        return "Please enter a username."

    # Perform a database query to retrieve information about the specified user
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user_info = cursor.fetchone()
    cursor.close()

    if user_info:
        # Access the elements of the tuple by index
        username = user_info[0]
        password = user_info[1]

        return f"User: {username} | Password: {password}"
    else:
        return "User not found."


if __name__ == '__main__':
    app.debug=True
    app.run(host='db8.cse.nd.edu', port=5070)