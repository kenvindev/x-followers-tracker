import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

class FollowerAPIClient:
    def __init__(self):
        """Initialize the API client with configuration from .env"""
        load_dotenv()
        self.api_endpoint = os.getenv("API_ENDPOINT")
        self.api_token = os.getenv("API_TOKEN")
        
        if not self.api_endpoint or not self.api_token:
            raise ValueError("API_ENDPOINT and API_TOKEN must be set in .env file")
        
        self.headers = {
            "X-Tool-Request-Token": self.api_token,
            "Content-Type": "application/json"
        }
    
    def notify_new_followers(self, target_username: str, new_followers: List[Dict[str, Any]]) -> bool:
        """
        Send new followers data to the API endpoint
        
        Args:
            target_username: The username being monitored
            new_followers: List of new follower data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not new_followers:
            print("No new followers to notify")
            return True
            
        try:
            payload = {
                "target_username": target_username,
                "timestamp": datetime.now().isoformat(),
                "new_followers": new_followers
            }
            
            response = requests.post(
                self.api_endpoint,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                print(f"Successfully notified API about {len(new_followers)} new followers")
                return True
            else:
                print(f"API request failed with status code {response.status_code}")
                #print(f"Response: {response.json}")
                return False
                
        except Exception as e:
            print(f"Error sending API request: {str(e)}")
            return False
    
    def format_follower_data(self, follower_info: str) -> Dict[str, str]:
        """
        Format follower information into API payload format
        
        Args:
            follower_info: String in format "Display Name (@username)"
            
        Returns:
            dict: Formatted follower data
        """
        try:
            # Extract display name and username from the format "Display Name (@username)"
            display_name = follower_info.split(" (@")[0]
            username = follower_info.split("(@")[1].rstrip(")")
            
            return {
                "display_name": display_name,
                "username": username,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error formatting follower data '{follower_info}': {str(e)}")
            return {
                "display_name": follower_info,
                "username": "unknown",
                "timestamp": datetime.now().isoformat()
            } 