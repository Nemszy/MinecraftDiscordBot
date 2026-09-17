import asyncio
import os
import socket
import time
import discord
import psutil
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

SERVER_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
HARDWARE_CHANNEL_ID = int(os.getenv("HARDWARE_CHANNEL_ID", "0"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "25565"))

MINECRAFT_LOG = os.getenv(
    "MINECRAFT_LOG",
    "/home/nemszy/minecraft/logs/latest.log"
)

LOG_STATE_FILE = os.getenv(
    "LOG_STATE_FILE",
    "/home/nemszy/discord/.minecraft_log_state"
)

CHECK_INTERVAL = 300

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set.")

if SERVER_CHANNEL_ID == 0:
    raise RuntimeError("DISCORD_CHANNEL_ID is not set.")

if HARDWARE_CHANNEL_ID == 0:
    raise RuntimeError("HARDWARE_CHANNEL_ID is not set.")

if LOG_CHANNEL_ID == 0:
    raise RuntimeError("LOG_CHANNEL_ID is not set.")

def get_timestamp():
    return datetime.now(timezone.utc).strftime(
        "%d/%m/%Y UTC+0 %H:%M:%S"
    )

def get_log_filename():
    return datetime.now(timezone.utc).strftime(
        "log%d-%m-%Y UTC+0 %H-%M.txt"
    )

def load_log_position():
    if not os.path.exists(LOG_STATE_FILE):
        return 0, 0

    try:
        with open(LOG_STATE_FILE, "r", encoding="utf-8") as file:
            data = file.read().strip()

        inode, position = data.split("|")

        return int(inode), int(position)

    except (ValueError, OSError):
        return 0, 0

def save_log_position(inode, position):
    directory = os.path.dirname(LOG_STATE_FILE)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(LOG_STATE_FILE, "w", encoding="utf-8") as file:
        file.write(f"{inode}|{position}")

def get_new_minecraft_logs():
    if not os.path.exists(MINECRAFT_LOG):
        return None

    stat = os.stat(MINECRAFT_LOG)

    current_inode = stat.st_ino
    current_size = stat.st_size

    saved_inode, saved_position = load_log_position()

    if (
        current_inode != saved_inode
        or current_size < saved_position
    ):
        saved_position = 0

    if current_size == saved_position:
        return None

    with open(
        MINECRAFT_LOG,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as file:
        file.seek(saved_position)

        new_content = file.read()
        new_position = file.tell()

    save_log_position(
        current_inode,
        new_position
    )

    if not new_content.strip():
        return None

    return new_content

async def upload_minecraft_logs():
    channel = bot.get_channel(LOG_CHANNEL_ID)

    if channel is None:
        print("ERROR: Log channel not found.")
        return

    try:
        new_logs = get_new_minecraft_logs()

        if new_logs is None:
            print("No new Minecraft logs.")
            return

        filename = get_log_filename()
        temp_path = f"/tmp/{filename}"

        with open(temp_path, "w", encoding="utf-8") as file:
            file.write("Minecraft Server Log\n")
            file.write(f"Generated: {get_timestamp()}\n")
            file.write(f"Source: {MINECRAFT_LOG}\n")
            file.write("=" * 80)
            file.write("\n\n")
            file.write(new_logs)

        await channel.send(
            content=(
                f"📜 Minecraft server logs "
                f"from `{get_timestamp()}`"
            ),
            file=discord.File(
                temp_path,
                filename=filename
            )
        )

        os.remove(temp_path)

        print(f"Minecraft logs uploaded: {filename}")

    except Exception as error:
        print(
            f"ERROR: Minecraft log upload failed: {error}"
        )

def is_server_online():
    try:
        with socket.create_connection(
            (SERVER_IP, SERVER_PORT),
            timeout=3
        ):
            return True

    except OSError:
        return False

def get_hardware_data():
    core_usage = psutil.cpu_percent(
        interval=1,
        percpu=True
    )

    cpu_usage = (
        sum(core_usage) / len(core_usage)
        if core_usage
        else 0
    )

    temperatures = psutil.sensors_temperatures()

    core_temps = []

    for sensor in temperatures.get("coretemp", []):
        if (
            sensor.current is not None
            and sensor.label.startswith("Core")
        ):
            core_temps.append(sensor.current)

    cpu_temp = (
        max(core_temps)
        if core_temps
        else None
    )

    ram = psutil.virtual_memory()

    ram_used = ram.used / (1024 ** 3)
    ram_total = ram.total / (1024 ** 3)

    storage = psutil.disk_usage("/")

    storage_used = storage.used / (1024 ** 3)
    storage_total = storage.total / (1024 ** 3)

    battery_info = psutil.sensors_battery()

    if battery_info:
        battery = battery_info.percent

        power_status = (
            "Charging / AC"
            if battery_info.power_plugged
            else "Battery"
        )

    else:
        battery = None
        power_status = "N/A"

    uptime_seconds = time.time() - psutil.boot_time()

    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    uptime = f"{days}d {hours}h {minutes}m"

    return {
        "cpu_usage": cpu_usage,
        "core_usage": core_usage,
        "core_temps": core_temps,
        "cpu_temp": cpu_temp,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "ram_percent": ram.percent,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage.percent,
        "battery": battery,
        "power_status": power_status,
        "uptime": uptime
    }

def get_hardware_embed(data):
    core_lines = []

    for index, usage in enumerate(data["core_usage"]):
        if index < len(data["core_temps"]):
            temperature = (
                f"{data['core_temps'][index]:.1f}°C"
            )
        else:
            temperature = "N/A"

        core_lines.append(
            f"Core {index}: {usage:.1f}% | {temperature}"
        )

    core_text = "\n".join(core_lines)

    cpu_temp = (
        f"{data['cpu_temp']:.1f}°C"
        if data["cpu_temp"] is not None
        else "N/A"
    )

    battery = (
        f"{data['battery']:.0f}%"
        if data["battery"] is not None
        else "N/A"
    )

    return discord.Embed(
        title="Hardware Status",
        description=(
            f"CPU Usage: {data['cpu_usage']:.1f}%\n\n"
            f"{core_text}\n\n"
            f"CPU Temp: {cpu_temp}\n\n"
            f"RAM: {data['ram_used']:.1f} / "
            f"{data['ram_total']:.1f} GB "
            f"({data['ram_percent']:.1f}%)\n\n"
            f"Storage: {data['storage_used']:.1f} / "
            f"{data['storage_total']:.1f} GB "
            f"({data['storage_percent']:.1f}%)\n\n"
            f"Battery: {battery}\n"
            f"Power: {data['power_status']}\n\n"
            f"Uptime: {data['uptime']}\n\n"
            f"Time: {get_timestamp()}"
        ),
        color=discord.Color.blue()
    )

def create_server_embed(online):
    if online:
        description = "🟢 Server is Online"
        color = discord.Color.green()
    else:
        description = "🔴 Server is Offline"
        color = discord.Color.red()

    embed = discord.Embed(
        title="Server Status",
        description=description,
        color=color
    )

    embed.add_field(
        name="IP:",
        value=SERVER_IP,
        inline=True
    )

    embed.add_field(
        name="PORT:",
        value=str(SERVER_PORT),
        inline=True
    )

    embed.add_field(
        name="Support",
        value="Please contact support if an issue occurs",
        inline=False
    )

    embed.set_footer(text="Bot v1.0.0")

    return embed

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

last_status = None

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_server_status():
    global last_status

    channel = bot.get_channel(SERVER_CHANNEL_ID)

    if channel is None:
        print("ERROR: Server status channel not found.")
        return

    try:
        online = is_server_online()
        status = "online" if online else "offline"

        if last_status is None:
            last_status = status

            await channel.send(
                embed=create_server_embed(online)
            )

            print(
                f"Minecraft server is "
                f"{status.upper()}."
            )

            return

        if status == last_status:
            return

        last_status = status

        await channel.send(
            embed=create_server_embed(online)
        )

        print(
            f"Minecraft server changed "
            f"to {status.upper()}."
        )

    except Exception as error:
        print(
            f"ERROR: Server monitoring failed: {error}"
        )

@tasks.loop(seconds=CHECK_INTERVAL)
async def send_hardware_status():
    channel = bot.get_channel(HARDWARE_CHANNEL_ID)

    if channel is None:
        print("ERROR: Hardware channel not found.")
        return

    try:
        data = get_hardware_data()
        embed = get_hardware_embed(data)

        await channel.send(embed=embed)

        print("Hardware status sent to Discord.")

    except Exception as error:
        print(
            f"ERROR: Hardware monitoring failed: {error}"
        )

@tasks.loop(seconds=CHECK_INTERVAL)
async def minecraft_log_task():
    try:
        await upload_minecraft_logs()

    except Exception as error:
        print(
            f"ERROR: Minecraft log task failed: {error}"
        )

@check_server_status.before_loop
async def before_server_status():
    await bot.wait_until_ready()

@send_hardware_status.before_loop
async def before_hardware_status():
    await bot.wait_until_ready()

@minecraft_log_task.before_loop
async def before_minecraft_log_task():
    await bot.wait_until_ready()
    await asyncio.sleep(30)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

    if not check_server_status.is_running():
        check_server_status.start()

    if not send_hardware_status.is_running():
        send_hardware_status.start()

    if not minecraft_log_task.is_running():
        minecraft_log_task.start()

bot.run(TOKEN)
