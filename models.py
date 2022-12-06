# import sqlalchemy as db
# from sqlalchemy import func
# from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.VARCHAR(8), primary_key=True, nullable=False)
    email = db.Column(db.VARCHAR(120), nullable=False)
    name = db.Column(db.VARCHAR(120), nullable=False)
    auth_key = db.Column(db.VARCHAR(120))


class Games(db.Model):
    __tablename__ = 'games'
    code = db.Column(db.VARCHAR(5), primary_key=True, nullable=False, unique=True)
    datetime_created = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    players = relationship("Players", backref="games")
    started = db.Column(db.Boolean, nullable=False, default=False)
    paused = db.Column(db.Boolean, nullable=False, default=False)
    round_number = db.Column(db.Integer, nullable=False, default=1)
    max_rounds = db.Column(db.Integer, nullable=False, default=5)
    players_turn = db.Column(db.VARCHAR(8))
    dice_1 = db.Column(db.Integer, nullable=False, default=0)
    dice_2 = db.Column(db.Integer, nullable=False, default=0)
    roll_required = db.Column(db.Boolean, nullable=False, default=True)
    # True represents individual numbers and blocks the combined number being selected
    select_strategy_small = db.Column(db.Boolean, nullable=False, default=False)
    roll_lock = db.Column(db.Boolean, nullable=False, default=False)
    end_turn = db.Column(db.Boolean, nullable=False, default=False)
    game_over = db.Column(db.Boolean, nullable=False, default=False)
    number_1 = db.Column(db.Boolean, nullable=False, default=False)
    number_2 = db.Column(db.Boolean, nullable=False, default=False)
    number_3 = db.Column(db.Boolean, nullable=False, default=False)
    number_4 = db.Column(db.Boolean, nullable=False, default=False)
    number_5 = db.Column(db.Boolean, nullable=False, default=False)
    number_6 = db.Column(db.Boolean, nullable=False, default=False)
    number_7 = db.Column(db.Boolean, nullable=False, default=False)
    number_8 = db.Column(db.Boolean, nullable=False, default=False)
    number_9 = db.Column(db.Boolean, nullable=False, default=False)


class Players(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.VARCHAR(8), primary_key=True, nullable=False)
    user_id = db.Column(db.VARCHAR(8), db.ForeignKey('users.id'))
    sid = db.Column(db.VARCHAR(120))
    game_code = db.Column(db.VARCHAR(5), db.ForeignKey("games.code"))
    user = relationship("Users", backref="players")
    game = relationship("Games", back_populates="players", overlaps="games")
    connected = db.Column(db.Boolean, nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    datetime_joined = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    player_number = db.Column(db.Integer, nullable=False)

# Base.metadata.create_all(engine)
