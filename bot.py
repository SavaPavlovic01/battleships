import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import db
import json
import random
import matplotlib.pyplot as plt
import numpy as np

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content == "bb help":
        print (message.author.id)
        await message.reply("PRAVILA")
    elif message.content == "bb start":
        await start_game(message.author.id, message)
    elif "bb shoot" in message.content:
        parsed = message.content.split("(")[1].split(')')[0].split(',')
        if len(parsed) != 2:
            await message.reply("Invalid arguments")
            return
        await shoot(int(parsed[0]), int(parsed[1]), message.author.id, message)
    elif message.content == "bb record":
        await send_record(message)
    elif "bb place" in message.content:
        parsed = message.content.split("(")
        parsed = parsed[1].split(')')
        parsed = parsed[0].split(',')
        if len(parsed) != 4:
            await message.reply("Invalid arguments")
            return
        await place(int(parsed[0]), int(parsed[1]), int(parsed[2]), int(parsed[3]), message.author.id, message)
    elif message.content == 'bb board':
        await show(message.author.id, message)
    elif message.content == "bb bot":
        await show_bot_board(message.author.id, message)
    elif message.content == "bb calc":
        await message.reply("json.dumps(calc_prob())")
    elif message.content == "bb test":
        x = np.array(range(100))
        y = np.array([0]*100)
        moves = np.array([]) 
        n= 5000
        for i in range(n):
            move = await play_game()
            y[move] += 1
            moves = np.append(moves, move)
            print(str(i) + " out of " + str(n))
        plt.bar(x,y)
        plt.title("MEAN: " + str(np.mean(moves)) + "   MEDIAN: " + str(np.median(moves)) + "   STD: " + str(np.std(moves)) + 
                  "\nN = " + str(n))
        plt.savefig("RES.png")
        
        plt.close()
        await message.reply("DONE")
        return

async def send_record(message):
    user = db.get_user(message.author.id)
    if user == None:
        await message.reply("0 wins\n0 loses")
    else:
        await message.reply(f'{user["wins"]} wins\n{user["loses"]} loses')


async def start_game(id, message):
    if db.get_game(id) != None:
        await message.reply("You already have an active game", )
        return
    if db.get_user(id) == None:
        db.insert_user(id,"temp")
    bot_board = await generate_board()
    db.start_game(id,bot_board)
    print("Working on it")

async def shoot(row, col, id, message):
    game = db.get_game(id)
    if game == None:
        await message.reply("You dont have an active game")
        return
    if row > 9 or col > 9 or row < 0 or col < 0:
        await message.reply("Index out of bounds")
        return
    bot_board = json.loads(game['bot_board'])
    index = row * 10 + col
    if bot_board.get(str(index), None) != None:
        await message.reply("Hit!")
        bot_board[str(index)] = 1
        game['bot_board'] = json.dumps(bot_board)
        db.update_game(game)
    else:
        await message.reply("Miss!")

async def place(start_row, start_col, end_row, end_col, id, message):
    game = db.get_game(id)
    game["left_to_place"] = json.loads(game['left_to_place'])
    game['board'] = json.loads(game['board'])
    if game == None:
        await message.reply("You have no active game")
        return
    else:
        start_index = start_col + start_row * 10
        end_index = end_col + end_row * 10
        direction = 0
        if start_col == end_col:
            direction = 1
        else:
            direction = 0

        if not await is_valid(start_row, start_col, end_row, end_col, game['board'], game['left_to_place'], message):
            return
        ship_len = abs(start_col - end_col) + abs(start_row - end_row) + 1
        game['left_to_place'].remove(ship_len)
        step = 10
        if direction == 0: step = 1
        for pos in range(start_index, end_index + 1, step):
            game['board'][str(pos)] = 0
        game['board'] = json.dumps(game['board'])
        game['left_to_place'] = json.dumps(game['left_to_place'])
        db.update_game(game)
        await message.reply('ok')

async def show(id, message):
    game = db.get_game(id)
    game_board = json.loads(game['board'])
    if game == None:
        await message.reply("You dont have an active game")
        return
    await message.reply(board_string(game_board))

async def show_bot_board(id, message):
    game = db.get_game(id)
    game_board = json.loads(game["bot_board"])
    await message.reply(board_string(game_board))

def board_string(game_board):
    board = ""
    for i in range(100):
        if i % 10 == 0 and i > 0 :
            board += "\n"
        if game_board.get(str(i), None) == None:
            board += 'E'
        elif game_board[str(i)] == 0:
            board += 'S'
        else:
            board += 'X'
    return board

async def is_valid(start_row,start_col, end_row,end_col, board, left_to_place, message):
    start_index = start_col + start_row * 10
    end_index = end_col + end_row * 10
    direction = 0
    if start_col == end_col:
        direction = 1
    if start_row < 0 or start_col< 0 or end_row < 0 or end_col < 0:
        return False
    if start_index < 0 or start_index > 99:
        if message != None: await message.reply("Invalid starting position")
        return False
    if end_index < 0 or end_index > 99:
        if message != None: await message.reply("Invalid end position")
        return False
        
    # check diagoal placement
    if start_row != end_row and start_col != end_col:
        if message != None: await message.reply("Cant place ship diagonal")
        return False
        
    # check if that ship already placed and if valid len
    ship_len = abs(start_col - end_col) + abs(start_row - end_row) + 1
    if direction == 0 and start_col + ship_len > 9:
        if message != None: await message.reply("Cant place ship there")
        return False
    if ship_len > 5 or ship_len < 0:
        if message != None: await message.reply("Invalid ship lenght")
        return False
        
    if ship_len not in left_to_place:
        if message != None: await message.reply("You already placed that ship")
        return False

    # check if space is free
    keys = board.keys()
    step = 10
    if direction == 0: step = 1
    
    for pos in range(start_index, end_index + 1, step):

        if str(pos) in keys:
            if message != None: await message.reply("Cant place ship there")
            return False
    return True


async def generate_board():
    board = {}
    ship_len = [2,3,3,4,5]
    ship_positions = {2:[], 3:[], 4:[], 5:[], 0:[]}
    while len(ship_len) > 0:
        row = random.randint(0,9)
        col = random.randint(0,9)
        cur_ship = ship_len[len(ship_len) - 1]
        options = []
        
        if await is_valid(row, col, row, col + cur_ship - 1, board, ship_len, None):
            options.append((row, col, 0))
        if await is_valid(row, col, row + cur_ship - 1, col, board, ship_len, None):
            options.append((row, col, 1))
        if len(options)== 0 : continue
        res = random.choice(options)
        options.clear()
        if res[2] == 0:
            index = res[0] * 10 + res[1]
            cur_len = cur_ship
            if cur_ship == 3 and len(ship_positions[3]) > 0: cur_len = 0
            for pos in range(index, index + cur_ship):
                board[str(pos)] = 0
                ship_positions[cur_len].append(pos)
            ship_len.pop()
        else:
            index = res[0] * 10 + res[1]
            cur_len = cur_ship
            if cur_ship == 3 and len(ship_positions[3]) > 0: cur_len = 0
            for pos in range(index, index + cur_ship * 10, 10):
                board[str(pos)] = 0
                ship_positions[cur_len].append(pos)
            ship_len.pop()

    return board, ship_positions
            
async def calc_percent():
    freq = [0] * 100
    n = 30000
    total = 0
    for i in range(n):
        board = await generate_board()
        for i in range(100):
            if board.get(str(i), None) != None:
                freq[i] += 1
                #total += 1
    for i in range(100):
        freq[i] = freq[i] / n
    np_arr = np.array(freq)
    np_arr = np.reshape(np_arr, (10,10))
    print(np_arr)
    plt.matshow(np_arr, cmap = plt.cm.Blues)
    plt.show()
    return [0,1]
    
def get_best_move_hunting(sizes, shot, name, verbose = False):
    freq = []
    for i in range(100):
        freq.append([0, i])
    total = 0
    while len(sizes) > 0:
        cur_size = sizes[len(sizes) - 1]
        if cur_size == 0: cur_size = 3
        sizes.pop()
        for i in range(10):
            for j in range(10):
                if j + cur_size - 1 < 10:
                    valid = True
                    for pos in range(i * 10 + j, i * 10 + j + cur_size):
                        if pos in shot:
                            valid = False
                            break
                    if valid:
                        for pos in range(i * 10 + j, i * 10 + j + cur_size):
                            freq[pos][0] += 1
                            total += 1
                if i + cur_size - 1 < 10:
                    valid = True
                    for pos in range(i * 10 + j, i * 10 + j + cur_size * 10, 10):
                        if pos in shot:
                            valid = False
                            break
                    if valid:
                        for pos in range(i * 10 + j, i * 10 + j + cur_size * 10, 10):
                            freq[pos][0] += 1
                            total += 1    
    if verbose:
        graph_arr = []
        for i in freq:
            graph_arr.append(i[0])
        np_arr = np.array(graph_arr)
        np_arr = np.reshape(np_arr, (10,10))
        plt.matshow(np_arr, cmap = plt.cm.Blues)
        plt.title("Hunting")
        plt.savefig(str(name) + ".png") 
        plt.close()            
    freq = sorted(freq, key=lambda x:x[0], reverse=True)
    return freq[0][1]

def get_best_move_targeting(sizes, shot, targets, name, verbose = False):
    freq = []
    for i in range(100):
        freq.append([0, i])
    total = 0
    while len(sizes) > 0:
        cur_size = sizes[len(sizes) - 1]
        if cur_size == 0: cur_size = 3
        sizes.pop()
        for i in range(10):
            for j in range(10):
                if j + cur_size - 1 < 10:
                    valid = True
                    at_least_one = False
                    for pos in range(i * 10 + j, i * 10 + j + cur_size):
                        if pos in targets: 
                            at_least_one = True
                            continue
                        if pos in shot:
                            valid = False
                            break
                    if valid and at_least_one:
                        for pos in range(i * 10 + j, i * 10 + j + cur_size):
                            if pos in shot: continue
                            freq[pos][0] += 1
                            total += 1
                if i + cur_size - 1 < 10:
                    valid = True
                    at_least_one = False
                    for pos in range(i * 10 + j, i * 10 + j + cur_size * 10, 10):
                        if pos in targets: 
                            at_least_one = True
                            continue
                        if pos in shot:
                            valid = False
                            break
                    if valid and at_least_one:
                        for pos in range(i * 10 + j, i * 10 + j + cur_size * 10, 10):
                            if pos in shot: continue
                            freq[pos][0] += 1
                            total += 1                    
    if verbose:
        graph_arr = []
        for i in freq:
            graph_arr.append(i[0])
        np_arr = np.array(graph_arr)
        np_arr = np.reshape(np_arr, (10,10))
        plt.matshow(np_arr, cmap = plt.cm.Blues)
        plt.title("Targeting")
        plt.savefig(str(name) + ".png")
        plt.close()
    freq = sorted(freq, key=lambda x:x[0], reverse=True)
    return freq[0][1]    

def get_dead_ships(ship_pos):
    ret = []
    for key, val in ship_pos.items():
        if len(val) == 0: ret.append(key)
    return ret

def get_alive_ships(ship_pos):
    ret = []
    for key, val in ship_pos.items():
        if len(val) > 0: ret.append(key)
    return ret

def get_dead_ship_len(ship_pos):
    ls = get_dead_ships(ship_pos)
    cnt = 0
    for num in ls:
        add = num
        if num == 0: add = 3
        cnt += add
    return cnt

def hit_ship(ship_pos, pos):
    for key, val in ship_pos.items():
        if pos in val: val.remove(pos)

async def play_game():
    board, ship_pos = await generate_board()
    #print(board_string(board))
    #print(board)
    #print(ship_pos)
    shot = set()
    hits = set()
    targets = set()
    move_cnt = 0
    while len(get_alive_ships(ship_pos)) > 0:
        #print(move_cnt,get_alive_ships(ship_pos))
        if len(hits) == get_dead_ship_len(ship_pos):
            move = get_best_move_hunting(get_alive_ships(ship_pos), shot, move_cnt)
            #print(move)
            move_cnt += 1
            if board.get(str(move), None) != None:
                hits.add(move)
                shot.add(move)
                targets.add(move)
                hit_ship(ship_pos, move)
            else:
                shot.add(move)
        else:
            if len(targets) == 0: print("BUG")
            move = get_best_move_targeting(get_alive_ships(ship_pos), shot, targets, move_cnt)
            #print("targeting", move, "\ntargets:", targets)
            move_cnt += 1
            if board.get(str(move), None) != None:
                hits.add(move)
                shot.add(move)
                hit_ship(ship_pos, move)
                if len(hits) == get_dead_ship_len(ship_pos):
                    targets.clear()
                else:
                    targets.add(move)
            else:
                shot.add(move)
        if move_cnt == 80:
            print("SHOT",shot)
            print("BOARD", board)
            print("HITS",hits)
            print("SHIP_POS", ship_pos)
            print("SHIPS_ALIVE", get_alive_ships(ship_pos))
            print("DEAD_SHIPS", get_dead_ships(ship_pos))
            print("TARGETS", targets)
            break
    return move_cnt

if __name__ == "__main__":
    bot.run(TOKEN)