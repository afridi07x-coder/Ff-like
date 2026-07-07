import asyncio
import re
import json
import os
from datetime import datetime
from flask import Flask, request, jsonify
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import threading
import time

# ============= CONFIGURATION =============
API_ID = 34635054
API_HASH = "b8e93ca4f3abdcba65cc020504f82f08"
GROUP_USERNAME = "freefirelikegroup2"
BOT_USERNAME = "ZERO2LIKEBOT"

SESSION_STRING = os.environ.get("TG_SESSION_STRING", "1BVtsOL0BuzSnVOKtWU8EImp8JcoyfGGk0jAkFEYIHLESMp7EaSE_938U8wEB2ULm_AuARm26fDAFbZ0SBvJmF-lg1jl1by_lxPI4QCUYsTSvm58Q8skyvd6cgAj1uGONykTFa0xHr87CI2nwKo1cqdrBZZdwGCxm2Izk13edqIKN0I997J6Kt8QeaoOhPj8gSwt_67dvJFlLQow_OTu0t_UOSGsZvIoxfitZyL2gaXUI1XA9q4RJaFNwvPDNVCEnQvA6Zt7-U9Hi6w9FitQzxa8M4-FNuKsxrXYngS1lwdZHRDIKlj-QBR87_OFjdCf7Et-lYOr0xp1t0ED0MPsToS4iAUn4ouQ=")

API_KEY = "felix56"
RESULTS_FILE = "web_api_results.json"

# ============= FLASK APP =============
app = Flask(__name__)
telegram_client = None
group_entity = None
bot_entity = None
results = []
processing_lock = threading.Lock()

# ============= LOAD RESULTS =============
def load_results():
    global results
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"📊 Loaded {len(results)} existing results")
        except:
            results = []

def save_results():
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(results)} results to {RESULTS_FILE}")

load_results()

# ============= UNICODE NORMALIZATION =============
_UNICODE_NORMALIZE_MAP = {
    **{chr(0x1D400 + i): chr(0x41 + i) for i in range(26)},
    **{chr(0x1D41A + i): chr(0x41 + i) for i in range(26)},
    'ᴀ': 'A', 'ʙ': 'B', 'ᴄ': 'C', 'ᴅ': 'D', 'ᴇ': 'E', 'ғ': 'F', 'ɢ': 'G',
    'ʜ': 'H', 'ɪ': 'I', 'ᴊ': 'J', 'ᴋ': 'K', 'ʟ': 'L', 'ᴍ': 'M', 'ɴ': 'N',
    'ᴏ': 'O', 'ᴘ': 'P', 'ǫ': 'Q', 'ʀ': 'R', 's': 'S',
    'ᴛ': 'T', 'ᴜ': 'U', 'ᴠ': 'V', 'ᴡ': 'W', 'ʏ': 'Y', 'ᴢ': 'Z',
}
_UNICODE_NORMALIZE_TABLE = str.maketrans(_UNICODE_NORMALIZE_MAP)

def normalize_text(text):
    return text.translate(_UNICODE_NORMALIZE_TABLE)

# ============= PARSE BOT RESPONSE =============
def parse_bot_response(text, uid, server):
    """
    Parse bot's response and return CLEAN JSON with EXACT fields only.
    """
    
    text_original = text
    text_upper = normalize_text(text_original).upper()
    
    def extract(patterns, source=text_original, flags=re.IGNORECASE):
        for pattern in patterns:
            match = re.search(pattern, source, flags)
            if match:
                return match.group(1).strip()
        return None
    
    def clean_name(name):
        if name:
            name = re.sub(r'^[\*\s]+', '', name)
            name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', name)
            return name.strip()
        return "Unknown"
    
    def clean_number(value):
        if value:
            return value.replace(',', '').strip()
        return None
    
    # ========================================
    # 1. SUCCESS - VIP Like Successful
    # ========================================
    if 'VIP LIKE SUCCESSFULL' in text_upper or 'LIKES SENT' in text_upper or '𝐕ɪᴘ 𝐋ɪᴋᴇ sᴜᴄᴄᴇssғᴜʟʟ' in text_upper:
        name = extract([
            r'👑\s*𝐅𝐅\s*𝐍ᴀᴍᴇ:\s*(.+?)(?:\n|$)',
            r'👑\s*FF\s*NAME:\s*(.+?)(?:\n|$)',
            r'𝐅𝐅\s*𝐍ᴀᴍᴇ:\s*(.+?)(?:\n|$)',
            r'FF NAME:\s*(.+?)(?:\n|$)',
            r'NAME:\s*(.+?)(?:\n|$)'
        ])
        
        uid_val = extract([
            r'🆔\s*𝐔ɪᴅ:\s*(\d+)',
            r'🆔\s*UID:\s*(\d+)',
            r'𝐔ɪᴅ:\s*(\d+)',
            r'ID:\s*(\d+)',
            r'UID:\s*(\d+)'
        ])
        
        region = extract([
            r'🌍\s*𝐑ᴇɢɪᴏɴ:\s*([A-Za-z]+)',
            r'🌍\s*REGION:\s*([A-Za-z]+)',
            r'𝐑ᴇɢɪᴏɴ:\s*([A-Za-z]+)',
            r'REGION:\s*([A-Za-z]+)'
        ])
        
        likes_sent = extract([
            r'💖\s*𝐋ɪᴋᴇs\s*sᴇɴᴛ:\s*([\d,]+)',
            r'💖\s*LIKES\s*SENT:\s*([\d,]+)',
            r'𝐋ɪᴋᴇs\s*sᴇɴᴛ:\s*([\d,]+)',
            r'LIKES SENT:\s*([\d,]+)'
        ])
        
        before = extract([
            r'📊\s*𝐁ᴇғᴏʀᴇ:\s*([\d,]+)',
            r'📊\s*BEFORE:\s*([\d,]+)',
            r'𝐁ᴇғᴏʀᴇ:\s*([\d,]+)',
            r'BEFORE:\s*([\d,]+)'
        ])
        
        after = extract([
            r'📊\s*𝐀ғᴛᴇʀ:\s*([\d,]+)',
            r'📊\s*AFTER:\s*([\d,]+)',
            r'𝐀ғᴛᴇʀ:\s*([\d,]+)',
            r'AFTER:\s*([\d,]+)'
        ])
        
        credits_left = extract([
            r'🌟\s*𝐒ᴛᴀᴛᴜs:\s*𝐂ʀᴇᴅɪᴛs\s*ʟᴇғᴛ:\s*([\d,]+)',
            r'🌟\s*STATUS:\s*CREDITS\s*LEFT:\s*([\d,]+)',
            r'𝐂ʀᴇᴅɪᴛs\s*ʟᴇғᴛ:\s*([\d,]+)',
            r'CREDITS LEFT:\s*([\d,]+)'
        ])
        
        return {
            'success': True,
            'message': 'Likes Sent Successfully',
            'player_name': clean_name(name) if name else 'Unknown',
            'uid': uid_val if uid_val else str(uid),
            'region': region.upper() if region else 'Unknown',
            'likes_sent': int(clean_number(likes_sent)) if likes_sent else 0,
            'before': int(clean_number(before)) if before else 0,
            'after': int(clean_number(after)) if after else 0,
            'credits_left': int(clean_number(credits_left)) if credits_left else 0
        }
    
    # ========================================
    # 2. MAX LIKED - Account already max liked
    # ========================================
    elif 'ACCOUNT ALREADY MAX LIKED' in text_upper or 'MAX LIKED TODAY' in text_upper or 'ALREADY MAX' in text_upper or '𝐀ᴄᴄᴏᴜɴᴛ ᴀʟʀᴇᴀᴅʏ ᴍᴀx ʟɪᴋᴇᴅ ᴛᴏᴅᴀʏ' in text_upper:
        name = extract([
            r'👑\s*𝐅𝐅\s*𝐍ᴀᴍᴇ:\s*(.+?)(?:\n|$)',
            r'👑\s*FF\s*NAME:\s*(.+?)(?:\n|$)',
            r'𝐅𝐅\s*𝐍ᴀᴍᴇ:\s*(.+?)(?:\n|$)',
            r'FF NAME:\s*(.+?)(?:\n|$)'
        ])
        
        uid_val = extract([
            r'🆔\s*𝐔ɪᴅ:\s*(\d+)',
            r'🆔\s*UID:\s*(\d+)',
            r'𝐔ɪᴅ:\s*(\d+)',
            r'ID:\s*(\d+)'
        ])
        
        if not uid_val:
            uid_match = re.search(r'(\d{10,11})', text_original)
            if uid_match:
                uid_val = uid_match.group(1)
        
        region = extract([
            r'🌍\s*𝐑ᴇɢɪᴏɴ:\s*([A-Za-z]+)',
            r'🌍\s*REGION:\s*([A-Za-z]+)',
            r'𝐑ᴇɢɪᴏɴ:\s*([A-Za-z]+)',
            r'REGION:\s*([A-Za-z]+)'
        ])
        
        current_likes = extract([
            r'💖\s*𝐂ᴜʀʀᴇɴᴛ\s*ʟɪᴋᴇs:\s*([\d,]+)',
            r'💖\s*CURRENT\s*LIKES:\s*([\d,]+)',
            r'𝐂ᴜʀʀᴇɴᴛ\s*ʟɪᴋᴇs:\s*([\d,]+)',
            r'CURRENT LIKES:\s*([\d,]+)'
        ])
        
        return {
            'success': False,
            'message': "Account already reached today's maximum likes.",
            'player_name': clean_name(name) if name else 'Unknown',
            'uid': uid_val if uid_val else str(uid),
            'region': region.upper() if region else 'Unknown',
            'current_likes': int(clean_number(current_likes)) if current_likes else 0,
            'credit_restored': True
        }
    
    # ========================================
    # 3. FAILED - Like Request Failed
    # ========================================
    elif 'LIKE REQUEST FAILD' in text_upper or 'REQUEST FAILD' in text_upper or '𝐋ɪᴋᴇ 𝐑ᴇǫᴜᴇsᴛ ғᴀɪʟᴅ' in text_upper:
        uid_val = extract([
            r'🆔\s*𝐔ɪᴅ:\s*(\d+)',
            r'🆔\s*UID:\s*(\d+)',
            r'𝐔ɪᴅ:\s*(\d+)',
            r'UID:\s*(\d+)'
        ])
        
        region = extract([
            r'🌍\s*𝐑ᴇɢɪᴏɴ:\s*([A-Za-z]+)',
            r'🌍\s*REGION:\s*([A-Za-z]+)',
            r'𝐑ᴇɢɪᴏɴ:\s*([A-Za-z]+)',
            r'REGION:\s*([A-Za-z]+)'
        ])
        
        return {
            'success': False,
            'message': 'Like request failed. Please check the UID and region.',
            'uid': uid_val if uid_val else str(uid),
            'region': region.upper() if region else 'Unknown'
        }
    
    # ========================================
    # UNKNOWN / UNRECOGNIZED RESPONSE
    # ========================================
    return {
        'success': False,
        'message': 'Unknown response',
        'uid': str(uid),
        'region': 'Unknown'
    }

# ============= SEND LIKE COMMAND =============
async def send_like_command(server, uid):
    """Send like command to group and wait for response"""
    global results
    
    bot_entity_local = bot_entity
    
    command = f"/like {server} {uid}"
    sent_msg = await telegram_client.send_message(group_entity, command)
    print(f"📤 Sent: {command} (id={sent_msg.id})")
    
    start_time = time.time()
    seen_ids = set()
    max_wait_seconds = 35
    
    while time.time() - start_time < max_wait_seconds:
        try:
            async for msg in telegram_client.iter_messages(group_entity, limit=10):
                if msg.sender_id != bot_entity_local.id or not msg.text:
                    continue
                
                if msg.id <= sent_msg.id:
                    continue
                
                if msg.id in seen_ids:
                    continue
                seen_ids.add(msg.id)
                
                msg_text_norm_upper = normalize_text(msg.text).upper()
                has_keyword = "LIKES" in msg_text_norm_upper or "FAILD" in msg_text_norm_upper or "MAX" in msg_text_norm_upper
                if uid in msg.text and has_keyword:
                    data = parse_bot_response(msg.text, uid, server)
                    return data
        except:
            pass
        await asyncio.sleep(0.3)
    
    print(f"⚠️ No response for UID: {uid}")
    return {
        'success': False,
        'message': 'No response from bot',
        'uid': str(uid),
        'region': 'Unknown'
    }

# ============= FLASK API ENDPOINTS =============
@app.route('/like', methods=['GET'])
def handle_like():
    key = request.args.get('key')
    server = request.args.get('server')
    uid = request.args.get('uid')
    
    if key != API_KEY:
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401
    
    if not server or not uid:
        return jsonify({'success': False, 'error': 'Missing parameters: server and uid required'}), 400
    
    if not uid.isdigit():
        return jsonify({'success': False, 'error': 'UID must be numeric'}), 400
    
    result = asyncio.run_coroutine_threadsafe(
        send_like_command(server.lower(), uid),
        loop
    )
    
    try:
        data = result.result(timeout=40)
        with processing_lock:
            results.append(data)
            save_results()
        return jsonify(data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/like/bulk', methods=['POST'])
def handle_bulk_like():
    try:
        data = request.get_json()
        key = data.get('key')
        requests_list = data.get('requests', [])
        
        if key != API_KEY:
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        if not requests_list:
            return jsonify({'success': False, 'error': 'No requests provided'}), 400
        
        results_list = []
        for req in requests_list:
            server = req.get('server')
            uid = req.get('uid')
            
            if not server or not uid:
                continue
            
            result = asyncio.run_coroutine_threadsafe(
                send_like_command(server.lower(), str(uid)),
                loop
            )
            
            try:
                res = result.result(timeout=40)
                results_list.append(res)
                with processing_lock:
                    results.append(res)
                save_results()
            except:
                results_list.append({
                    'success': False,
                    'message': 'Timeout or error',
                    'uid': str(uid),
                })
        
        return jsonify({
            'success': True,
            'count': len(results_list),
            'results': results_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    key = request.args.get('key')
    if key != API_KEY:
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401
    
    total = len(results)
    success = sum(1 for r in results if r.get('success') == True)
    failed = sum(1 for r in results if r.get('success') == False)
    total_likes = sum(r.get('likes_sent', 0) for r in results if r.get('success') == True)
    
    return jsonify({
        'success': True,
        'stats': {
            'total_requests': total,
            'success': success,
            'failed': failed,
            'total_likes': total_likes,
            'success_rate': f"{(success/total*100 if total > 0 else 0):.1f}%"
        }
    })

@app.route('/results', methods=['GET'])
def get_results():
    key = request.args.get('key')
    if key != API_KEY:
        return jsonify({'success': False, 'error': 'Invalid API key'}), 401
    
    limit = request.args.get('limit', default=100, type=int)
    return jsonify({
        'success': True,
        'total': len(results),
        'results': results[-limit:]
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'success': True,
        'status': 'healthy',
        'total_results': len(results),
        'connected': telegram_client is not None
    })

# ============= TELEGRAM CLIENT SETUP =============
loop = None

async def setup_telegram():
    global telegram_client, group_entity, bot_entity, loop
    
    loop = asyncio.get_event_loop()
    
    if SESSION_STRING == "PASTE_YOUR_SESSION_STRING_HERE":
        print("❌ No session string set. Set TG_SESSION_STRING env var or edit SESSION_STRING in the script.")
        return
    
    telegram_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    await telegram_client.start()
    print("✅ Telegram client started (logged in via session string)!")
    
    try:
        group_entity = await telegram_client.get_entity(GROUP_USERNAME)
        print(f"✅ Found group: {GROUP_USERNAME}")
    except Exception as e:
        print(f"❌ Cannot find group: {e}")
        return
    
    try:
        bot_entity = await telegram_client.get_entity(BOT_USERNAME)
        print(f"✅ Found bot: {BOT_USERNAME}")
    except Exception as e:
        print(f"❌ Cannot find bot: {e}")
        return
    
    print("✅ API Server is ready!")
    await telegram_client.run_until_disconnected()

# ============= MAIN =============
if __name__ == '__main__':
    print("="*50)
    print("🚀 Web API Like Server")
    print("="*50)
    print(f"📍 Endpoint: http://localhost:5000/like")
    print(f"🔑 API Key: {API_KEY}")
    print(f"📝 Example: http://localhost:5000/like?key={API_KEY}&server=ind&uid=1234567890")
    print("="*50)
    
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    try:
        asyncio.run(setup_telegram())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")