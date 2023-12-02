from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired
from datetime import datetime

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

def group_by_type(items):
    types = {}
    for item in items:
        item_type = item[5]
        if item_type not in types:
            types[item_type] = []
        types[item_type].append(item)
    return types

def split_odd_type(types):
    # Check if the total number of types is odd
    num_types = len(types)
    if num_types % 2 == 1:
        # Find the largest type
        largest_type = max(types, key=lambda type: len(types[type]))
        largest_items = types[largest_type]

        # Remove the largest type from the dictionary
        del types[largest_type]

        # Split the largest type into two equal parts
        half_len = len(largest_items) // 2
        types[largest_type] = largest_items[:half_len]  # Update the current type
        new_type = f"{largest_type} (cont.)"
        types[new_type] = largest_items[half_len:]

    return types


@app.route('/')
def index():
    cursor = mysql.connection.cursor()

    # Fetch a list of all restaurant names
    cursor.execute("SELECT DISTINCT name FROM grubhub_restaurant")
    restaurant_names = [row[0] for row in cursor.fetchall()]

    all_data = {}  # Store data for all restaurants

    for restaurant_name in restaurant_names:
        cursor.execute("""SELECT gf.name, gf.calories, gf.protein, gf.total_carbs as carbs, gf.total_fat as fat, 
                        gf.type, gf.price
                        FROM grubhub_available ga
                        JOIN grubhub_food gf ON ga.food_id = gf.food_id
                        JOIN grubhub_restaurant gr ON ga.restaurant_id = gr.restaurant_id
                        WHERE gr.name = %s;""", (restaurant_name,))
        restaurant_items = cursor.fetchall()
        
        types = group_by_type(restaurant_items)
        types = split_odd_type(types)

        # Split the types into two separate lists
        top_row = []
        bottom_row = []
        for t, items in types.items():
            if len(top_row) < len(types)/2:
                top_row.append((t, items))
            else:
                bottom_row.append((t, items))

        # Store data for this restaurant
        all_data[restaurant_name] = {
            "top_row": top_row,
            "bottom_row": bottom_row
        }


    # Fetch data from the ndh_data table
    # Mapping of weekday integers to day names
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Get the current date
    current_date = datetime.now()

    # Get the day of the week as an integer (Monday is 0, Sunday is 6)
    day_of_week_int = current_date.weekday()

    # Get the corresponding day name using the mapping
    day_of_week_name = days_of_week[day_of_week_int]

    cursor.execute("""
        SELECT day, meal_type, name, serving_size, calories, total_fat, total_carbohydrate, protein
        FROM ndhfood
        WHERE day = %s
        AND NOT (calories = 0 AND total_fat = 0 AND total_carbohydrate = 0 AND protein = 0)
    """, (day_of_week_name,))

    ndh_data = cursor.fetchall()

    cursor.close()
    
    return render_template('index.html', all_data=all_data, ndh_data=ndh_data, day=day_of_week_name)

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

    # Retrieve the list of restaurant names
    cursor.execute("SELECT DISTINCT name FROM grubhub_restaurant")
    restaurant_names = [row[0] for row in cursor.fetchall()]

    cursor.close()

    return render_template('admin_page.html', user_list=user_list, restaurant_names=restaurant_names)


@app.route('/delete_user', methods=['POST'])
def delete_user():
    if request.method == 'POST':
        user_to_delete = request.form['user_to_delete']
        if user_to_delete:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM users WHERE username = %s", (user_to_delete,))
            mysql.connection.commit()
            cursor.close()
    
    back_button = f'<a href="{url_for("admin_page")}">Back</a>'
    return f"{user_to_delete} successfully deleted<br>{back_button}"


@app.route('/add_user', methods=['POST'])
def add_user():
    cur = mysql.connection.cursor()
    user = request.form['username']
    pw = request.form['password']
    
    cur.execute("SELECT * FROM users WHERE username = %s", (user,))
    existing_user = cur.fetchone()

    confirmation_message = f"{user} added with password: {pw}"
    back_button = f'<a href="{url_for("admin_page")}">Back</a>'

    if existing_user:
        # If the user already exists, return confirmation with a back button
        confirmation_with_back = f"{confirmation_message}<br>{back_button}"
    else:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pw))
        mysql.connection.commit()
        cur.close()
        # In the 'else' branch, return confirmation with the back button as well
        confirmation_with_back = f"{confirmation_message}<br>{back_button}"

    return confirmation_with_back


@app.route('/confirm_update', methods=['GET'])
def confirm_update():
    user = request.args.get('user')
    pw = request.args.get('pw')
    return render_template('confirm_update.html', user=user, pw=pw)

@app.route('/add_item', methods=['POST'])
def add_item():
    try:
        # Retrieve the form data
        name = request.form['food_name']
        cals = int(request.form['calories']) 
        protein = float(request.form['protein'])  
        fat = float(request.form['fat'])  
        carbs = float(request.form['carbs'])  
        item_type = request.form['type']
        source = request.form['source']
        price = float(request.form['price']) 
        restaurant_name = request.form['restaurant']

        if source == "Dining Hall":
            # Add logic here for adding Dining Hall items
            pass
        elif source == "Grubhub":
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT restaurant_id FROM grubhub_restaurant WHERE name = %s", (restaurant_name,))
            restaurant_id = cursor.fetchone()[0]
            cursor.close()

            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO grubhub_food (name, calories, protein, total_fat, total_carbs, type, price) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (name, cals, protein, fat, carbs, item_type, price))
            food_id = cursor.lastrowid  # Get the last inserted food_id
            cursor.close()

            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO grubhub_available (restaurant_id, food_id) VALUES (%s, %s)", (restaurant_id, food_id))
            mysql.connection.commit()
            cursor.close()

        success_message = "Record updated successfully"
    except Exception as e:
        error_message = "An error occurred. Please check the data and try again."

    back_button = f'<a href="{url_for("admin_page")}">Back</a>'
    if "error_message" in locals():
        return f"{error_message}<br>{back_button}"
    else:
        return f"{success_message}<br>{back_button}"


@app.route('/search_user', methods=['POST'])
def search_user():
    back_button = f'<a href="{url_for("admin_page")}">Back</a>'

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

        return f"User: {username} | Password: {password}<br>{back_button}"
    else:
        return f"User not found.<br>{back_button}"

@app.route('/delete_item', methods=['POST'])
def delete_item():
    if request.method == 'POST':
        item_to_delete = request.form['item_to_delete']
        option = request.form['option']
        if item_to_delete:
            cursor = mysql.connection.cursor()
            if option == "Grubhub":
                cursor = mysql.connection.cursor()
                cursor.execute("DELETE FROM grubhub_food WHERE name = %s", (item_to_delete,))
                mysql.connection.commit()
                cursor.close()
    
    back_button = f'<a href="{url_for("admin_page")}">Back</a>'
    return f"{item_to_delete} successfully deleted<br>{back_button}"

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_term = request.form.get('search_term')
        search_pattern = f"%{search_term}%"

        cursor = mysql.connection.cursor()
        
        cursor.execute(
            "SELECT name, calories, protein, total_carbs, total_fat "
            "FROM grubhub_food "
            "WHERE name LIKE %s "
            "UNION "
            "SELECT name, calories, protein, total_carbohydrate as total_carbs, total_fat "
            "FROM ndhfood "
            "WHERE name LIKE %s",
            (search_pattern, search_pattern)
        )

        results = cursor.fetchall()

        # Create a list of dictionaries to hold results
        food_items = []
        for row in results:
            food_items.append({
                'name': row[0],
                'calories': row[1],
                'protein': row[2],
                'carbs': row[3],
                'fat': row[4]
            })

        cursor.close()

        return render_template('search.html', food_items=food_items)

    # Handle the case for GET requests or initial page load
    return render_template('search.html')


@app.route('/select_food', methods=['POST'])
def select_nutrition():
    #Can input cals fat and carbs as parameter or add the search into this function and save as variables
    try:
        # Retrieve user input from the form
        #unsure if this interacts correctly with ui
        selected_source = request.form['selected_source']
        selected_restaurant = request.form['selected_restaurant']
        order_by_clause = ""
        for attribute in selected_attributes:
            if attribute == "calories":
                order_by_clause +=f"ABS(gf.{attribute/10} - %s) + "
            order_by_clause += f"ABS(gf.{attribute} - %s) + "

        order_by_clause = order_by_clause.rstrip("+ ")
        # Validate input
        if not selected_food or not selected_attributes or not selected_source:
            return jsonify({"error": "Invalid input. Please provide all required fields."})

        # Define the columns to be selected based on user input
        selected_columns = ", ".join(selected_attributes)

        # Query the appropriate table based on the selected source
        cursor = mysql.connection.cursor()

        if selected_source == "Grubhub":
            cursor.execute(f"""SELECT gf.name, calories, total_fat, total_carbs, protein FROM grubhub_food gf
                               JOIN grubhub_available ga ON gf.food_id = ga.food_id
                               JOIN grubhub_restaurant gr ON ga.restaurant_id = gr.restaurant_id
                               WHERE gr.name = %s
                               ORDER BY {order_by_clause} 
                               LIMIT 1;""", (selected_restaurant, cals/10, fat, carbs, protein)) #cals, fat, carbs, protein is those stats for the originally selected food
        elif selected_source == "Dining Hall":
            cursor.execute(f"""SELECT ndhfood.name, calories, total_fat, total_carbohydrate, protein FROM ndhfood
                               ORDER BY {order_by_clause}
                               LIMIT 1;""", (cals/10, fat, carbs, protein))
        else:
            return jsonify({"error": "Invalid source selected."})

        selected_item = cursor.fetchone()
        cursor.close()

        if not selected_item:
            return jsonify({"error": "No matching item found."})

        # Format the result as a JSON response
        result = {}
        for i, attribute in enumerate(selected_attributes):
            result[attribute] = selected_item[i]

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.debug=True
    app.run(host='db8.cse.nd.edu', port=5070)