import json
import os
import time
import uuid

import flask
import requests
from flask import request
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from models import *

app = flask.Flask(__name__)
cors = CORS(app, supports_credentials=True)

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_POOL_SIZE'] = 5
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 0
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

socketio = SocketIO(app, cors_allowed_origins="*", logger=True)


def socket_emit(event, data, sid):
    socketio.emit(event, data, room=sid)


from game import Game

gameHandler = Game(emit=socket_emit, app=app)


def authenticate_request(request):
    auth_key = request.cookies.get("auth-key")
    user = db.session.query(Users).filter_by(auth_key=auth_key).first()
    if user is not None:
        return True, user.id
    return False, 0


@app.route("/")
def api_index():
    # db.create_all()
    # db.session.commit()
    return flask.jsonify({"Api": True})


@app.route("/auth")
def auth():
    auth_key = flask.request.cookies.get("auth-key")
    if auth_key is not None:
        user = db.session.query(Users).filter_by(auth_key=auth_key).first()
        if user is not None:
            return flask.jsonify({"authenticated": True, "name": user.name})
    return flask.jsonify({"authenticated": False})


@app.route("/v1/auth/google", methods=["OPTIONS", "POST"])
def google_auth_login():
    if flask.request.method == "POST":
        data = flask.request.get_json()
        try:
            token = data["token"]
        except KeyError:
            return flask.jsonify({"No Token": True})

        authorization_header = {"Authorization": "OAuth %s" % token}
        r = requests.get("https://www.googleapis.com/oauth2/v2/userinfo",
                         headers=authorization_header)
        user_data = json.loads(r.text)

        user = db.session.query(Users).filter_by(email=user_data["email"]).first()
        if user is None:
            # Create new user
            user = Users(email=user_data["email"], name=user_data["name"], id=str(uuid.uuid4())[:8])

            db.session.add(user)
            db.session.commit()
        else:
            # print(user.name)
            pass

        auth_key = uuid.uuid4()
        user.auth_key = auth_key
        db.session.commit()

        resp = flask.make_response(flask.jsonify({"auth-key": auth_key, "authenticated": True, "name": user.name}))
        return resp

    # Fetch the access token

    return flask.jsonify({"Good": True})


@app.route("/game/create", methods=["post"])
def create_game():
    authenticated, user_id = authenticate_request(request)
    if authenticated:
        game = Games(code=str(uuid.uuid4())[:5])
        db.session.add(game)
        db.session.commit()
        print(f"Created Game: {game.code}")
        return flask.jsonify({"authenticated": True, "code": f"{game.code}"})
    return flask.jsonify({"authenticated": False})


@app.route("/game/valid", methods=["post"])
def valid_game():
    data = flask.request.get_json()
    game = db.session.query(Games).filter_by(code=data["game-code"]).first()
    if game is not None:
        print(game.code)
        return flask.jsonify({"valid": True})
    return flask.jsonify({"valid": False})


@socketio.on('connect')
def connect(auth):
    # auth_key = request.cookies.get("auth-key")
    pass


def get_user(request):
    user = db.session.query(Users).filter_by(sid=request.sid).first()
    if user is not None:
        return user
    return False


# @socketio.on('auth')
# def socket_auth(auth_data):
#     if os.environ.get("environment") == "DEV":
#         auth_key = auth_data["auth-key"]
#     else:
#         auth_key = request.cookies.get("auth-key")
#     user = db.session.query(Users).filter_by(auth_key=auth_key).first()
#     if user is not None:
#         if user.sid != request.sid:
#             # if db.session.query(Players).filter_by(user)
#             user.sid = request.sid
#             db.session.commit()
#             print(f"User: {user.name} authenticated")
#         socketio.emit("auth-callback", True, room=request.sid)
#     else:
#         print(f"Auth failed using: {auth_key}")


@socketio.on('game_event')
def game_event(data):
    gameHandler.ws_event(data, request)


@socketio.on('disconnect')
def disconnect():
    gameHandler.disconnect(request.sid)


if __name__ == '__main__':
    socketio.run(app)
