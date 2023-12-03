def tester():
    selected_food = 'Chef''s Salad'
    chosen_restaurant = request.args.get('restaurant')
    nlp = spacy.load("en_core_web_md")
    selected_food_processed = nlp(selected_food)
    query_names = f"""SELECT gf.name FROM grubhub_food gf
            JOIN grubhub_available ga ON gf.food_id = ga.food_id
            JOIN grubhub_restaurant gr ON ga.restaurant_id = gr.restaurant_id
            WHERE gr.name = 'chick-fil-a';"""
    cursor = mysql.connection.cursor()
    cursor.execute(query_names)
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
    return {'name': result}