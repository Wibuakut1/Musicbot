import discord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
from flask import Flask # TAMBAHKAN INI
from threading import Thread # TAMBAHKAN INI

# --- Bagian Web Server untuk UptimeRobot ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
  app.run(host='0.0.0.0', port=8080)

def start_web_server_thread():
    t = Thread(target=run_web_server)
    t.start()
# -------------------------------------------


# Muat variabel dari Secrets (Environment Variables)
load_dotenv()

# --- Konfigurasi ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

if not all([DISCORD_TOKEN, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET]):
    print("Error: Pastikan semua variabel (DISCORD_TOKEN, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET) sudah diatur di menu 'Secrets'.")
    exit()

# Inisialisasi bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

# Inisialisasi koneksi ke Spotify API
try:
    auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    print("Berhasil terhubung ke Spotify.")
except Exception as e:
    print(f"Gagal terhubung ke Spotify: {e}")
    sp = None

# Opsi untuk yt-dlp dan FFmpeg
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

def search_youtube(query):
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        except Exception:
            return None
    return {'url': info['url'], 'title': info['title']}

@bot.event
async def on_ready():
    print(f'Bot telah login sebagai {bot.user}')
    print('------')

@bot.slash_command(name="play", description="Memutar lagu dari Spotify (link) atau YouTube (judul).")
async def play(ctx: discord.ApplicationContext, query: str):
    if not ctx.author.voice:
        await ctx.respond("Kamu harus berada di voice channel!", ephemeral=True)
        return
    voice_channel = ctx.author.voice.channel
    if ctx.voice_client and ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)
    elif not ctx.voice_client:
        try:
            await voice_channel.connect()
        except asyncio.TimeoutError:
            await ctx.respond("Gagal terhubung ke voice channel.", ephemeral=True)
            return
    await ctx.defer()
    search_query, song_title = "", ""
    if "open.spotify.com/track" in query and sp:
        try:
            track_info = sp.track(query)
            artist_name, track_name = track_info['artists'][0]['name'], track_info['name']
            search_query, song_title = f"{track_name} {artist_name}", f"{track_name} by {artist_name}"
        except Exception:
            await ctx.followup.send("Gagal mendapatkan info lagu dari link Spotify.")
            return
    else:
        search_query, song_title = query, query
    video = search_youtube(search_query)
    if video is None:
        await ctx.followup.send(f"Maaf, tidak bisa menemukan lagu: {song_title}")
        return
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        ctx.voice_client.stop()
    ctx.voice_client.play(discord.FFmpegPCMAudio(video['url'], **FFMPEG_OPTIONS))
    await ctx.followup.send(f'🎶 **Now Playing:** {video["title"]}')

@bot.slash_command(name="leave", description="Membuat bot keluar dari voice channel.")
async def leave(ctx: discord.ApplicationContext):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.respond("Bye! Sampai jumpa lagi.", ephemeral=True)
    else:
        await ctx.respond("Aku sedang tidak ada di voice channel.", ephemeral=True)

# Jalankan server web dan bot
if sp:
    start_web_server_thread() # TAMBAHKAN INI: Jalankan web server di thread terpisah
    bot.run(DISCORD_TOKEN)
else:
    print("Bot tidak dapat dijalankan karena gagal terhubung ke Spotify.")
            
