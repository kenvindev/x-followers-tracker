import os
import time
import requests
from datetime import datetime
from database import DatabaseManager

class APISyncService:
    def __init__(self, target_username: str, sync_interval: int = 60):
        """Initialize the API sync service
        
        Args:
            target_username: Twitter username being tracked
            sync_interval: Interval between syncs in seconds (default: 60)
        """
        self.target_username = target_username
        self.sync_interval = sync_interval
        self.should_exit = False
        
        # Get API configuration
        self.api_endpoint = os.getenv('API_ENDPOINT')
        self.api_token = os.getenv('API_TOKEN')
        
        if not self.api_endpoint or not self.api_token:
            raise ValueError("API_ENDPOINT and API_TOKEN must be set in .env file")
            
        # Initialize database manager
        self.db = DatabaseManager()
        
    def sync_follower(self, follower):
        """Sync a single follower to API
        
        Args:
            follower: Follower data dictionary
        
        Returns:
            bool: True if sync was successful
        """
        # Check if we should exit
        if self.should_exit:
            return False
            
        try:
            # Print request details for debugging
            print(f"\nSending request to {self.api_endpoint}")
            print(f"Headers: X-Tool-Request-Token: {self.api_token[:5]}...")
            
            response = requests.post(
                self.api_endpoint,
                headers={
                    'X-Tool-Request-Token': self.api_token,
                    'Content-Type': 'application/json'
                },
                json={
                    'target_username': self.target_username,
                    'follower_username': follower['username'],
                    'follower_display_name': follower['display_name'],
                    'first_seen': follower['first_seen']
                },
                timeout=10
            )
            
            # Print response details for debugging
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            # Check response status first
            if response.status_code == 404:
                print(f"Error: API endpoint not found - {self.api_endpoint}")
                return False
                
            # Try to parse JSON response
            try:
                response_data = response.json()
                print(f"Response data: {response_data}")  # Print response data for debugging
            except ValueError:
                print(f"Error: Invalid JSON response from API (Status: {response.status_code})")
                print(f"Response text: {response.text[:200]}")  # Print first 200 chars of response
                return False
            
            # Check response status and data
            if response.status_code == 200 and response_data.get('success') == True:
                print(f"Successfully synced follower: {follower['username']}")
                return True
            elif response.status_code == 500:
                error_msg = response_data.get('error', 'Internal server error')
                print(f"API server error for {follower['username']}: {error_msg}")
                return False
            else:
                error_msg = response_data.get('error', 'Unknown error')
                print(f"Error syncing follower {follower['username']}: {response.status_code} - {error_msg}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"Connection error: Could not connect to API endpoint")
            return False
        except requests.exceptions.Timeout:
            print(f"Timeout syncing follower {follower['username']}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Network error syncing follower {follower['username']}: {str(e)}")
            return False
        except Exception as e:
            print(f"Error syncing follower {follower['username']}: {str(e)}")
            return False
            
    def stop(self):
        """Stop the service"""
        print("Stopping API sync service...")
        self.should_exit = True
            
    def run(self):
        """Run the API sync service"""
        print(f"Starting API sync service for @{self.target_username}")
        print(f"API endpoint: {self.api_endpoint}")
        
        retry_count = 0
        max_retries = 3
        
        while not self.should_exit:
            try:
                # Exit immediately if flag is set
                if self.should_exit:
                    break
                    
                # Get pending followers
                pending_followers = self.db.get_unsynced_followers(self.target_username)
                
                # Exit if flag was set while getting followers
                if self.should_exit:
                    break
                
                if pending_followers:
                    print(f"\nFound {len(pending_followers)} followers to sync")
                    retry_count = 0
                    
                    # Process each follower
                    for follower in pending_followers:
                        # Exit immediately if flag is set
                        if self.should_exit:
                            break
                            
                        if self.sync_follower(follower):
                            self.db.mark_follower_synced(follower['id'])
                            
                        # Exit if flag was set during sync
                        if self.should_exit:
                            break
                            
                        # Only sleep between followers if not exiting
                        if not self.should_exit and len(pending_followers) > 1:
                            time.sleep(2)
                else:
                    print(".", end="", flush=True)
                
                # Exit if flag was set
                if self.should_exit:
                    break
                    
                # Only sleep if not exiting
                if not self.should_exit:
                    time.sleep(self.sync_interval)
                
            except Exception as e:
                print(f"\nError in sync service: {str(e)}")
                
                # Exit if flag was set during exception handling
                if self.should_exit:
                    break
                    
                retry_count += 1
                
                if retry_count >= max_retries:
                    print(f"Failed after {max_retries} retries. Waiting 5 minutes before continuing...")
                    # Only wait if not exiting
                    if not self.should_exit:
                        time.sleep(300)
                    retry_count = 0
                else:
                    if not self.should_exit:
                        time.sleep(self.sync_interval)
        
        # Final cleanup
        print("\nAPI sync service stopped.") 