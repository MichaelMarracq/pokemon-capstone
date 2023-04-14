from flask import Flask, render_template, redirect, session, flash, request, jsonify
# from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Like
from forms import LoginForm, RegisterForm
import requests, random, json

app = Flask(__name__)
app.app_context().push()
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///pokemon"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "mikeisabeast"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

API_KEY = '86d009f1-34fa-4d94-9888-7eae05f5fc1f'
BASE_URL = 'https://api.pokemontcg.io/v2/'


connect_db(app)
db.create_all()

# toolbar = DebugToolbarExtension(app)


@app.route('/')
def homepage():
    return redirect('/home')


@app.route('/home')
def show_home():
    if 'curr_user' in session:
        id = session['curr_user']
        user = User.query.filter_by(id=id).first()
        return render_template('home.html', user=user)
    else:
        user = ''
        return render_template('home.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def show_login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)
        if user:
            session['curr_user'] = user.id
            flash('You Logged In!')
            return redirect('/home')
        else:
            return redirect('/liked_cards')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def show_register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        new_user = User.register(username, password)

        db.session.add(new_user)
        db.session.commit()

        return redirect('/home')

    return render_template('register.html', form=form)


# @app.route('/<int:id>/likes')
# def show_likes(id):
#     likes = Like.query.filter_by(user_id=id).all()

#     cards = []

#     for like in likes:
#         url = f'{BASE_URL}cards/{like.card_id}'
#         headers = {'x-api-key':API_KEY}
#         response = requests.get(url, headers=headers)
#         raw_data = response.json()
#         data = raw_data['data']
#         cards.append({
#             'id':data['id'],
#             'name':data['name'],
#             'image':data['images']['small'],
#             'rarity':data['rarity'],
#             'price': data['cardmarket']['prices']['averageSellPrice']
# })
#     return render_template('liked.html', cards=cards)


@app.route('/<int:id>/likes')
def show_likes(id):
    likes = Like.query.filter_by(user_id=id).all()
    like_ids = [like.card_id for like in likes]
    json_likes = json.dumps(like_ids)


    cards = []

    for like in likes:
        url = f'{BASE_URL}cards/{like.card_id}'
        headers = {'x-api-key':API_KEY}
        response = requests.get(url, headers=headers)
        raw_data = response.json()
        data = raw_data['data']
        
        # Check if the 'rarity' field is present in the data
        if 'rarity' in data:
            rarity = data['rarity']
        else:
            rarity = 'Common'
        
        # Check if the 'cardmarket' and 'averageSellPrice' fields are present in the data
        if 'cardmarket' in data and 'prices' in data['cardmarket'] and 'averageSellPrice' in data['cardmarket']['prices']:
            price = data['cardmarket']['prices']['averageSellPrice']
        else:
            price = None
        
        # Append the card information to the list of cards if both 'rarity' and 'price' are present
        cards.append({
            'id':data['id'],
            'name':data['name'],
            'image':data['images']['small'],
            'rarity':rarity,
            'price': price
        })
    
    return render_template('liked.html', cards=cards, like_ids=json_likes)


def get_setlist():
    url = f'{BASE_URL}sets'
    sets = []
    headers = {'x-api-key':API_KEY}
    response = requests.get(url, headers=headers)
    raw_data = response.json()
    data = raw_data['data']
    for card_set in data:
        name = card_set['name']
        id = card_set['id']
        sets.append({
            'id':id,
            'name':name
        })
    return sets[:14]


def get_setlist_index():
    url = f'{BASE_URL}sets'
    sets = []
    headers = {'x-api-key':API_KEY}
    response = requests.get(url, headers=headers)
    raw_data = response.json()
    data = raw_data['data']
    for card_set in data:
        sets.append(card_set)
    return sets[:14]

@app.route('/index')
def show_index():
    sets = get_setlist_index()
    return render_template('set_index.html', sets=sets)


@app.route('/index/<set_id>')
def show_set(set_id):



    if 'curr_user' in session:
        user_id = session['curr_user']
        likes = Like.query.filter_by(user_id=user_id).all()
        like_ids = [like.card_id for like in likes]
        json_likes = json.dumps(like_ids)


    sets = get_setlist()
    url = f'{BASE_URL}cards?q=set.id:{set_id}'
    cards = []
    headers = {'x-api-key':API_KEY}
    response = requests.get(url, headers=headers)
    raw_data = response.json()
    data = raw_data['data']
    for card in data:
        cards.append(card)
    random_cards = random.sample(cards, min(len(cards), 50))
    return render_template('index.html', sets=sets, cards=random_cards, like_ids=json_likes)    

@app.route('/<int:id>')
def show_user(id):
    user = User.query.filter_by(id=id).first()
    return render_template('profile.html', user=user)

@app.route('/addlike', methods=['POST'])
def add_like():
    data = request.get_json()
    card_id = data.get('card_id')
    if 'curr_user' in session:
        user_id = session['curr_user']
    else:
        return jsonify({'message': 'Nope.'}), 500
    print(f'Card Id = {card_id}, User Id = {user_id}')
    like = Like(user_id=user_id, card_id=card_id)

    db.session.add(like)
    db.session.commit()

    return jsonify({'message': 'Like added to database.'}), 200



@app.route('/deletelike', methods=['POST'])
def delete_like():
    user_id = session['curr_user']
    data = request.get_json()
    card_id = data.get('card_id')

    like = Like.query.filter_by(user_id=user_id, card_id=card_id).first()
    if like:
        db.session.delete(like)
        db.session.commit()
        return jsonify({'message': 'Like deleted from database.'}), 200
    else:
        return jsonify({'message': 'Like not found in database.'}), 404


@app.route('/logout')
def logout():
    session.pop('curr_user', None)
    flash('You Logged Out!')
    return redirect('/home')