import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException
from database import DatabaseManager
from pathlib import Path

class TwitterFollowerTracker:
    def __init__(self, target_username: str, scan_interval: int = 60):
        self.target_username = target_username
        self.scan_interval = scan_interval
        self.should_exit = False
        self.driver = None
        self.db = DatabaseManager()
        
    def setup_driver(self):
        """Set up Chrome WebDriver with necessary options"""
        try:
            options = Options()
            
            # Use Chrome profile directory
            profile_dir = Path("data/chrome_profiles")
            if not profile_dir.exists():
                profile_dir.mkdir(parents=True, exist_ok=True)
                
            # Profile settings
            options.add_argument(f'--user-data-dir={profile_dir.absolute()}')
            options.add_argument('--profile-directory=Default')
            
            # Mobile emulation settings
            mobile_emulation = {
                "deviceMetrics": {
                    "width": 360,
                    "height": 640,
                    "pixelRatio": 3.0
                },
                "userAgent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
            }
            options.add_experimental_option("mobileEmulation", mobile_emulation)
            
            # Other necessary options
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-first-run')
            options.add_argument('--no-service-autorun')
            options.add_argument('--password-store=basic')
            
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                    
            self.driver = webdriver.Chrome(options=options)
            
            # Additional settings to avoid detection
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Started Chrome in mobile mode with saved profile")
            return True
            
        except Exception as e:
            print(f"Error setting up WebDriver: {str(e)}")
            return False
            
    def check_login(self):
        """Check if user is logged in"""
        try:
            current_url = self.driver.current_url
            
            # Check if we're on a logout URL
            if "logout=" in current_url:
                print("[INFO] Detected logout URL, attempting to re-login...")
                self.driver.get("https://x.com/home")
                time.sleep(2)
            
            # Try to find login button
            login_button = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="loginButton"]')
            if login_button:
                print("[WARNING] Not logged in. Please log in manually...")
                # Wait for manual login
                while True:
                    time.sleep(5)
                    if not self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="loginButton"]'):
                        print("[INFO] Successfully logged in!")
                        return True
                    
                    # Check if we're still on a logout URL
                    current_url = self.driver.current_url
                    if "logout=" in current_url:
                        print("[INFO] Still on logout URL, redirecting to home...")
                        self.driver.get("https://x.com/home")
                        time.sleep(2)
                        
            return True
            
        except Exception as e:
            print(f"[ERROR] Error checking login status: {str(e)}")
            return False
        
    def scroll_to_bottom(self):
        """Scroll to bottom of page and wait for content to load"""
        print("Starting to scroll and load followers...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        processed_positions = set()  # Track processed positions
        max_count = 0
        no_new_count = 0
        consecutive_existing = 0  # Count consecutive existing followers
        MAX_NO_NEW = 5
        MAX_CONSECUTIVE_EXISTING = 10  # Stop after finding 10 consecutive existing followers
        scroll_pause_time = 2
        scroll_step = 300
        
        # Initialize batch variables
        current_batch = []
        batch_size = 100
        all_followers = []
        
        # Load existing followers from database for comparison
        existing_followers = {f['username'] for f in self.db.get_all_followers(self.target_username)}
        print(f"Loaded {len(existing_followers)} existing followers from database")
        
        while True:
            if self.should_exit:
                break
                
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
                    found_new_in_batch = False
                    
                    # Process visible cells
                    for cell in visible_cells:
                        try:
                            # Get display name and username using correct selectors
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
                                username = username.lstrip('@')
                                follower_info = {
                                    'display_name': display_name,
                                    'username': username
                                }
                                
                                if username not in existing_followers and follower_info not in all_followers:
                                    print(f"[NEW] Found follower: {display_name} (@{username})")
                                    all_followers.append(follower_info)
                                    current_batch.append(follower_info)
                                    consecutive_existing = 0  # Reset counter when finding new follower
                                    found_new_in_batch = True
                                    
                                    # Save batch if it reaches the size limit
                                    if len(current_batch) >= batch_size:
                                        batch_num = int(time.time())
                                        self.db.add_followers(self.target_username, current_batch, batch_num)
                                        print(f"Saved batch of {len(current_batch)} followers")
                                        current_batch = []
                                else:
                                    print(f"[EXISTING] Found follower: {display_name} (@{username})")
                                    consecutive_existing += 1
                                    
                                    if consecutive_existing >= MAX_CONSECUTIVE_EXISTING:
                                        print(f"\nFound {MAX_CONSECUTIVE_EXISTING} consecutive existing followers")
                                        print("Assuming we've reached previously scanned followers, stopping scan...")
                                        break
                                        
                        except Exception as e:
                            print(f"Error processing follower: {str(e)}")
                            continue
                            
                    if consecutive_existing >= MAX_CONSECUTIVE_EXISTING:
                        break
                        
                    if not found_new_in_batch:
                        no_new_count += 1
                        if no_new_count >= MAX_NO_NEW:
                            print(f"No new followers found after {MAX_NO_NEW} attempts")
                            break
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
            batch_num = int(time.time())
            self.db.add_followers(self.target_username, current_batch, batch_num)
        
        total_followers = len(all_followers)
        print(f"Finished scrolling, found total of {total_followers} unique followers")
        return total_followers
        
    def process_followers(self):
        """Process visible follower cells and save to database"""
        try:
            cells = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="cellInnerDiv"]')
            total_processed = 0
            batch_followers = []
            
            for cell in cells:
                if self.should_exit:
                    break
                    
                try:
                    # Get display name and username from mobile layout
                    name_element = cell.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] > div:first-child > div:first-child > span')
                    username_element = cell.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] > div:last-child > span')
                    
                    display_name = name_element.text.strip()
                    username = username_element.text.strip()
                    if username.startswith('@'):
                        username = username[1:]
                        
                    # Skip if already processed
                    if not display_name or not username:
                        continue
                        
                    # Add to batch
                    batch_followers.append({
                        'display_name': display_name,
                        'username': username
                    })
                    total_processed += 1
                    print(f"Found follower: {display_name} (@{username})")
                    
                except StaleElementReferenceException:
                    print("Stale element, skipping...")
                    continue
                except Exception as e:
                    print(f"Error processing follower: {str(e)}")
                    continue
                    
            # Save batch to database
            if batch_followers:
                batch_num = int(time.time())
                new_followers = self.db.add_followers(
                    target_username=self.target_username,
                    followers=batch_followers,
                    batch_num=batch_num
                )
                print(f"\nSaved {new_followers} new followers to database")
                
            return total_processed
            
        except Exception as e:
            print(f"Error processing followers: {str(e)}")
            return 0
            
    def scan_followers(self):
        """Scan followers page and process new followers"""
        try:
            # Navigate to followers page
            followers_url = f"https://x.com/{self.target_username}/followers"
            self.driver.get(followers_url)
            time.sleep(2)
            
            # Check if we got redirected to a logout URL
            current_url = self.driver.current_url
            if "logout=" in current_url:
                print("[INFO] Redirected to logout URL, attempting to re-login...")
                if not self.check_login():
                    print("[ERROR] Failed to re-login")
                    return
                # Try navigating to followers page again
                self.driver.get(followers_url)
                time.sleep(2)
                
            # Wait for followers to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="cellInnerDiv"]'))
                )
            except TimeoutException:
                print("Timeout waiting for followers to load")
                return
                
            # Load and process followers while scrolling
            total_followers = self.scroll_to_bottom()
            if total_followers == 0:
                print("No followers found")
                return
                
            print(f"\nSuccessfully processed {total_followers} followers")
            
        except Exception as e:
            print(f"[ERROR] Error during follower scan: {str(e)}")
            if "logout=" in self.driver.current_url:
                print("[INFO] Exception occurred on logout URL, will retry after re-login")
                if self.check_login():
                    print("[INFO] Successfully re-logged in, retrying scan...")
                    return self.scan_followers()
            raise
        
    def stop(self):
        """Stop the tracker"""
        print("Stopping Twitter Follower Tracker...")
        self.should_exit = True
        if self.driver:
            self.driver.quit()
            
    def run(self):
        """Run the follower tracker"""
        print(f"Starting Twitter Follower Tracker for @{self.target_username}")
        
        if not self.setup_driver():
            print("Failed to set up WebDriver")
            return
            
        if not self.check_login():
            self.stop()
            return
            
        # Load previous results
        previous_followers = self.db.get_all_followers(self.target_username)
        if previous_followers:
            print(f"Loaded {len(previous_followers)} followers from previous runs")
            
        while not self.should_exit:
            try:
                print(f"\nStarting new scan at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                self.scan_followers()
                
                if self.should_exit:
                    break
                    
                print(f"Waiting {self.scan_interval} seconds before next scan...")
                time.sleep(self.scan_interval)
                
            except KeyboardInterrupt:
                print("\nReceived keyboard interrupt")
                break
            except Exception as e:
                print(f"Error in main loop: {str(e)}")
                if not self.setup_driver():
                    print("Failed to recover WebDriver")
                    break
                if not self.check_login():
                    break
                    
        self.stop() 