from flask import Flask, render_template_string, request, redirect
import sqlite3
import threading
from database import DatabaseManager
import math
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from pathlib import Path

class FollowerWebViewer:
    def __init__(self, target_username: str, port: int = 3000):
        self.target_username = target_username
        self.port = port
        self.db = DatabaseManager()
        self.follower_tracker = None
        self.api_sync = None
        self.login_browser = None
        
        # HTML template with login browser button
        self.template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Twitter Follower Tracker</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                th, td {
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }
                th {
                    background-color: #f5f5f5;
                }
                tr:nth-child(even) {
                    background-color: #f9f9f9;
                }
                .pagination {
                    margin: 20px 0;
                    text-align: center;
                }
                .pagination a {
                    padding: 8px 16px;
                    margin: 0 4px;
                    border: 1px solid #ddd;
                    text-decoration: none;
                    color: black;
                }
                .pagination a.active {
                    background-color: #4CAF50;
                    color: white;
                    border: 1px solid #4CAF50;
                }
                .pagination a:hover:not(.active) {
                    background-color: #ddd;
                }
                .filter-box {
                    margin: 20px 0;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                }
                .filter-box input[type="text"] {
                    padding: 8px;
                    margin-right: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                .filter-box button {
                    padding: 8px 15px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                .filter-box button:hover {
                    background-color: #0056b3;
                }
                .control-box {
                    margin: 20px 0;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .start-button {
                    padding: 10px 20px;
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }
                .start-button:hover {
                    background-color: #218838;
                }
                .stop-button {
                    background-color: #dc3545;
                }
                .stop-button:hover {
                    background-color: #c82333;
                }
                .status {
                    margin-left: 10px;
                    font-weight: bold;
                }
                .status.running {
                    color: #28a745;
                }
                .status.stopped {
                    color: #dc3545;
                }
                .button-group {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 10px;
                }
                .login-button {
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }
                .login-button:hover {
                    background-color: #0056b3;
                }
            </style>
        </head>
        <body>
            <h1>Twitter Follower Tracker</h1>
            <h2>Target: @{{ target_username }}</h2>
            
            <div class="control-box">
                <div class="button-group">
                    <form method="post" action="/open_login_browser">
                        <button type="submit" class="login-button">Open Login Browser</button>
                    </form>
                    
                    <form method="post" action="/toggle_checker">
                        {% if checker_running %}
                            <button type="submit" class="start-button stop-button">Stop Checker</button>
                            <span class="status running">Checker is running</span>
                        {% else %}
                            <button type="submit" class="start-button">Start Checker</button>
                            <span class="status stopped">Checker is stopped</span>
                        {% endif %}
                    </form>

                    <form method="post" action="/toggle_api_sync">
                        {% if api_sync_running %}
                            <button type="submit" class="start-button stop-button">Stop API Sync</button>
                            <span class="status running">API Sync is running</span>
                        {% else %}
                            <button type="submit" class="start-button">Start API Sync</button>
                            <span class="status stopped">API Sync is stopped</span>
                        {% endif %}
                    </form>
                </div>
                
                {% if login_browser_open %}
                    <p class="status">Login browser is open. Please use it to log in/out of Twitter.</p>
                {% endif %}
            </div>
            
            <div class="filter-box">
                <form method="get">
                    <input type="text" name="username_filter" value="{{ username_filter }}" placeholder="Filter by username">
                    <button type="submit">Filter</button>
                    {% if username_filter %}
                        <a href="?page=1">Clear Filter</a>
                    {% endif %}
                </form>
            </div>
            
            <h3>Active Followers ({{ total_active }})</h3>
            <table>
                <thead>
                    <tr>
                        <th>Display Name</th>
                        <th>Username</th>
                        <th>First Seen</th>
                        <th>Last Seen</th>
                        <th>API Synced</th>
                    </tr>
                </thead>
                <tbody>
                    {% for follower in active_followers %}
                    <tr>
                        <td>{{ follower.display_name }}</td>
                        <td>@{{ follower.username }}</td>
                        <td>{{ follower.first_seen }}</td>
                        <td>{{ follower.last_seen }}</td>
                        <td>{{ 'Yes' if follower.is_synced else 'No' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="pagination">
                {% if total_pages > 1 %}
                    {% if page > 1 %}
                        <a href="?page={{ page - 1 }}&username_filter={{ username_filter }}">&laquo; Previous</a>
                    {% endif %}
                    
                    {% for p in range(1, total_pages + 1) %}
                        <a href="?page={{ p }}&username_filter={{ username_filter }}" 
                           {% if p == page %}class="active"{% endif %}>
                            {{ p }}
                        </a>
                    {% endfor %}
                    
                    {% if page < total_pages %}
                        <a href="?page={{ page + 1 }}&username_filter={{ username_filter }}">Next &raquo;</a>
                    {% endif %}
                {% endif %}
            </div>
            
            <h3>Recent Scans</h3>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Total Followers</th>
                        <th>New Followers</th>
                        <th>Batch Number</th>
                    </tr>
                </thead>
                <tbody>
                    {% for scan in recent_scans %}
                    <tr>
                        <td>{{ scan.timestamp }}</td>
                        <td>{{ scan.total_followers }}</td>
                        <td>{{ scan.new_followers }}</td>
                        <td>{{ scan.batch_number }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </body>
        </html>
        """
        
    def get_follower_data(self, page=1, per_page=25, username_filter=None):
        """Get follower data with pagination and filtering"""
        conn = sqlite3.connect('data/followers.db')
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            
            # Base query
            query = """
                SELECT id, username, display_name, first_seen, last_seen, api_synced as is_synced
                FROM followers 
                WHERE target_username = ? AND is_active = 1
            """
            params = [self.target_username]
            
            # Add username filter if provided
            if username_filter:
                query += " AND username LIKE ?"
                params.append(f"%{username_filter}%")
                
            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query})"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Add pagination
            query += " ORDER BY first_seen DESC LIMIT ? OFFSET ?"
            params.extend([per_page, (page - 1) * per_page])
            
            # Get paginated results
            cursor.execute(query, params)
            followers = cursor.fetchall()
            
            # Format timestamps
            formatted_followers = []
            for follower in followers:
                follower_dict = dict(follower)
                # Convert timestamps to readable format
                for field in ['first_seen', 'last_seen']:
                    if follower_dict[field]:
                        dt = datetime.fromisoformat(follower_dict[field].replace('Z', '+00:00'))
                        follower_dict[field] = dt.strftime('%Y-%m-%d %H:%M:%S')
                formatted_followers.append(follower_dict)
            
            # Get recent scans
            cursor.execute("""
                SELECT 
                    timestamp,
                    total_followers,
                    new_followers,
                    batch_number 
                FROM scans 
                WHERE target_username = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            """, [self.target_username])
            recent_scans = cursor.fetchall()
            
            # Format scan timestamps
            formatted_scans = []
            for scan in recent_scans:
                scan_dict = dict(scan)
                if scan_dict['timestamp']:
                    dt = datetime.fromisoformat(scan_dict['timestamp'].replace('Z', '+00:00'))
                    scan_dict['timestamp'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                formatted_scans.append(scan_dict)
            
            return {
                'active_followers': formatted_followers,
                'total_active': total_count,
                'recent_scans': formatted_scans,
                'total_pages': math.ceil(total_count / per_page)
            }
            
        finally:
            conn.close()
            
    def run(self):
        """Run the web viewer"""
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 25))
            username_filter = request.args.get('username_filter', '')
            
            data = self.get_follower_data(page, per_page, username_filter)
            checker_running = self.follower_tracker is not None and hasattr(self.follower_tracker, 'should_exit') and not self.follower_tracker.should_exit
            api_sync_running = self.api_sync is not None and hasattr(self.api_sync, 'should_exit') and not self.api_sync.should_exit
            login_browser_open = self.login_browser is not None
            
            return render_template_string(
                self.template,
                target_username=self.target_username,
                active_followers=data['active_followers'],
                total_active=data['total_active'],
                recent_scans=data['recent_scans'],
                page=page,
                per_page=per_page,
                total_pages=data['total_pages'],
                username_filter=username_filter,
                checker_running=checker_running,
                api_sync_running=api_sync_running,
                login_browser_open=login_browser_open
            )
            
        @app.route('/open_login_browser', methods=['POST'])
        def open_login_browser():
            # Close existing login browser if any
            if self.login_browser:
                try:
                    self.login_browser.quit()
                except:
                    pass
                    
            # Use Chrome profile directory
            profile_dir = Path("data/chrome_profiles")
            if not profile_dir.exists():
                profile_dir.mkdir(parents=True, exist_ok=True)
                
            # Profile settings
            options = Options()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--no-sandbox')
            options.add_argument(f'--user-data-dir={profile_dir.absolute()}')
            options.add_argument('--profile-directory=Default')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Additional settings to avoid detection
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-first-run')
            options.add_argument('--no-service-autorun')
            options.add_argument('--password-store=basic')
            
            try:
                # Open new browser and navigate to Twitter
                self.login_browser = webdriver.Chrome(options=options)
                self.login_browser.get('https://x.com/login')
                print("Opened login browser with profile")
            except Exception as e:
                print(f"Error opening login browser: {str(e)}")
                if self.login_browser:
                    self.login_browser.quit()
                self.login_browser = None
            
            return redirect('/')
            
        @app.route('/toggle_checker', methods=['POST'])
        def toggle_checker():
            # Close login browser if open
            if self.login_browser:
                try:
                    self.login_browser.quit()
                except:
                    pass
                self.login_browser = None
            
            if self.follower_tracker is None or self.follower_tracker.should_exit:
                # Start the checker only
                from twitter_checker import TwitterFollowerTracker
                
                # Initialize follower tracker
                self.follower_tracker = TwitterFollowerTracker(self.target_username)
                
                def run_checker():
                    self.follower_tracker.run()
                
                # Start checker in a separate thread
                checker_thread = threading.Thread(target=run_checker)
                checker_thread.daemon = True
                checker_thread.start()
                
                print("Started follower checker")
            else:
                # Stop the checker
                if self.follower_tracker:
                    self.follower_tracker.stop()
                    self.follower_tracker = None
                    print("Stopped follower checker")
            
            return redirect('/')

        @app.route('/toggle_api_sync', methods=['POST'])
        def toggle_api_sync():
            if self.api_sync is None or self.api_sync.should_exit:
                # Start API sync
                from api_sync import APISyncService
                
                # Initialize API sync service
                self.api_sync = APISyncService(self.target_username)
                
                def run_api_sync():
                    self.api_sync.run()
                
                # Start API sync in a separate thread
                api_thread = threading.Thread(target=run_api_sync)
                api_thread.daemon = True
                api_thread.start()
                
                print("Started API sync service")
            else:
                # Stop API sync
                if self.api_sync:
                    self.api_sync.stop()
                    self.api_sync = None
                    print("Stopped API sync service")
            
            return redirect('/')
            
        app.run(host='127.0.0.1', port=self.port, debug=False) 