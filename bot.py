import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import db
import json

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
        shoot()
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
    db.start_game(id)
    print("Working on it")

def shoot():
    print("Not yet implemented")

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

        # check out of bounds
        if start_index < 0 or start_index > 99:
            await message.reply("Invalid starting position")
            return
        if end_index < 0 or end_index > 99:
            await message.reply("Invalid end position")
            return
        
        # check diagoal placement
        if start_row != end_row and start_col != end_col:
            await message.reply("Cant place ship diagonal")
            return
        
        # check if that ship already placed and if valid len
        ship_len = abs(start_col - end_col) + abs(start_row - end_row) + 1
        if ship_len > 5 or ship_len < 0:
            await message.reply("Invalid ship lenght")
            return
        
        if ship_len not in game["left_to_place"]:
            await message.reply("You already placed that ship")
            return
        game["left_to_place"].remove(ship_len)

        # check if space is free
        keys = game['board'].keys()
        for pos in range(start_index, end_index + 1):
            if str(pos) in keys:
                await message.reply("Cant place ship there")
                return
        for pos in range(start_index, end_index + 1):
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
    board = ""
    for i in range(100):
        if i % 10 == 0 and i > 0 :
            board += "\n"
        if game_board.get(str(i), None) == None:
            board += 'W'
        elif game_board[str(i)] == 0:
            board += 'S'
        else:
            board += 'X'
    await message.reply(board)


if __name__ == "__main__":
    bot.run(TOKEN)