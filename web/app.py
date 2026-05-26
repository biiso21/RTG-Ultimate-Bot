from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import discord
from discord.ext import commands
import aiosqlite
import asyncio
import secrets
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# تخزين مؤقت للبوت (سيتم ربطه لاحقاً)
bot_instance = None

def set_bot(bot):
    global bot_instance
    bot_instance = bot

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')

@app.route('/login')
def login():
    """صفحة تسجيل الدخول"""
    return render_template('login.html')

@app.route('/dashboard/<int:guild_id>')
async def dashboard(guild_id):
    """لوحة التحكم الرئيسية"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    guild = bot_instance.get_guild(guild_id)
    if not guild:
        return "Server not found", 404
    
    return render_template('dashboard.html', guild=guild)

@app.route('/api/guilds')
async def api_guilds():
    """API: جلب سيرفرات المستخدم"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    # هذا يحتاج إلى OAuth2 كامل
    # سنبسطها حالياً
    guilds = []
    for guild in bot_instance.guilds:
        guilds.append({
            'id': guild.id,
            'name': guild.name,
            'icon': str(guild.icon.url) if guild.icon else None,
            'member_count': guild.member_count
        })
    
    return jsonify(guilds)

@app.route('/api/economy/<int:guild_id>')
async def api_economy(guild_id):
    """API: جلب بيانات الاقتصاد"""
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute(
            "SELECT user_id, balance FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT 10",
            (guild_id,)
        ) as cursor:
            results = await cursor.fetchall()
    
    data = []
    for user_id, balance in results:
        guild = bot_instance.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None
        data.append({
            'name': member.display_name if member else f"User #{user_id}",
            'balance': balance
        })
    
    return jsonify(data)

@app.route('/api/leveling/<int:guild_id>')
async def api_leveling(guild_id):
    """API: جلب بيانات المستويات"""
    async with aiosqlite.connect("data/rtg_bot.db") as db:
        async with db.execute(
            "SELECT user_id, level, xp FROM leveling WHERE guild_id = ? ORDER BY level DESC LIMIT 10",
            (guild_id,)
        ) as cursor:
            results = await cursor.fetchall()
    
    data = []
    for user_id, level, xp in results:
        guild = bot_instance.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None
        data.append({
            'name': member.display_name if member else f"User #{user_id}",
            'level': level,
            'xp': xp
        })
    
    return jsonify(data)

@app.route('/api/stats/<int:guild_id>')
async def api_stats(guild_id):
    """API: إحصائيات السيرفر"""
    guild = bot_instance.get_guild(guild_id)
    if not guild:
        return jsonify({'error': 'Guild not found'}), 404
    
    return jsonify({
        'name': guild.name,
        'member_count': guild.member_count,
        'channel_count': len(guild.channels),
        'role_count': len(guild.roles),
        'boost_count': guild.premium_subscription_count,
        'created_at': guild.created_at.isoformat()
    })

def run_web_server():
    """تشغيل خادم الويب"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)