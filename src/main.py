import os
from dotenv import load_dotenv
from web_viewer import FollowerWebViewer

def main():
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    target_username = os.getenv('TARGET_USERNAME')
    web_port = int(os.getenv('WEB_PORT', '3000'))
    
    if not target_username:
        print("Error: TARGET_USERNAME not set in .env file")
        return
        
    try:
        # Start web viewer only
        print(f"Starting web viewer for @{target_username}")
        web_viewer = FollowerWebViewer(target_username, web_port)
        web_viewer.run()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {str(e)}")
        
if __name__ == "__main__":
    main() 