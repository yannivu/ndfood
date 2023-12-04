from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired
from datetime import datetime, time
import spacy

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

    # Get the current time
    current_time = datetime.now().time()

    # Determine meal type based on time
    if current_time > time(14, 0):  # Past 2 PM
        meal_type = 'Dinner'
    elif current_time > time(10, 30):  # Past 10:30 AM
        meal_type = 'Lunch'
    else:  # Past midnight until 10:30 AM
        meal_type = 'Breakfast'

    cursor.execute("""
        SELECT day, meal_type, name, serving_size, calories, total_fat, total_carbohydrate, protein, category
        FROM ndhfood
        WHERE day = %s AND meal_type = %s AND (category = 'Entrees' OR category = 'Sides')
        AND NOT (calories = 0 AND total_fat = 0 AND total_carbohydrate = 0 AND protein = 0)
    """, (day_of_week_name, meal_type))


    ndh_data = cursor.fetchall()

    categories = {}
    for item in ndh_data:
        category = item[8]  # Assuming 'category' is at index 8 in ndh_data
        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    cursor.close()
    
    return render_template('index.html', all_data=all_data, ndh_data=ndh_data, day=day_of_week_name, categories=categories, meal_type=meal_type)

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
    query = None  # Initialize the query variable

    try:
        # Retrieve the form data
        name = request.form['food_name']
        cals = int(request.form['calories']) 
        protein = int(request.form['protein'])  
        fat = int(request.form['fat'])  
        carbs = int(request.form['carbs'])  
        category = request.form['type']
        source = request.form['source']

        if source == "Dining Hall":
            # Retrieve Dining Hall specific form data
            if 'meal' in request.form and 'day' in request.form:
                meal_type = request.form['meal']
                day = request.form['day']
                cursor = mysql.connection.cursor()
                query = "INSERT INTO ndhfood (name, calories, protein, total_fat, total_carbohydrate, category, meal_type, day) VALUES ('{}', {}, {}, {}, {}, '{}', '{}', '{}');".format(name, cals, protein, fat, carbs, category, meal_type, day)
                cursor.execute(query)
                mysql.connection.commit()
                cursor.close()
                print(f'query executed: {query}')
                success_message = f"Record updated successfully. Query: {query}"
            else:
                raise KeyError(f'Missing Dining Hall specific fields. Query: {query}')
        elif source == "Grubhub":
            restaurant_name = request.form['restaurant']
            price = float(request.form['price']) 
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT restaurant_id FROM grubhub_restaurant WHERE name = %s", (restaurant_name,))
            restaurant_id = cursor.fetchone()[0]
            cursor.close()

            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO grubhub_food (name, calories, protein, total_fat, total_carbs, type, price) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (name, cals, protein, fat, carbs, category, price))
            food_id = cursor.lastrowid  # Get the last inserted food_id
            cursor.close()

            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO grubhub_available (restaurant_id, food_id) VALUES (%s, %s)", (restaurant_id, food_id))
            mysql.connection.commit()
            cursor.close()
            success_message = "Record updated successfully"
        
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"

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
def select_food():
    # Get the data sent from the frontend using request.json
    data = request.json  # Assuming data is sent in JSON format

    # Retrieve data fields from the JSON payload
    selected_food = {
        'name': data['name'],
        'calories': data['calories'],
        'protein': data['protein'],
        'carbs': data['carbs'],
        'fat': data['fat']
    }

    session['selected_food'] = selected_food  # Storing food_items in session for example
    return redirect(url_for('similar_options'))

@app.route('/similar_options')
def similar_options():
    # Retrieve selected_food from session
    selected_food = session.get('selected_food')

    cursor = mysql.connection.cursor()

    # Retrieve the list of restaurant names
    cursor.execute("SELECT DISTINCT name FROM grubhub_restaurant")
    restaurant_names = [row[0] for row in cursor.fetchall()]

    cursor.close()

    return render_template('similar_options.html', selected_food=selected_food, restaurant_names=restaurant_names)


@app.route('/display_similar', methods=['GET'])
def display_similar():
    chosen_sort = request.args.get('sort') 
    chosen_restaurant = request.args.get('restaurant')
    nutritional_values = request.args.getlist('nutritional_value')
    nlp = spacy.load("en_core_web_md")

    selected_food = session.get('selected_food')
    name = selected_food['name']
    calories = selected_food['calories']
    fat = selected_food['fat']
    carbs = selected_food['carbs']
    protein = selected_food['protein']
    
    if chosen_sort == "nutrition":
        order_by_clause = ""
        for value in nutritional_values:
            if value == 'calories':
                order_by_clause += f"ABS(gf.calories/10 - {calories}/10) + "
            elif value == 'protein':
                order_by_clause += f"ABS(gf.protein - {protein}) + "
            elif value == 'carbs':
                order_by_clause += f"ABS(gf.total_carbs - {carbs}) + "
            elif value == 'fat':
                order_by_clause += f"ABS(gf.total_fat - {fat}) + "

        # Remove the last '+' and extra spaces
        order_by_clause = order_by_clause[:-3]

        query_all = f"""SELECT gf.name, calories, protein, total_carbs, total_fat FROM grubhub_food gf
                JOIN grubhub_available ga ON gf.food_id = ga.food_id
                JOIN grubhub_restaurant gr ON ga.restaurant_id = gr.restaurant_id
                WHERE gf.name != %s 
                ORDER BY {order_by_clause} 
                LIMIT 1;"""

        query_restaurant = f"""SELECT gf.name, calories, protein, total_carbs, total_fat FROM grubhub_food gf
                JOIN grubhub_available ga ON gf.food_id = ga.food_id
                JOIN grubhub_restaurant gr ON ga.restaurant_id = gr.restaurant_id
                WHERE gr.name = %s and gf.name != %s 
                ORDER BY {order_by_clause} 
                LIMIT 1;"""

        cursor = mysql.connection.cursor()
        
        if chosen_restaurant == "Search All Restaurants":
            cursor.execute(query_all, (name,))
        else:
            cursor.execute(query_restaurant, (chosen_restaurant, name,))

        
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

        # Process and display the 'food_items' in display_similar.html template
        return render_template('display_similar.html', food_items=food_items)

    elif chosen_sort == "name":
        selected_food_processed = nlp(name)
        query_names = f"""SELECT gf.name FROM grubhub_food gf
                JOIN grubhub_available ga ON gf.food_id = ga.food_id
                JOIN grubhub_restaurant gr ON ga.restaurant_id = gr.restaurant_id
                WHERE gr.name = %s;"""
        query_allnames = f"""SELECT gf.name FROM grubhub_food gf
                JOIN grubhub_available ga ON gf.food_id = ga.food_id
                JOIN grubhub_restaurant gr ON ga.restaurant_id = gr.restaurant_id
                WHERE gf.name != %s;"""
        cursor = mysql.connection.cursor()
        if chosen_restaurant == "Search All Restaurants":
            cursor.execute(query_allnames, (name,))
        else:
            cursor.execute(query_names, (chosen_restaurant,))
        rows = cursor.fetchall()
        max_similarity = 0
        result = None   
        for row in rows:
            row_doc = nlp(row[0])
            curr_similarity = selected_food_processed.similarity(row_doc)
            if curr_similarity > max_similarity:
                max_similarity = curr_similarity
                result = row[0]
        cursor.close()
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT name, calories, protein, total_carbs, total_fat "
            "FROM grubhub_food "
            "WHERE name = %s "
            "UNION "
            "SELECT name, calories, protein, total_carbohydrate as total_carbs, total_fat "
            "FROM ndhfood "
            "WHERE name = %s",
            (result, result)
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

        return render_template('display_similar.html', food_items=food_items)

if __name__ == '__main__':
    app.debug=True
    app.run(host='db8.cse.nd.edu', port=5070)