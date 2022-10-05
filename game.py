import random
import time
import uuid
from operator import itemgetter

from models import *


class Game:
    def __init__(self, emit, app):
        self.event_function_map = {"join_game": self.join_game, "roll": self.roll,
                                   "number_clicked": self.number_clicked, "start": self.start_game,
                                   "end_turn": self.end_turn, "leave_game": self.leave_game}
        self.colours = ["#000000", "#FFFFFF", "#0000ff", "#ff0000", "#d0208f", "#ffff00", "#2e8b57", "#ffa600",
                        "#00ffff", "#da70d6", "#cd863f", "#80ff00"]

        self.emit = emit
        self.app = app
        with self.app.app_context():
            db.create_all()
            db.session.commit()

            players = db.session.query(Players).all()
            for player in players:
                player.connected = False

            db.session.commit()

    def ws_event(self, data, request):
        try:
            self.event_function_map[data[0]](data[1], request)

        except KeyError:  # Security feature so only authorised methods can be executed remotely
            print(f"Event: {data[0]} is not registered")

    def join_game(self, data, request):
        try:
            user = db.session.query(Users).filter_by(auth_key=data["auth-key"]).first()
        except KeyError:
            print("No Auth")
            self.emit("join_response", {"success": False, "game_exist": False, "isSignedIn": False}, request.sid)
            return 0
        if user is not None:
            game = db.session.query(Games).filter_by(code=data["game-code"]).first()
            if game is not None:
                players = db.session.query(Players).filter_by(game_code=game.code, user_id=user.id).first()
                if players is None:
                    if not game.started:
                        existing_players = db.session.query(Players).filter_by(game_code=game.code).all()
                        num = len(existing_players) + 1
                        if num is None:
                            num = 1
                        player = Players(id=str(uuid.uuid4())[:5], game_code=game.code, user_id=user.id, connected=True,
                                         sid=request.sid, player_number=num)

                        if num == 1:
                            print(player.id)
                            game.players_turn = player.id
                        db.session.add(player)
                        db.session.commit()
                        self.emit("join_response", {"success": True, "player_id": player.id}, player.sid)

                        self.send_player_game_info(game, player)
                        self.send_all_players_info(game)
                elif players.connected is False:
                    players.connected = True
                    players.sid = request.sid
                    db.session.commit()
                    self.emit("join_response", {"success": True, "player_id": players.id}, players.sid)
                    self.send_player_game_info(game, players)
                    self.send_all_players_info(game)
            else:
                print("No game")
                self.emit("join_response", {"success": False, "game_exist": False, "isSignedIn": True}, request.sid)
        else:
            print("Invalid Auth Key")

    def disconnect(self, sid):
        player = db.session.query(Players).filter_by(sid=sid).first()
        if player is not None:
            if player.connected:
                player.connected = False
                db.session.commit()

    def leave_game(self, data, request):
        player = db.session.query(Players).filter_by(sid=request.sid).first()
        if player is not None:
            player.connected = False
            db.session.commit()

            # delete_able = True
            # for p in player.game.players:
            #     if p.connected:
            #         delete_able = False
            #
            # if delete_able:
            #     for p in player.game.players:
            #         db.session.delete(p)
            #
            #     game = db.session.query(Games).filter_by(code=data["game-code"]).first()
            #
            #     db.session.delete(game)
            #
            #     db.session.commit()

    def get_players_data(self, players):
        player_info = []
        colour_index = 0
        for p in players:
            player_info.append(
                {"name": p.user.name, "player_number": p.player_number, "score": p.score, "connected": p.connected,
                 "id": p.id, "colour": self.colours[colour_index]})

            colour_index += 1

        round_info = {"rounds": players[0].game.round_number, "max_rounds": players[0].game.max_rounds}

        return {"player_info": player_info, "round_info": round_info}

    def get_game_data(self, game):
        game_info = {"code": game.code, "started": game.started, "paused": game.paused,
                     "round_number": game.round_number, "players_turn": game.players_turn,
                     "dice": {"dice_1": game.dice_1, "dice_2": game.dice_2},
                     "can_roll": False, "roll_lock": game.roll_lock, "end_turn": game.end_turn,
                     "game_over": game.game_over,
                     "numbers": [
                         {"number": 1, "used": game.number_1}, {"number": 2, "used": game.number_2},
                         {"number": 3, "used": game.number_3}, {"number": 4, "used": game.number_4},
                         {"number": 5, "used": game.number_5}, {"number": 6, "used": game.number_6},
                         {"number": 7, "used": game.number_7}, {"number": 8, "used": game.number_8},
                         {"number": 9, "used": game.number_9}]}
        return game_info

    def send_all_players(self, game, event, data):
        players = db.session.query(Players).filter_by(game_code=game.code).order_by(Players.player_number).all()
        for p in players:
            self.emit(event, data, sid=p.sid)

    def send_all_players_info(self, game):
        players = db.session.query(Players).filter_by(game_code=game.code).order_by(
            Players.player_number).all()
        self.send_all_players(game, "player_info", self.get_players_data(players))

    def send_player_game_info(self, game, player):
        players = db.session.query(Players).filter_by(game_code=game.code).order_by(Players.player_number).all()

        player_info = self.get_players_data(players)
        game_info = self.get_game_data(game)

        if player.id == game.players_turn:
            game_info["can_roll"] = True

        self.emit("board_info", game_info, sid=player.sid)
        self.emit("player_info", player_info, sid=player.sid)

    def send_all_board_info(self, game):
        for player in game.players:
            game_info = self.get_game_data(game)
            if player.id == game.players_turn:
                game_info["can_roll"] = True

            self.emit("board_info", game_info, sid=player.sid)

    def clear_board(self, game):
        game.number_1 = False
        game.number_2 = False
        game.number_3 = False
        game.number_4 = False
        game.number_5 = False
        game.number_6 = False
        game.number_7 = False
        game.number_8 = False
        game.number_9 = False
        db.session.commit()

    def start_game(self, data, request):
        player = db.session.query(Players).filter_by(sid=request.sid).first()
        if player.id == player.game.players_turn:
            player.game.started = True
            db.session.commit()

            self.send_all_board_info(player.game)
            self.send_all_players(player.game, "status_message", {"message": f"{player.user.name}'s Turn"})

    def roll(self, data, request):
        player = db.session.query(Players).filter_by(sid=request.sid).first()
        if not player.game.roll_lock:
            roll = {"dice_1": random.randint(1, 6), "dice_2": random.randint(1, 6), "roll_wait": random.randrange(1, 3)}
            # roll["dice_1"] = 3
            # roll["dice_2"] = 3
            player.game.dice_1 = roll["dice_1"]
            player.game.dice_2 = roll["dice_2"]

            can_play = False
            player.game.roll_lock = True
            legal_small, legal_combined = self.get_legal_numbers(player.game)

            if legal_combined is not None:
                can_play = True

            if len(legal_small) != 0:
                can_play = True

            if not can_play:
                player.game.end_turn = True

            db.session.commit()
            self.send_all_players(player.game, "rolled", roll)
            self.send_all_board_info(player.game)

    def end_turn(self, data, request):
        player = db.session.query(Players).filter_by(sid=request.sid).first()
        if player.id == player.game.players_turn:
            player.game.end_turn = False
            player.game.roll_lock = False
            player.game.select_strategy_small = False
            player_number = player.player_number
            next_player = db.session.query(Players).filter_by(game_code=player.game.code,
                                                              player_number=player_number + 1).first()
            if next_player is None:
                next_player = db.session.query(Players).filter_by(game_code=player.game.code,
                                                                  player_number=1).first()
                player.game.players_turn = next_player.id
                if player.game.round_number == player.game.max_rounds:
                    self.game_over(player.game)
                else:
                    player.game.round_number += 1

            else:
                player.game.players_turn = next_player.id

            db.session.commit()
            self.clear_board(player.game)

            self.send_all_players_info(player.game)
            self.send_all_board_info(player.game)
            player = db.session.query(Players).filter_by(id=player.game.players_turn).first()
            self.send_all_players(player.game, "status_message", {"message": f"{player.user.name}'s Turn"})

    def game_over(self, game):
        game.game_over = True
        db.session.commit()

        players_data = self.get_players_data(game.players)
        players_data["player_info"] = sorted(players_data["player_info"], key=itemgetter('score'), reverse=True)

        self.send_all_players(game, "game_over", {"players": players_data})

    def get_legal_numbers(self, game):
        numbers = [game.number_1, game.number_2, game.number_3, game.number_4,
                   game.number_5, game.number_6, game.number_7, game.number_8,
                   game.number_9]
        legal_small = []
        legal_combined = None

        if not game.select_strategy_small:
            if game.dice_1 != game.dice_2:
                if not (numbers[game.dice_1 - 1] or numbers[game.dice_2 - 1]):
                    legal_small.append(game.dice_1)

                    legal_small.append(game.dice_2)

            if game.dice_1 + game.dice_2 < 10:
                legal_combined = game.dice_1 + game.dice_2
                if numbers[legal_combined - 1]:
                    legal_combined = None
        else:
            if not numbers[game.dice_1 - 1]:
                legal_small.append(game.dice_1)

            if not numbers[game.dice_2 - 1]:
                legal_small.append(game.dice_2)

        return legal_small, legal_combined

    def number_clicked(self, data, request):
        player = db.session.query(Players).filter_by(sid=request.sid).first()
        num_map = {"1": "number_1", "2": "number_2", "3": "number_3", "4": "number_4", "5": "number_5", "6": "number_6",
                   "7": "number_7", "8": "number_8", "9": "number_9"}
        numbers = [player.game.number_1, player.game.number_2, player.game.number_3, player.game.number_4,
                   player.game.number_5, player.game.number_6, player.game.number_7, player.game.number_8,
                   player.game.number_9]
        # Map is a security measure
        if not player.game.end_turn:
            if player.id == player.game.players_turn:
                if player.game.roll_lock:
                    legal_small, legal_combined = self.get_legal_numbers(player.game)
                    picked_num = int(data["number"])
                    print(picked_num)
                    if picked_num in legal_small:
                        if not player.game.select_strategy_small:
                            exec(f"player.game.number_{picked_num}=True")
                            numbers[picked_num - 1] = True
                            player.game.select_strategy_small = True
                            player.score += picked_num

                        else:
                            exec(f"player.game.number_{picked_num}=True")
                            player.game.select_strategy_small = False
                            player.game.roll_lock = False
                            player.score += picked_num
                    elif legal_combined == picked_num:
                        exec(f"player.game.number_{picked_num}=True")
                        player.game.roll_lock = False
                        player.score += picked_num

                    db.session.commit()

                    game = db.session.query(Games).filter_by(code=player.game_code).first()
                    if (game.number_1 is True) and (game.number_2 is True) and (
                            game.number_3 is True) and (game.number_4 is True) and (
                            game.number_5 is True) and (game.number_6 is True) and (
                            game.number_7 is True) and (game.number_8 is True) and (
                            game.number_9 is True):
                        print("THE BOX HAS BEEN SHUT")

                        self.clear_board(game)

                    self.send_all_board_info(player.game)
                    self.send_all_players_info(player.game)

                    print(legal_small, legal_combined)

                else:
                    print("Need to roll first")
            else:
                print("Wrong Player")
        else:

            print("You Turn Needs to End First")
