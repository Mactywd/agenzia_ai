from flask import Flask, render_template, url_for
from scrapers import flights, hotels, attractions

app = Flask(__name__, static_url_path='/static')

@app.route('/')
def index():
    # load index.html
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    # load index.html
    return render_template('chatbot.html')

@app.route('/faq')
def faq():
    # load index.html
    return render_template('faq.html')

if __name__ == '__main__':
    app.run(debug=True)

