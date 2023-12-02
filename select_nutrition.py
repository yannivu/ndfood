from flask import jsonify

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
            cursor.execute(f"""SELECT ndhfood.name, caloreis, total_fat, total_carbhoydrate, protein FROM ndhfood
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