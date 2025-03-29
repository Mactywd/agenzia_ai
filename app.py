from flask import Flask, render_template
from scrapers import flights, hotels, attractions

app = Flask(__name__)

@app.route('/')
def home():
    # load index.html
    return render_template('templates/index.html')


if __name__ == '__main__':
    app.run(debug=True)

