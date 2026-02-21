"""PicoRouter - Web Settings UI."""

import json
import os

SETTINGS_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>PicoRouter Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h2 { color: #555; font-size: 18px; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #666; font-weight: 500; }
        input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        textarea { min-height: 100px; font-family: monospace; }
        button { background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        button:hover { background: #0056b3; }
        button.danger { background: #dc3545; }
        button.danger:hover { background: #c82333; }
        button.success { background: #28a745; }
        button.success:hover { background: #218838; }
        .btn-group { display: flex; gap: 10px; }
        .status { padding: 10px; border-radius: 4px; margin-bottom: 15px; display: none; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .tab-nav { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
        .tab-nav button { background: none; color: #666; padding: 10px 20px; border-radius: 0; }
        .tab-nav button.active { border-bottom: 2px solid #007bff; color: #007bff; margin-bottom: -2px; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        pre { background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
        .api-key { display: flex; gap: 10px; align-items: center; }
        .api-key input { flex: 1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚙️ PicoRouter Settings</h1>
        
        <div id="status" class="status"></div>
        
        <div class="tab-nav">
            <button class="active" onclick="showTab('config')">Configuration</button>
            <button onclick="showTab('profiles')">Profiles</button>
            <button onclick="showTab('keys')">API Keys</button>
            <button onclick="showTab('providers')">Providers</button>
        </div>
        
        <div id="config" class="tab-content active">
            <div class="card">
                <h2>Current Configuration</h2>
                <pre id="config-display">Loading...</pre>
                <div class="btn-group" style="margin-top: 15px;">
                    <button onclick="reloadConfig()">↻ Reload</button>
                    <button class="success" onclick="saveConfig()">💾 Save Changes</button>
                </div>
            </div>
            <div class="card">
                <h2>Edit Configuration (YAML)</h2>
                <textarea id="config-editor" rows="20"></textarea>
            </div>
        </div>
        
        <div id="profiles" class="tab-content">
            <div class="card">
                <h2>Profiles</h2>
                <div id="profiles-list">Loading...</div>
            </div>
        </div>
        
        <div id="keys" class="tab-content">
            <div class="card">
                <h2>API Keys</h2>
                <div id="keys-list">Loading...</div>
            </div>
            <div class="card">
                <h2>Add New Key</h2>
                <div class="form-group">
                    <label>Key Name</label>
                    <input type="text" id="new-key-name" placeholder="mykey">
                </div>
                <div class="form-group">
                    <label>Rate Limit (requests/minute)</label>
                    <input type="number" id="new-key-rate" value="60">
                </div>
                <div class="form-group">
                    <label>Allowed Profiles (comma-separated)</label>
                    <input type="text" id="new-key-profiles" placeholder="chat, coding">
                </div>
                <button onclick="addKey()">➕ Add Key</button>
            </div>
        </div>
        
        <div id="providers" class="tab-content">
            <div class="card">
                <h2>Available Providers</h2>
                <div id="providers-list">Loading...</div>
            </div>
        </div>
    </div>
    
    <script>
        let currentConfig = null;
        
        function showStatus(msg, type) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.className = 'status ' + type;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 3000);
        }
        
        function showTab(name) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-nav button').forEach(b => b.classList.remove('active'));
            document.getElementById(name).classList.add('active');
            event.target.classList.add('active');
        }
        
        async function loadConfig() {
            try {
                const resp = await fetch('/settings/config');
                currentConfig = await resp.json();
                document.getElementById('config-display').textContent = JSON.stringify(currentConfig, null, 2);
                document.getElementById('config-editor').value = JSON.stringify(currentConfig, null, 2);
                loadProfiles();
            } catch(e) {
                showStatus('Failed to load config: ' + e, 'error');
            }
        }
        
        async function reloadConfig() {
            await loadConfig();
            showStatus('Config reloaded', 'success');
        }
        
        async function saveConfig() {
            try {
                const config = JSON.parse(document.getElementById('config-editor').value);
                const resp = await fetch('/settings/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                });
                if (resp.ok) {
                    showStatus('Configuration saved!', 'success');
                    loadConfig();
                } else {
                    const err = await resp.text();
                    showStatus('Save failed: ' + err, 'error');
                }
            } catch(e) {
                showStatus('Invalid JSON: ' + e, 'error');
            }
        }
        
        async function loadProfiles() {
            const profiles = currentConfig?.profiles || {};
            let html = '<table style="width:100%; border-collapse: collapse;">';
            html += '<tr><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Name</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Local</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Cloud</th></tr>';
            for (const [name, profile] of Object.entries(profiles)) {
                const local = profile.local?.provider || '-';
                const cloud = profile.cloud?.providers ? Object.keys(profile.cloud.providers).join(', ') : '-';
                html += `<tr><td style="padding:8px; border-bottom:1px solid #ddd;">${name}</td><td style="padding:8px; border-bottom:1px solid #ddd;">${local}</td><td style="padding:8px; border-bottom:1px solid #ddd;">${cloud}</td></tr>`;
            }
            html += '</table>';
            document.getElementById('profiles-list').innerHTML = html || 'No profiles configured';
        }
        
        async function loadKeys() {
            try {
                const resp = await fetch('/settings/keys');
                const keys = await resp.json();
                let html = '<table style="width:100%; border-collapse: collapse;">';
                html += '<tr><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Name</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Rate Limit</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Profiles</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Actions</th></tr>';
                for (const [name, key] of Object.entries(keys)) {
                    const rate = key.rate_limit || '-';
                    const profiles = (key.profiles || []).join(', ') || 'all';
                    html += `<tr><td style="padding:8px; border-bottom:1px solid #ddd;">${name}</td><td style="padding:8px; border-bottom:1px solid #ddd;">${rate}</td><td style="padding:8px; border-bottom:1px solid #ddd;">${profiles}</td><td style="padding:8px; border-bottom:1px solid #ddd;"><button class="danger" onclick="removeKey('${name}')">🗑️</button></td></tr>`;
                }
                html += '</table>';
                document.getElementById('keys-list').innerHTML = html || 'No keys configured';
            } catch(e) {
                document.getElementById('keys-list').innerHTML = 'Error loading keys: ' + e;
            }
        }
        
        async function addKey() {
            const name = document.getElementById('new-key-name').value;
            const rate = parseInt(document.getElementById('new-key-rate').value);
            const profiles = document.getElementById('new-key-profiles').value.split(',').map(p => p.trim()).filter(p => p);
            
            if (!name) {
                showStatus('Please enter a key name', 'error');
                return;
            }
            
            try {
                const resp = await fetch('/settings/keys', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, rate_limit: rate, profiles})
                });
                if (resp.ok) {
                    showStatus('Key added!', 'success');
                    document.getElementById('new-key-name').value = '';
                    loadKeys();
                } else {
                    showStatus('Failed to add key', 'error');
                }
            } catch(e) {
                showStatus('Error: ' + e, 'error');
            }
        }
        
        async function removeKey(name) {
            if (!confirm('Delete key "' + name + '"?')) return;
            try {
                const resp = await fetch('/settings/keys/' + name, {method: 'DELETE'});
                if (resp.ok) {
                    showStatus('Key removed', 'success');
                    loadKeys();
                } else {
                    showStatus('Failed to remove key', 'error');
                }
            } catch(e) {
                showStatus('Error: ' + e, 'error');
            }
        }
        
        async function loadProviders() {
            try {
                const resp = await fetch('/v1/providers');
                const providers = await resp.json();
                let html = '<table style="width:100%; border-collapse: collapse;">';
                html += '<tr><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Provider</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Endpoint</th></tr>';
                for (const [name, info] of Object.entries(providers)) {
                    html += `<tr><td style="padding:8px; border-bottom:1px solid #ddd;">${name}</td><td style="padding:8px; border-bottom:1px solid #ddd;">${info.endpoint || 'local'}</td></tr>`;
                }
                html += '</table>';
                document.getElementById('providers-list').innerHTML = html;
            } catch(e) {
                document.getElementById('providers-list').innerHTML = 'Error: ' + e;
            }
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            loadConfig();
            loadKeys();
            loadProviders();
        });
    </script>
</body>
</html>
"""


def get_settings_html():
    return SETTINGS_HTML
