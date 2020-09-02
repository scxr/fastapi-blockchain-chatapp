import datetime
import requests
import json
from flask import render_template, redirect, request
from app import app
CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"

posts = []

def fetch_posts():
    get_chain_address = f"{CONNECTED_NODE_ADDRESS}/chain"
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        content = []
        chain = json.loads(response.content)
        for block in chain["chain"]:
            for tx in block["transactions"]:
                tx["index"] = block["index"]
                tx["hash"] = block["previous_hash"]
                content.append(tx)
        global posts
        posts = sorted(content, key=lambda k: k['timestamp'],
                       reverse=True)
        return posts

@app.route('/')
def index():
    posts = fetch_posts()
    print(posts)
 
    return render_template('index.html',
                           title='Decentralisation for you',
                           posts=posts,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string)

@app.route('/submit', methods=['POST'])
def submit_txt():
    post_content = request.form["content"]
    author = request.form["author"]
    post_object = {
        'author':author,
        'content':post_content,
    }
    new_transaction_address = f"{CONNECTED_NODE_ADDRESS}/new_transaction"
    r = requests.post(new_transaction_address,
                  json=post_object,
                  headers={'Content-type':'application/json'})
    print(r.content)
    return redirect('/')
def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M')