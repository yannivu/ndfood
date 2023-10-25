from flask import Flask, render_template, request, session, redirect, url_for
#from flask_mysqldb import MySQL

app = Flask(__name__) # create a new Flask instance

app.secret_key='yvu' # secret key to setup the new instance

# creating a connection with mySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'yvu'
app.config['MYSQL_PASSWORD'] = 'goirish'
app.config['MYSQL_DB'] = 'yvu'

@app.route('/', methods=['GET', 'POST']) # use get to get info (we are getting the user's age)
def index():
    return render_template('index.html')
    
if __name__ == '__main__':
    app.debug=True
    app.run(host='db8.cse.nd.edu', port=5070) # runs the web app (specify host and port) -opens http://db8.cse.nd.edu:5070