import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import random
from sheetCommands import (
    get_service,
    get_sheet_values,
    write_to_sheet,
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")

witty_quotes = open("quotes.txt", "r")
quotes = witty_quotes.read().split("\n")

used_symbol = "s>"

spreadSrv, driveSrv = get_service()

print(get_sheet_values(spreadSrv, SHEET_ID, "in sync!A12:C12"))
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix=used_symbol, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")


@bot.command()
async def help(ctx):
    chosen_line = quotes[random.randint(0, len(quotes) - 1)]
    embed = discord.Embed(
        title="Commands",
        description=f"Prefix: {used_symbol}",
        color=int("0x2ECC71", 16),
    )
    embed.add_field(
        name="read <number>", value="Reads the entry at the given number", inline=False
    )
    embed.add_field(
        name="read_max", value="Reads the current max entry number", inline=False
    )
    embed.add_field(
        name="write <message>",
        value="Writes the message to the sheet. Please put the message in quotes.",
        inline=False,
    )
    embed.add_field(
        name="add_wording", value="Increments the current wording count", inline=False
    )
    embed.add_field(
        name="current_wording", value="Displays the current wording count", inline=False
    )
    embed.add_field(
        name="add_quote <quote>", value="Adds a quote to the list of quotes", inline=False
    )
    embed.set_footer(text=chosen_line)
    await ctx.send(embed=embed)


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.command()
async def read_max(ctx):
    value = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E3:E3")
    await ctx.send(f"Same count is currently at: {value["values"][0][0]}")


@bot.command()
async def read(ctx, num):
    try:
        chosen_line = quotes[random.randint(0, len(quotes) - 1)]
        num = int(num)
        value = get_sheet_values(spreadSrv, SHEET_ID, f"in sync!C{num+2}")
        string_value = value["values"][0]
        if string_value == []:
            await ctx.send("No entry found")
            return
        string_value = [x.replace("\\n", "\n") for x in string_value]
        embed = discord.Embed(
            title=f"Entry {num}",
            description=f"{string_value[0]}",
            color=int("0x2ECC71", 16),
        )
        embed.set_footer(text=chosen_line)
        await ctx.send(embed=embed)
    except ValueError:
        await ctx.send("Please provide a valid number")
        return


@bot.command()
async def write(ctx, arg):
    if arg[0] == '"':
        end = arg.find('"', 1)
        if end == -1:
            await ctx.send("Invalid format")
            return
        arg = arg[1:end]
    current = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E3:E3")
    current = int(current["values"][0][0])
    try:
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"in sync!A{current+3}:C{current+3}",
            {"values": [[current + 1, "", arg]]},
        )
    except Exception as e:
        await ctx.send(f"Failed to write to sheet: {e}")
        return
    await ctx.send(f"Successfully wrote entry {current+1} ")


@bot.command()
async def add_wording(ctx):
    current = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E4")
    current = int(current["values"][0][0])
    try:
        write_to_sheet(spreadSrv, SHEET_ID, "in sync!E4", {"values": [[current + 1]]})
        await ctx.send(f"Current count: {current+1}")
        return
    except Exception as e:
        await ctx.send(f"Failed to write to sheet: {e}")
        return


@bot.command()
async def current_wording(ctx):
    current = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E4")
    current = int(current["values"][0][0])
    await ctx.send(f"Current Wording! count: {current}")
    return

@bot.command()
async def add_quote(ctx, quote):
    with open("quotes.txt", "a") as f:
        f.write(f"\n{quote}")
    await ctx.send("Quote added!")
    quotes.append(quote)

bot.run(TOKEN)
