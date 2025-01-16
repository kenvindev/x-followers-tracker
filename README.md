# X Follower Tracker

An automated tool for tracking and managing Twitter/X followers with a web interface.

## Features

- 🔄 Automatically track Twitter/X followers with configurable scan intervals
- 💾 Store follower data locally in SQLite database
- 🌐 Web interface for viewing and managing the tracking process
- 🔍 Filter and search through follower history
- 📊 View statistics and recent scan history
- 🔄 API synchronization for new followers
- 👥 Track active/inactive followers
- 🔐 Secure Chrome profile management for login sessions

## Requirements

- Windows OS
- Python 3.8 or higher
- Chrome browser
- Logged-in Twitter/X account

## Quick Setup

1. Clone this repository
2. Run `run.bat` - this will:
   - Create virtual environment
   - Install dependencies
   - Set up configuration
   - Create necessary directories
3. Open the web interface at `http://127.0.0.1:3000`
4. Click "Open Login Browser" to log in to your Twitter/X account
5. Click "Start Checker" to begin tracking followers

## Configuration

Edit `.env` file with your settings:
```
TARGET_USERNAME=your_target_username
SCAN_INTERVAL_MINUTES=1
API_ENDPOINT=your_api_endpoint
API_TOKEN=your_api_token
WEB_PORT=3000
```

## Web Interface Features

- Start/Stop follower checking
- Open login browser for account management
- View and filter follower list
- Track scan history and statistics
- Monitor API sync status

## Data Storage

- All data is stored in `data/followers.db` (SQLite database)
- Chrome profiles are saved in `data/chrome_profiles`
- Ensures persistence of login sessions and follower data

## Notes

- The login browser uses a saved Chrome profile to maintain login state
- You can switch accounts by:
  1. Stopping the checker
  2. Opening login browser
  3. Logging out and in with new account
  4. Starting the checker again
- The checker will stop automatically after finding multiple consecutive existing followers
- API sync runs automatically alongside the follower checker

## Troubleshooting

- If login issues occur, try:
  1. Stop the checker
  2. Open login browser
  3. Clear cookies/cache if needed
  4. Log in again
  5. Restart the checker
- If the web interface is not accessible, check if port 3000 is available
- Check the console output for detailed error messages and status updates 
