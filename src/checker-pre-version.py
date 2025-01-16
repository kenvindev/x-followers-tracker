import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from pathlib import Path
from api_client import FollowerAPIClient
from database import FollowerDatabase

class TwitterFollowerTracker:
    def __init__(self, target_username: str, scan_interval: int):
        """Initialize the Twitter follower tracker
        
        Args:
            target_username: Twitter username to track
            scan_interval: Interval between scans in minutes
        """
        self.target_username = target_username
        self.scan_interval = scan_interval
        self.driver = None
        self.wait = None
        self.db = FollowerDatabase()  # Initialize database connection
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with all necessary options"""
        # Setup Chrome profile directory
        user_data_dir = os.path.join(os.getcwd(), 'chrome_profile')
        Path(user_data_dir).mkdir(exist_ok=True)
        
        # Setup Chrome driver
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        
        # Add mobile emulation
        mobile_emulation = {
            "deviceMetrics": { "width": 360, "height": 640, "pixelRatio": 3.0 },
            "userAgent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        # Add other options
        options.add_argument(f'--user-data-dir={user_data_dir}')
        options.add_argument('--profile-directory=Default')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-extensions')
        options.add_argument('--start-maximized')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def save_progress(self, followers):
        """Save new followers to database
        
        Args:
            followers: List of follower usernames
        """
        try:
            # Add followers to database
            self.db.add_followers(self.target_username, followers)
            print(f"Saved {len(followers)} followers to database")
            
        except Exception as e:
            print(f"Error saving followers: {str(e)}")
    
    def load_previous_results(self) -> set:
        """Load all previously saved results from database"""
        return self.db.get_all_followers(self.target_username)
    
    def check_login(self):
        """Check and handle login status"""
        self.driver.get('https://x.com/home')
        
        try:
            login_button = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="loginButton"]')))
            print("Please login manually in the browser window...")
            self.wait = WebDriverWait(self.driver, 300)
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]')))
            print("Login detected!")
        except TimeoutException:
            print("Using existing login session...")
    
    def scroll_to_bottom(self):
        """Scroll to bottom of page and wait for content to load"""
        print("Starting to scroll and load followers...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        processed_positions = set()  # Lưu các vị trí đã xử lý
        max_count = 0
        no_new_count = 0
        MAX_NO_NEW = 5
        scroll_pause_time = 2
        scroll_step = 300
        
        # Initialize batch variables
        current_batch = set()
        batch_size = 100
        batch_num = 1
        all_followers = set()
        
        while True:
            try:
                # Get current scroll position
                current_position = self.driver.execute_script("return window.pageYOffset")
                
                # Get all visible followers at current position
                cells = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="UserCell"]')
                current_count = len(cells)
                
                # Process only cells that are currently visible and not processed
                visible_cells = []
                for cell in cells:
                    try:
                        # Check if cell is visible in viewport
                        is_visible = self.driver.execute_script("""
                            var elem = arguments[0];
                            var rect = elem.getBoundingClientRect();
                            return (
                                rect.top >= 0 &&
                                rect.left >= 0 &&
                                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                            );
                        """, cell)
                        
                        if is_visible:
                            cell_position = cell.location['y']
                            if cell_position not in processed_positions:
                                visible_cells.append(cell)
                                processed_positions.add(cell_position)
                    except:
                        continue
                
                if visible_cells:
                    print(f"Found {len(visible_cells)} new visible followers at position {current_position}")
                    max_count = max(max_count, current_count)
                    no_new_count = 0
                    
                    # Process visible cells
                    for cell in visible_cells:
                        try:
                            # Get display name and username
                            display_name_element = cell.find_element(
                                By.CSS_SELECTOR,
                                'div[dir="ltr"] span.css-1jxf684 span.css-1jxf684'
                            )
                            display_name = display_name_element.text.strip()
                            
                            username_element = cell.find_element(
                                By.CSS_SELECTOR,
                                'div[dir="ltr"][class*="r-1wvb978"] span.css-1jxf684'
                            )
                            username = username_element.text.strip()
                            
                            if username and display_name:
                                if not username.startswith('@'):
                                    username = f"@{username}"
                                follower_info = f"{display_name} ({username})"
                                
                                if follower_info not in all_followers:
                                    print(f"[NEW] Found follower: {follower_info}")
                                    all_followers.add(follower_info)
                                    current_batch.add(follower_info)
                                    
                                    # Save batch if it reaches the size limit
                                    if len(current_batch) >= batch_size:
                                        self.save_progress(current_batch)
                                        current_batch = set()
                                        batch_num += 1
                                else:
                                    print(f"[DUPLICATE] Found follower: {follower_info}")
                        except Exception as e:
                            print(f"Error processing follower: {str(e)}")
                            continue
                else:
                    no_new_count += 1
                    if no_new_count >= MAX_NO_NEW:
                        print(f"No new followers found after {MAX_NO_NEW} attempts")
                        break
                
                # Scroll down by step
                new_position = min(current_position + scroll_step, last_height)
                self.driver.execute_script(f"window.scrollTo(0, {new_position});")
                time.sleep(scroll_pause_time)
                
                # Check if we've reached the bottom
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height and new_position >= last_height:
                    break
                
                last_height = new_height
                
            except Exception as e:
                print(f"Error during scrolling: {str(e)}")
                # Scroll back a bit and retry
                current_position = self.driver.execute_script("return window.pageYOffset")
                self.driver.execute_script(f"window.scrollTo(0, {current_position - 200});")
                time.sleep(2)
                continue
        
        # Save any remaining followers in the last batch
        if current_batch:
            print(f"Saving final batch of {len(current_batch)} followers...")
            self.save_progress(current_batch)
        
        print(f"Finished scrolling, found total of {len(all_followers)} unique followers")
        return len(all_followers)
    
    def scan_followers(self, previous_followers: set) -> set:
        """Scan for new followers"""
        all_followers = set()
        batch_num = 1
        current_batch = set()
        batch_size = 100
        
        # Navigate to followers page
        followers_url = f'https://x.com/{self.target_username}/followers'
        print(f"Navigating to followers page: {followers_url}")
        self.driver.get(followers_url)
        time.sleep(5)
        
        # Verify we're on the followers page
        if 'followers' not in self.driver.current_url.lower():
            self.driver.get(followers_url)
            time.sleep(5)
        
        # Wait for followers section to load
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]')))
        time.sleep(2)
        
        # Initial scroll to load all followers
        print("Loading all followers...")
        total_followers = self.scroll_to_bottom()  # This method now returns the number of unique followers found
        
        # Since scroll_to_bottom now processes and saves followers as it finds them,
        # we don't need to process them again here
        
        print(f"\nFinished scanning, found {total_followers} followers")
        
        return self.load_previous_results()  # Return all followers including newly found ones
    
    def run(self):
        """Main loop to continuously track followers"""
        try:
            while True:
                print("\n=== Starting new scan ===")
                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                try:
                    # Check login status
                    self.check_login()
                    
                    # Load previous results from database
                    previous_followers = self.load_previous_results()
                    print(f"Loaded {len(previous_followers)} followers from database")
                    
                    # Scan for new followers
                    all_followers = self.scan_followers(previous_followers)
                    
                    # Mark unfollowers in database
                    self.db.mark_unfollowers(self.target_username, all_followers)
                    
                    # Get recent scan history
                    scan_history = self.db.get_scan_history(self.target_username, 5)
                    
                    # Print results
                    print(f"\nTotal followers found: {len(all_followers)}")
                    print("\nFollowers list:")
                    for follower in sorted(all_followers):
                        print(f"- {follower}")
                        
                    print("\nRecent scan history:")
                    for scan in scan_history:
                        print(f"- {scan['timestamp']}: {scan['total_followers']} total, {scan['new_followers']} new")
                    
                    # Wait before next scan
                    wait_seconds = self.scan_interval * 60
                    print(f"\nWaiting {self.scan_interval} minutes before next scan...")
                    time.sleep(wait_seconds)
                    
                except Exception as e:
                    print(f"Error during scan: {str(e)}")
                    print(f"Will retry in {self.scan_interval} minutes...")
                    time.sleep(self.scan_interval * 60)
                    continue
                
        except KeyboardInterrupt:
            print("\nTracker stopped by user")
        finally:
            if self.driver:
                self.driver.quit()
            if self.db:
                self.db.close() 