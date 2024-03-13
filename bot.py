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
        await message.reply(json.dumps(calc_prob()))

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
    while len(ship_len) > 0:
        row = random.randint(0,9)
        col = random.randint(0,9)
        cur_ship = ship_len[len(ship_len) - 1]
        options = []
        """
        if await is_valid(row, col, row, col + cur_ship - 1, board, ship_len, None):
            index = row * 10 + col  
            
            for pos in range(index, index + cur_ship):
                board[str(pos)] = 0
            ship_len.pop()
            continue
        if await is_valid(row, col, row + cur_ship - 1, col, board,ship_len, None):
            index = row * 10 + col 
            for pos in range(index, index + cur_ship * 10, 10):
                board[str(pos)] = 0
            ship_len.pop()
        """
        if await is_valid(row, col, row, col + cur_ship - 1, board, ship_len, None):
            options.append((row, col, 0))
        if await is_valid(row, col, row + cur_ship - 1, col, board, ship_len, None):
            options.append((row, col, 1))
        if await is_valid(row - cur_ship + 1, col, row, col, board, ship_len, None):
            options.append((row - cur_ship + 1, col, 1))
        if await is_valid(row, col - cur_ship + 1, row, col, board, ship_len, None): 
            options.append((row, col - cur_ship + 1, 0))
        if len(options)== 0 : continue
        res = random.choice(options)
        options.clear()
        if res[2] == 0:
            index = res[0] * 10 + res[1]
            for pos in range(index, index + cur_ship):
                board[str(pos)] = 0
            ship_len.pop()
        else:
            index = res[0] * 10 + res[1]
            for pos in range(index, index + cur_ship * 10, 10):
                board[str(pos)] = 0
            ship_len.pop()

    return board
            
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
    
def calc_prob():
    sizes = [2,3,3,4,5]
    freq = [0] * 100
    total = 0
    while len(sizes) > 0:
        cur_size = sizes[len(sizes) - 1]
        sizes.pop()
        for i in range(10):
            for j in range(10):
                if j + cur_size - 1 < 10:
                    for pos in range(i * 10 + j, i * 10 + j + cur_size):
                        freq[pos] += 1
                        total += 1
                if i + cur_size - 1 < 10:
                    for pos in range(i*10 + j, i*10 + j + cur_size * 10, 10):
                        freq[pos] += 1
                        total += 1
    np_arr = np.array(freq)
    np_arr = np.reshape(np_arr, (10,10))
    plt.matshow(np_arr, cmap = plt.cm.Blues)
    plt.show()
    return [0,1]


if __name__ == "__main__":
    bot.run(TOKEN)