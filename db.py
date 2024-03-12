import pymongo
import json

db_name = "battle_ships"
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client[db_name]

def make_db(name = db_name):
    if name in client.list_database_names():
        client.drop_database(name)
    db = client[name]
    col = db["users"]
    my_dict = {"name":"temp"}
    col.insert_one(my_dict)
    db["games"].insert_one({"state":6})

def insert_user(id, username):
    db["users"].insert_one({"_id" : id, "name":username, "wins":0, "loses":0})

def delete_user(id):
    db["users"].delete_one({"_id":id})

def get_user(id):
    return db["users"].find_one({"_id":id})

def get_game(id):
    return db["games"].find_one({"_id":id})

def update_game(game):
    db["games"].update_one({"_id": game["_id"]}, {"$set":game})


# board
# key is index (linearized), value is cell state (0 has ship/1 hit)
def start_game(id_user, bot_board):
    db["games"].insert_one({"_id":id_user, "state":"placing", "left_to_place":"[2,3,3,4,5]", "board":"{}", "bot_board":json.dumps(bot_board)})

if __name__ =="__main__":
    make_db()