import asyncio
import datetime
import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, button
from dotenv import load_dotenv
import random
import json
import time
from sheetCommands import (
    get_service,
    get_sheet_values,
    write_to_sheet,
)


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
REMINDER_FILE = "reminders.json"

witty_quotes = open("quotes.txt", "r")
quotes = witty_quotes.read().split("\n")

used_symbol = "s>"

spreadSrv, driveSrv, calendarSrv = get_service()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix=used_symbol, intents=intents, help_command=None)

reminders = {}

def save_reminders():
    if not os.path.exists(REMINDER_FILE):
        print("where??")
        json.dump(reminders, open(REMINDER_FILE, "w"), default=str)
        return
    with open(REMINDER_FILE, "w") as f:
        json.dump(reminders, f, default=str)

def load_reminders():
    global reminders
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "r") as f:
            if os.stat(REMINDER_FILE).st_size == 0:
                return
            data = json.load(f)
            for user_id, user_reminders in data.items():
                reminders[int(user_id)] = []
                for r in user_reminders:
                    r["time"] = datetime.datetime.fromisoformat(r["time"])
                    if r.get("interval"):
                        days, time_str = r["interval"].split(", ")
                        days = int(days.split()[0])
                        hours, minutes, seconds = map(int, time_str.split(":"))
                        r["interval"] = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
                    reminders[int(user_id)].append(r)
    else:
        print("where the fuck is the reminders file?")

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")
    load_reminders()

helpFields = [
    ["help", "Displays this message"],
    ["pick <item1> / <item2> / ...", "Picks a random item from the list of items. Items are separated by /, no quotes needed."],
    ["add_quote <quote>", "Adds a quote to the list of footer quotes"],
    ["show_quotes", "Displays a list of footer quotes"],
    ["read_backlog <number>", "Reads the backlog entry at the given number"],
    ["write_backlog <message>", "Writes the message to the backlog sheet."],
    ["read_backlog_max", "Reads the current max backlog entry number"],
    ["read_random", "Grabs a random in sync! entry from the sheet"],
    ["remind_me <date> <time> <message>", "Reminds you at the given date and time with the message"],
    ["remind_me_interval <interval> <message>", "Reminds you at the given interval with the message"],
    ["daily_reminder <time> <gap> <message>", "Reminds you at the given time every gap days with the message"],
    ["delete_reminder <index>", "Deletes the reminder at the given ID"],
    ["read_coffee <number>", "Reads the coffee entry at the given number"],
    ["add_coffee <name>; <location>; <gone>; <notes>", "Adds a coffee entry to the sheet. Use the command on its own to see the format."],
    ["random_coffee", "Reads a random coffee entry"],
    ["edit_coffee <entry number>; <location/gone/notes>; <new value>", "Edits a coffee entry. Use the command on its own to see the format."],
    ["read_foodies <number>", "Reads the foodies entry at the given number"],
    ["add_foodies <name>; <location>; <gone>; <moni>; <notes>", "Adds a foodies entry to the sheet. Use the command on its own to see the format."],
    ["random_foodies", "Reads a random foodies entry"],
    ["edit_foodies <entry number>; <location/gone/moni/notes>; <new value>", "Edits a foodies entry. Use the command on its own to see the format."],
    ["read_foodies_max", "Reads the current max foodies entry number"],
    ["read_coffee_max", "Reads the current max coffee entry number"],
    ["read <number>", "Reads the entry at the given number"],
    ["read_max", "Reads the current max entry number"],
    ["write <message>", "Writes the message to the sheet."],
    ["add_wording", "Increments the current wording count"],
    ["current_wording", "Displays the current wording count"],
    ["read_offsync <number>", "Reads the off sync entry at the given number"],
    ["read_max_offsync", "Reads the current max off sync entry number"],
    ["write_offsync <message>", "Writes the message to the off sync sheet."],
]

#add a command not found error message
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Command not found",
            color=int("0xE74C3C", 16),
        )
        embed.add_field(name="Try", value=f"{used_symbol}help", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)

class Help(View):
    pagination = []
    pagination.append(helpFields[0:8])
    pagination.append(helpFields[8:12])
    pagination.append(helpFields[12:17])
    pagination.append(helpFields[17:22])
    pagination.append(helpFields[22:])
    current_page = 0

    def __init__(self):
        super().__init__()
        self.embed = discord.Embed(
            title="Help",
            color=int("0x2ECC71", 16),
        )
        for field in self.pagination[self.current_page]:
            self.embed.add_field(name=field[0], value=field[1], inline=False)
        self.embed.set_footer(text=f"Page {self.current_page + 1}")

    @button(label="Previous", style=discord.ButtonStyle.primary)
    async def prev(self, interaction, button):
        if self.current_page == 0:
            await interaction.response.send_message("You are already on the first page", ephemeral=True)
            return  
        self.current_page -= 1
        self.embed.clear_fields()
        for field in self.pagination[self.current_page]:
            self.embed.add_field(name=field[0], value=field[1], inline=False)
        self.embed.set_footer(text=f"Page {self.current_page + 1}")
        await interaction.response.edit_message(embed=self.embed, view=self)
    
    @button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        if self.current_page == 5:
            await interaction.response.send_message("You are already on the last page", ephemeral=True)
            return
        self.current_page += 1
        self.embed.clear_fields()
        for field in self.pagination[self.current_page]:
            self.embed.add_field(name=field[0], value=field[1], inline=False)
        self.embed.set_footer(text=f"Page {self.current_page + 1}")
        await interaction.response.edit_message(embed=self.embed, view=self)

@bot.command()
async def help(ctx):
    view = Help()
    await ctx.send(embed=view.embed, view=view)

@bot.command()
async def write_backlog(ctx, *args):
    arg = " ".join(args)
    arg = arg.strip()
    current = get_sheet_values(spreadSrv, SHEET_ID, "backlog!E3:E3")
    current = int(current["values"][0][0])
    sender = ctx.author
    print(sender)
    if sender.id == 851515562118873108:
        sender = "Yoon"
    elif sender.id == 205950684225470464:
        sender = "Minim"
    else:
        sender = sender.name
    try:
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"backlog!A{current+3}:D{current+3}",
            {"values": [[current + 1, "", arg, sender]]},
        )
    except Exception as e:
        await ctx.send(f"Failed to write to sheet: {e}")
        return
    embed = discord.Embed(
        title=f"Successfully wrote entry {current+1}",
        description=f"{arg}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def read_backlog(ctx, *args):
    try:
        current = get_sheet_values(spreadSrv, SHEET_ID, "backlog!E3:E3")
        current = int(current["values"][0][0])
        chosen_line = quotes[random.randint(0, len(quotes) - 1)]
        num = int(args[0])
        value = get_sheet_values(spreadSrv, SHEET_ID, f"backlog!C{num+2}:D{num+2}")
        string_value = value["values"][0]
        if num > current:
            await ctx.send("No entry found")
            return
        embed = discord.Embed(
            title=f"Backlog {num}",
            color=int("0x2ECC71", 16),
        )
        embed.add_field(name="Logger", value=string_value[1], inline=False)
        embed.add_field(name="Entry", value=string_value[0], inline=False)
        embed.set_footer(text=chosen_line)
        await ctx.send(embed=embed)
    except ValueError:
        await ctx.send("Please provide a valid number")
        return

@bot.command()
async def read_backlog_max(ctx):
    value = get_sheet_values(spreadSrv, SHEET_ID, "backlog!E3:E3")
    embed = discord.Embed(
        title="Backlog!",
        description=f"Backlog count: {value['values'][0][0]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

class Backlog(View):
    def __init__(self, backlog):
        super().__init__()
        self.backlog = backlog
        self.current_page = 0
        self.embed = discord.Embed(
            title="Backlog",
            description="\n".join(backlog[self.current_page : self.current_page + 10]),
            color=int("0x2ECC71", 16),
        )
        self.embed.set_footer(text=f"Page {self.current_page//10 + 1}")

    @button(label="Previous", style=discord.ButtonStyle.primary)
    async def prev(self, interaction, button):
        self.current_page -= 10
        self.embed.description = "\n".join(self.backlog[self.current_page : self.current_page + 10])
        self.embed.set_footer(text=f"Page {self.current_page//10 + 1}")
        await interaction.response.edit_message(embed=self.embed, view=self)
    
    @button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        self.current_page += 10
        self.embed.description = "\n".join(self.backlog[self.current_page : self.current_page + 10])
        self.embed.set_footer(text=f"Page {self.current_page//10 + 1}")
        await interaction.response.edit_message(embed=self.embed, view=self)

@bot.command()
async def show_backlog(ctx):
    backlog = get_sheet_values(spreadSrv, SHEET_ID, "backlog!C3:D100")
    backlog = [f"{x[0]} - {x[1]}" for x in backlog["values"]]
    view = Backlog(backlog)
    await ctx.send(embed=view.embed, view=view)

@bot.command()
async def ping(ctx):
    await ctx.send("pong")

@bot.command()
async def random_number(ctx, *args):
    for arg in args:
        if not arg.isdigit():
            await ctx.send("Please provide valid numbers")
            return
    if len(args) == 0 or len(args) == 1:
        await ctx.send("Please provide at least 2 numbers")
        return
    rand = random.randint(0, len(args) - 1)
    embed = discord.Embed(
        title="Random number",
        color=int("0x2ECC71", 16),
    )
    embed.add_field(name="You rolled a", value=args[rand], inline=False)
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)
    return

@bot.command()
async def read_max(ctx):
    value = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E3:E3")
    embed = discord.Embed(
        title="Same!",
        description=f"Same! count: {value['values'][0][0]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def read_max_offsync(ctx):
    value = get_sheet_values(spreadSrv, SHEET_ID, "off sync!E3:E3")
    embed = discord.Embed(
        title="Off sync!",
        description=f"Off sync! count: {value['values'][0][0]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def remind_me(ctx, date: str, time: str, *, message: str):
    if "/" not in date or ":" not in time:
        await ctx.send("Please provide a valid date and time")
        return
    # if there are no arguments, send a help message
    if date == "" or time == "" or message == "":
        embed = discord.Embed(
            title="Remind me!",
            color=int("0xF1C40F", 16),
        )
        embed.add_field(name="Remind me", value=f"{used_symbol}remind_me <date> <time> <message>", inline=False)
        embed.add_field(name="date", value="A date in the format dd/mm. That means day/month. Example: 31/12", inline=False)
        embed.add_field(name="time", value="A time in the format hh:mm. In 24h format. Example: 13:00", inline=False)
        embed.add_field(name="message", value="A string of words, no quotes needed", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return
    remind_time = datetime.datetime.strptime(f"{date} {time}", "%d/%m %H:%M")
    if remind_time < datetime.datetime.now():
        await ctx.send("Please provide a valid time")
        return
    user_id = str(ctx.author.id)

    if user_id not in reminders:
        reminders[user_id] = []
    reminders[user_id].append({"time": remind_time, "message": message, "interval": None})
    save_reminders()

    await ctx.send(f"Reminder set for {remind_time}")

@bot.command()
async def remind_me_interval(ctx, interval: str, *, message: str):
    if interval == "" or message == "":
        embed = discord.Embed(
            title="Remind me!",
            color=int("0xF1C40F", 16),
        )
        embed.add_field(name="Remind me", value=f"{used_symbol}remind_me_interval <interval> <message>", inline=False)
        embed.add_field(name="interval", value="A time interval in the format <number><time unit>. Example: 1d2h3m4s", inline=False)
        embed.add_field(name="message", value="A string of words, no quotes needed", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return

    # interval can be set to something like 1d2h3m4s
    interval = interval.replace("d", "*86400+") # days
    interval = interval.replace("h", "*3600+") # hours
    interval = interval.replace("m", "*60+") # minutes
    interval = interval.replace("s", "+0")
    interval = eval(interval)
    user_id = str(ctx.author.id)
    remind_time = datetime.datetime.now() + datetime.timedelta(seconds=interval)

    if user_id not in reminders:
        reminders[user_id] = []
    
    reminders[user_id].append({"time": remind_time, "message": message, "interval": interval})
    save_reminders()

    if interval < 60:
        await ctx.send(f"Reminder set for {interval} seconds from now")
    elif interval < 3600:
        await ctx.send(f"Reminder set for {interval//60} minutes and {interval%60} seconds from now")
    elif interval < 86400:
        await ctx.send(f"Reminder set for {interval//3600} hours, {(interval%3600)//60} minutes and {interval%60} seconds from now")
    else:
        await ctx.send(f"Reminder set for {interval//86400} days, {(interval%86400)//3600} hours, {(interval%3600)//60} minutes and {interval%60} seconds from now")

@bot.command()
async def daily_reminder(ctx, time: str, gap: int, *, message: str):
    # Takes a time and an amount of gap days to send a message
    if ":" not in time:
        await ctx.send("Please provide a valid time")
        return
    if int(gap) < 1:
        await ctx.send("Please provide a valid gap")
        return
    if time == "" or gap == "" or message == "":
        embed = discord.Embed(
            title="Daily reminder!",
            color=int("0xF1C40F", 16),
        )
        embed.add_field(name="Daily reminder", value=f"{used_symbol}daily_reminder <time> <gap> <message>", inline=False)
        embed.add_field(name="time", value="A time in the format hh:mm. In 24h format. Example: 13:00", inline=False)
        embed.add_field(name="gap", value="A number of days to wait before sending the message. Set to 1 if you want it to be daily", inline=False)
        embed.add_field(name="message", value="A string of words, no quotes needed", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return
    user_id = str(ctx.author.id)
    if user_id not in reminders:
        reminders[user_id] = []
    # set the time's date to today
    remind_time = datetime.datetime.strptime(f"{datetime.datetime.now().strftime('%d/%m/%Y')} {time}", "%d/%m/%Y %H:%M")
    if remind_time < datetime.datetime.now():
        remind_time += datetime.timedelta(days=gap)
    reminders[user_id].append({"time": remind_time, "message": message, "interval": datetime.timedelta(days=gap)})
    save_reminders()

    if int(gap) == 1:
        await ctx.send(f"Daily reminder set for {time}")
    else:
        await ctx.send(f"Reminder set for {time} every {gap} days")

@bot.command()
async def delete_reminder(ctx, index: int):
    user_id = str(ctx.author.id)
    if user_id not in reminders or index >= len(reminders[user_id]):
        await ctx.send("Invalid reminder index")
        return
    reminders[user_id].pop(index)
    save_reminders()
    await ctx.send("Reminder deleted")

@bot.command()
async def read(ctx, num):
    try:
        current = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E3:E3")
        current = int(current["values"][0][0])
        chosen_line = quotes[random.randint(0, len(quotes) - 1)]
        num = int(num)
        value = get_sheet_values(spreadSrv, SHEET_ID, f"in sync!C{num+2}")
        string_value = value["values"][0]
        print(value["values"])
        if num > current:
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
async def read_random(ctx):
        current = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E3:E3")
        current = int(current["values"][0][0])
        chosen_line = quotes[random.randint(0, len(quotes) - 1)]
        num = random.randint(3, current+2)
        value = get_sheet_values(spreadSrv, SHEET_ID, f"in sync!C{num}:C{num}")
        string_value = value["values"][0]
        if string_value == []:
            await ctx.send("No entry found")
            return
        string_value = [x.replace("\\n", "\n") for x in string_value]
        embed = discord.Embed(
            title=f"Entry {num - 2}",
            description=f"{string_value[0]}",
            color=int("0x2ECC71", 16),
        )
        embed.set_footer(text=chosen_line)
        await ctx.send(embed=embed)

@bot.command()
async def read_offsync(ctx, num):
    try:
        chosen_line = quotes[random.randint(0, len(quotes) - 1)]
        num = int(num)
        value = get_sheet_values(spreadSrv, SHEET_ID, f"off sync!C{num+2}")
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
async def write(ctx, *arg):
    arg = " ".join(arg)
    arg = arg.strip()
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
    embed = discord.Embed(
        title=f"Successfully wrote entry {current+1}",
        description=f"{arg}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def write_offsync(ctx, *args):
    arg = " ".join(args)
    arg = arg.strip()
    current = get_sheet_values(spreadSrv, SHEET_ID, "off sync!E3:E3")
    current = int(current["values"][0][0])
    try:
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"off sync!A{current+3}:C{current+3}",
            {"values": [[current + 1, "", arg]]},
        )
    except Exception as e:
        await ctx.send(f"Failed to write to sheet: {e}")
        return
    embed = discord.Embed(
        title=f"Successfully wrote entry {current+1}",
        description=f"{arg}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)


@bot.command()
async def add_wording(ctx):
    current = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E4")
    current = int(current["values"][0][0])
    try:
        write_to_sheet(spreadSrv, SHEET_ID, "in sync!E4", {"values": [[current + 1]]})
        embed = discord.Embed(
            title="Wording!",
            description=f"Current count: {current+1}",
            color=int("0x2ECC71", 16),
        )
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return
    except Exception as e:
        await ctx.send(f"Failed to write to sheet: {e}")
        return


@bot.command()
async def current_wording(ctx):
    current = get_sheet_values(spreadSrv, SHEET_ID, "in sync!E4")
    current = int(current["values"][0][0])
    embed = discord.Embed(
        title="Wording!",
        description=f"Current count: {current}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)
    return

@bot.command()
async def add_quote(ctx, *args):
    quote = " ".join(args)
    quote = quote.strip()
    with open("quotes.txt", "a") as f:
        f.write(f"\n{quote}")
    quotes.append(quote)
    embed = discord.Embed(
        title="Quote added!",
        description=f"{quote}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)
    return


class Quotes(View):
    # purpose: Create an embed with a list of 10 quotes with pagination, and 2 buttons to navigate through the pages
    def __init__(self, quotes):
        super().__init__()
        self.quotes = quotes
        self.current_page = 0
        self.embed = discord.Embed(
            title="Quotes",
            description="\n".join(quotes[self.current_page : self.current_page + 10]),
            color=int("0x2ECC71", 16),
        )
        self.embed.set_footer(text=f"Page {self.current_page//10 + 1}")

    @button(label="Previous", style=discord.ButtonStyle.primary)
    async def prev(self,interaction, button ):
        self.current_page -= 10
        self.embed.description = "\n".join(self.quotes[self.current_page : self.current_page + 10])
        self.embed.set_footer(text=f"Page {self.current_page//10 + 1}")
        await interaction.response.edit_message(embed=self.embed, view=self)
    
    @button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self,interaction, button ):
        self.current_page += 10
        self.embed.description = "\n".join(self.quotes[self.current_page : self.current_page + 10])
        self.embed.set_footer(text=f"Page {self.current_page//10 + 1}")
        await interaction.response.edit_message(embed=self.embed, view=self)
    

@bot.command()
async def show_quotes(ctx):
    view = Quotes(quotes)
    await ctx.send(embed=view.embed, view=view)

@bot.command()
async def pick(ctx, *args):
    # Pick a random item from user inputted strings, each item separated by /
    if len(args) == 0:
        await ctx.send("Please provide a list of items separated by /")
        return
    items = " ".join(args).split("/")
    chosen = items[random.randint(0, len(items) - 1)]
    embed = discord.Embed(
        title="Chosen item",
        description=f"{chosen}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def read_coffee(ctx, arg):
    try:
        current = get_sheet_values(spreadSrv, SHEET_ID, "caffeine!H3:H3")
        current = int(current["values"][0][0])
        chosen_line = quotes[random.randint(0, len(quotes) - 1)]
        num = int(arg)
        value = get_sheet_values(spreadSrv, SHEET_ID, f"caffeine!C{num+2}:F{num+2}")
        values = value["values"]
        if num > current:
            await ctx.send("No entry found")
            return
        embed = discord.Embed(
            title=f"{values[0][0]}",
            color = int("0x2ECC71", 16)
        )
        # check if value[0][3] is empty
        if len(values[0]) == 3:
            values[0].append("None!")
        # embed.add_field(name="Name", value=values[0][0], inline=True)
        embed.add_field(name="Location", value=values[0][1], inline=False)
        embed.add_field(name="Gone?", value=values[0][2], inline=True)
        embed.add_field(name="Notes", value=values[0][3], inline=True)
        embed.set_footer(text=chosen_line)

        await ctx.send(embed=embed)
    except ValueError:
        await ctx.send("Please provide a valid number")
        return

@bot.command()
async def add_coffee(ctx, *args):
    items = " ".join(args).split(";")
    if args == ():
        embed = discord.Embed(
            title="Add coffee!",
            color=int("0xF1C40F", 16),
        )
        embed.add_field(name="Add coffee entry", value="f{used_symbol}add_coffee <name>; <location>; <gone>; <notes>", inline=False)
        embed.add_field(name="name", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="location", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="gone", value="Either \"đã đi\" or \"chưa đi\"", inline=False)
        embed.add_field(name="notes", value="A string of words, no quotes needed", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return
    if len(items) < 3 or len(items) > 4:
        await ctx.send("Please provide the correct number of arguments. Separate each item by \";\"")
        return
    current = get_sheet_values(spreadSrv, SHEET_ID, "caffeine!H3:H3")
    current = int(current["values"][0][0])
    for i in range(len(items)):
        items[i] = items[i].strip()
    if items[2] != "đã đi" and items[2] != "chưa đi":
        await ctx.send("Invalid argument. Please provide either \"đã đi\" or \"chưa đi\"")
        return 
    if items[2] == "đã đi":
        items[2] = "gone gone"
    elif items[2] == "chưa đi":
        items[2] = "no gone"
    if len(items) == 3:
        items.append("")
    try:
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"caffeine!A{current+3}:F{current+3}",
            {"values": [[current + 1, "" ,items[0], items[1], items[2], items[3]]]},
        )
    except Exception as e:
        await ctx.send(f"Failed to write to sheet: {e}")
        return
    embed = discord.Embed(
        title=f"Successfully wrote entry {current+1}",
        description=f"{items[0]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def random_coffee(ctx):
    chosen_line = quotes[random.randint(0, len(quotes) - 1)]
    value = get_sheet_values(spreadSrv, SHEET_ID, "caffeine!H3:H3")
    current = int(value["values"][0][0])
    num = random.randint(3, current+2)
    value = get_sheet_values(spreadSrv, SHEET_ID, f"caffeine!C{num}:F{num}")
    values = value["values"]
    if len(values) == 3:
        values.append(["None!"])
    if values == []:
        await ctx.send("No entry found")
        return
    embed = discord.Embed(
        title=f"{values[0][0]}",
        color = int("0x2ECC71", 16)
    )
    print("works here")
    embed.add_field(name="Location", value=values[0][1], inline=False)
    embed.add_field(name="Gone?", value=values[0][2], inline=True)
    embed.add_field(name="Notes", value=values[0][3], inline=True)
    embed.set_footer(text=chosen_line)
    await ctx.send(embed=embed)
    print("should've sent")
    return

@bot.command()
async def edit_coffee(ctx, *args):
    items = " ".join(args).split(";")
    current = get_sheet_values(spreadSrv, SHEET_ID, "caffeine!H3:H3")
    current = int(current["values"][0][0])
    print(args)
    if (args == ()):
        embed = discord.Embed(
            title="Edit coffee!",
            color=int("0xF1C40F", 16),
        )
        embed.add_field(name="Edit coffee entry", value=f"{used_symbol}edit_coffee <entry number>; <location/gone/notes>; <new value>", inline=False)
        embed.add_field(name="location", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="gone", value="Either \"đã đi\" or \"chưa đi\"", inline=False)
        embed.add_field(name="notes", value="A string of words, no quotes needed", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return
    for i in range(len(items)):
        items[i] = items[i].strip()
    if (int(items[0]) < 1 or int(items[0]) > current):
        await ctx.send("Invalid entry number")
        return
    if items[1] == "location":
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"caffeine!D{int(items[0])+2}",
            {"values": [[items[2]]]},
        )
    elif items[1] == "gone":
        if items[2] != "đã đi" and items[2] != "chưa đi":
            await ctx.send("Invalid argument. Please provide either \"đã đi\" or \"chưa đi\"")
            return 
        if items[2] == "đã đi":
            items[2] = "gone gone"
        elif items[2] == "chưa đi":
            items[2] = "no gone"
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"caffeine!E{int(items[0])+2}",
            {"values": [[items[2]]]},
        )
    elif items[1] == "notes":
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"caffeine!F{int(items[0])+2}",
            {"values": [[items[2]]]},
        )
    else:
        await ctx.send("Invalid argument. Please provide either \"location\", \"gone\", or \"notes\"")
        return
    embed = discord.Embed(
        title=f"Successfully edited entry {items[0]}'s {items[1]}",
        description=f"{items[2]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)
    return

@bot.command()
async def read_coffee_max(ctx):
    value = get_sheet_values(spreadSrv, SHEET_ID, "caffeine!H3:H3")
    embed = discord.Embed(
        title="Coffee!",
        description=f"Coffee count: {value['values'][0][0]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def read_foodies(ctx, num):
    try:
        current = get_sheet_values(spreadSrv, SHEET_ID, "foodies!I3:I3")
        current = int(current["values"][0][0])
        chosen_line = quotes[random.randint(0, len(quotes) - 1)]
        num = int(num)
        value = get_sheet_values(spreadSrv, SHEET_ID, f"foodies!C{num+2}:G{num+2}")
        values = value["values"]
        if num > current:
            await ctx.send("No entry found")
            return
        embed = discord.Embed(
            title=f"{values[0][0]}",
            color = int("0x2ECC71", 16)
        )
        embed.add_field(name="Location", value=values[0][1], inline=False)
        embed.add_field(name="Gone?", value=values[0][3], inline=True)
        embed.add_field(name="Moni", value=values[0][2], inline=True)
        embed.add_field(name="Notes", value=values[0][4], inline=True)
        embed.set_footer(text=chosen_line)
        await ctx.send(embed=embed)
    except ValueError:
        await ctx.send("Please provide a valid number")
        return

@bot.command()
async def add_foodies(ctx, *args):
    items = " ".join(args).split(";")
    if args == ():
        embed = discord.Embed(
            title="Add foodies!",
            color=int("0xF1C40F", 16),
        )
        embed.add_field(name="Add foodies entry", value="f{used_symbol}add_foodies <name>; <location>; <gone>; <moni>; <notes>", inline=False)
        embed.add_field(name="name", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="location", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="gone", value="Either \"đã đi\" or \"chưa đi\"", inline=False)
        embed.add_field(name="moni", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="notes", value="A string of words, no quotes needed", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return
    if len(items) < 4 or len(items) > 5:
        await ctx.send("Please provide the correct number of arguments. Separate each item by \";\"")
        return
    current = get_sheet_values(spreadSrv, SHEET_ID, "foodies!I3:I3")
    current = int(current["values"][0][0])
    for i in range(len(items)):
        items[i] = items[i].strip()
    if items[2] != "đã đi" and items[2] != "chưa đi":
        await ctx.send("Invalid argument. Please provide either \"đã đi\" or \"chưa đi\"")
        return 
    if items[2] == "đã đi":
        items[2] = "gone gone"
    elif items[2] == "chưa đi":
        items[2] = "no gone"
    if len(items) == 4:
        items.append("")
    try:
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"foodies!A{current+3}:G{current+3}",
            {"values": [[current + 1, "" ,items[0], items[1], items[3], items[2], items[4]]]},
        )
    except Exception as e:
        await ctx.send(f"Failed to write to sheet: {e}")
        return
    embed = discord.Embed(
        title=f"Successfully wrote entry {current+1}",
        color=int("0x2ECC71", 16),
    )
    embed.add_field(name="Name", value=items[0], inline=False)
    embed.add_field(name="Location", value=items[1], inline=False)
    embed.add_field(name="Gone?", value=items[2], inline=True)
    embed.add_field(name="Moni", value=items[3], inline=True)
    embed.add_field(name="Notes", value=items[4], inline=True)
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@bot.command()
async def random_foodies(ctx): 
    chosen_line = quotes[random.randint(0, len(quotes) - 1)]
    value = get_sheet_values(spreadSrv, SHEET_ID, "foodies!I3:I3")
    current = int(value["values"][0][0])
    num = random.randint(3, current+2)
    value = get_sheet_values(spreadSrv, SHEET_ID, f"foodies!C{num}:G{num}")
    values = value["values"]
    if len(values) == 4:
        values.append(["None!"])
    if values == []:
        await ctx.send("No entry found")
        return
    embed = discord.Embed(
        title=f"{values[0][0]}",
        color = int("0x2ECC71", 16)
    )
    embed.add_field(name="Location", value=values[0][1], inline=False)
    embed.add_field(name="Gone?", value=values[0][3], inline=True)
    embed.add_field(name="Moni", value=values[0][2], inline=True)
    embed.add_field(name="Notes", value=values[0][4], inline=True)
    embed.set_footer(text=chosen_line)
    await ctx.send(embed=embed)

@bot.command()
async def edit_foodies(ctx, *args):
    items = " ".join(args).split(";")
    current = get_sheet_values(spreadSrv, SHEET_ID, "foodies!I3:I3")
    current = int(current["values"][0][0])
    print(args)
    if (args == ()):
        embed = discord.Embed(
            title="Edit foodies!",
            color=int("0xF1C40F", 16),
        )
        embed.add_field(name="Edit foodies entry", value=f"{used_symbol}edit_foodies <entry number>; <location/gone/moni/notes>; <new value>", inline=False)
        embed.add_field(name="location", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="gone", value="Either \"đã đi\" or \"chưa đi\"", inline=False)
        embed.add_field(name="moni", value="A string of words, no quotes needed", inline=False)
        embed.add_field(name="notes", value="A string of words, no quotes needed", inline=False)
        embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
        await ctx.send(embed=embed)
        return
    for i in range(len(items)):
        items[i] = items[i].strip()
    if (int(items[0]) < 1 or int(items[0]) > current):
        await ctx.send("Invalid entry number")
        return
    if items[1] == "location":
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"foodies!D{int(items[0])+2}",
            {"values": [[items[2]]]},
        )
    elif items[1] == "gone":
        if items[2] != "đã đi" and items[2] != "chưa đi":
            await ctx.send("Invalid argument. Please provide either \"đã đi\" or \"chưa đi\"")
            return 
        if items[2] == "đã đi":
            items[2] = "gone gone"
        elif items[2] == "chưa đi":
            items[2] = "no gone"
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"foodies!E{int(items[0])+2}",
            {"values": [[items[2]]]},
        )
    elif items[1] == "moni":
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"foodies!F{int(items[0])+2}",
            {"values": [[items[2]]]},
        )
    elif items[1] == "notes":
        write_to_sheet(
            spreadSrv,
            SHEET_ID,
            f"foodies!G{int(items[0])+2}",
            {"values": [[items[2]]]},
        )
    else:
        await ctx.send("Invalid argument. Please provide either \"location\", \"gone\", \"moni\", or \"notes\"")
        return
    embed = discord.Embed(
        title=f"Successfully edited entry {items[0]}'s {items[1]}",
        description=f"{items[2]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)
    return

@bot.command()
async def read_foodies_max(ctx):
    value = get_sheet_values(spreadSrv, SHEET_ID, "foodies!I3:I3")
    embed = discord.Embed(
        title="Foodies!",
        description=f"Foodies count: {value['values'][0][0]}",
        color=int("0x2ECC71", 16),
    )
    embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
    await ctx.send(embed=embed)

@tasks.loop(seconds=60)
async def check_reminders():
    print("checking reminders...")
    now = datetime.datetime.now()
    to_remove = []
    for user_id, user_reminders in reminders.items():
        for reminder in user_reminders:
            if reminder["time"] < now:
                user = await bot.fetch_user(int(user_id))
                embed = discord.Embed(
                    title=f"Reminder ID {user_reminders.index(reminder)}",
                    description=reminder["message"],
                    color=int("0x2ECC71", 16),
                )
                embed.set_footer(text=quotes[random.randint(0, len(quotes) - 1)])
                await user.send(embed=embed)
                if reminder["interval"] is not None:
                    reminder["time"] = now + datetime.timedelta(seconds=reminder["interval"])
                else:
                    to_remove.append(reminder)
                
        for reminder in to_remove:
            user_reminders.remove(reminder)
        to_remove.clear()
        
    save_reminders()

bot.run(TOKEN)
