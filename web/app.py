# PicoRouter Web Interface

from flask import Flask, request, jsonify, render_template_string
import os

app = Flask(__name__)

# Default to local PicoRouter
PICOROUTER_URL = os.getenv("PICOROUTER_URL", "http://localhost:8080")
PICOROUTER_KEY = os.getenv("PICOROUTER_KEY", "")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PicoRouter</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
               background: #1a1a1a; color: #fff; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #4ade80; margin-bottom: 20px; }
        .chat { background: #2a2a2a; border-radius: 10px; height: 400px; overflow-y: auto; padding: 20px; margin-bottom: 20px; }
        .msg { margin-bottom: 15px; padding: 10px 15px; border-radius: 8px; max-width: 80%; }
        .user { background: #3b82f6; margin-left: auto; }
        .assistant { background: #374151; }
        .input-area { display: flex; gap: 10px; }
        input { flex: 1; padding: 12px; border-radius: 8px; border: none; background: #374151; color: #fff; }
        button { padding: 12px 24px; background: #4ade80; border: none; border-radius: 8px; 
                 cursor: pointer; font-weight: bold; color: #1a1a1a; }
        button:hover { background: #22c55e; }
        .stats { background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .stats span { margin-right: 20px; }
        .error { color: #f87171; padding: 10px; background: #7f1d1d; border-radius: 8px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>🧩 PicoRouter</h1>
    
    <div class="stats">
        <span>Requests: <strong id="reqs">0</strong></span>
        <span>Tokens: <strong id="tokens">0</strong></span>
        <span>Cost: <strong id="cost">$0.00</strong></span>
    </div>
    
    <div class="chat" id="chat"></div>
    
    <div class="input-area">
        <input type="text" id="message" placeholder="Type your message..." onkeypress="handleKey(event)">
        <button onclick="send()">Send</button>
    </div>
    
    <script>
        const API_URL = '{{ api_url }}';
        const API_KEY = '{{ api_key }}';
        
        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = 'msg ' + role;
            div.textContent = content;
            document.getElementById('chat').appendChild(div);
            document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
        }
        
        function handleKey(e) {
            if (e.key === 'Enter') send();
        }
        
        async function send() {
            const input = document.getElementById('message');
            const msg = input.value.trim();
            if (!msg) return;
            
            input.value = '';
            addMessage('user', msg);
            
            try {
                const resp = await fetch(API_URL + '/v1/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + API_KEY
                    },
                    body: JSON.stringify({
                        messages: [{role: 'user', content: msg}]
                    })
                });
                
                if (!resp.ok) throw await resp.text();
                
                const data = await resp.json();
                const reply = data.choices[0].message.content;
                addMessage('assistant', reply);
                
                // Update stats
                const stats = await fetch(API_URL + '/stats').then(r => r.json());
                document.getElementById('reqs').textContent = stats.total_requests;
                document.getElementById('tokens').textContent = stats.total_tokens;
                document.getElementById('cost').textContent = '$' + stats.total_cost_usd.toFixed(4);
                
            } catch(e) {
                addMessage('assistant', 'Error: ' + e);
            }
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML, api_url=PICOROUTER_URL, api_key=PICOROUTER_KEY)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    headers = {"Content-Type": "application/json"}
    if PICOROUTER_KEY:
        headers["Authorization"] = f"Bearer {PICOROUTER_KEY}"
    
    import requests
    resp = requests.post(
        f"{PICOROUTER_URL}/v1/chat/completions",
        json=data,
        headers=headers,
        timeout=120
    )
    return jsonify(resp.json()), resp.status_code


@app.route("/api/stats")
def stats():
    import requests
    resp = requests.get(f"{PICOROUTER_URL}/stats")
    return jsonify(resp.json())


if __name__ == "__main__":
    print(f"🌐 PicoRouter Web Interface")
    print(f"   Point browser to: http://localhost:5000")
    print(f"   Backend: {PICOROUTER_URL}")
    app.run(port=5000, debug=False)
