import requests
import time
import sys
import uuid
import json
from typing import Optional, List, Tuple, Dict, Any

try:
    from colorama import Fore, Style, init
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich import box
except ImportError as e:
    print(f"❌ Missing required library: {e}")
    print("📦 Install with: pip install requests colorama rich")
    sys.exit(1)

init(autoreset=True)
console = Console()

DEVICE_ID = str(uuid.uuid4())
ANDROID_ID = "android-" + str(uuid.uuid4())[:16]
USER_AGENT = "Instagram 123.0.0.21.114 Android (30/11; 420dpi; 1080x1920; OnePlus; Nord; OnePlus7T; qcom; en_US)"
APP_ID = "936619743392459"

class InstagramUnfollow:
    
    def __init__(self, sessionid: str, csrf_token: str = "missing"):
        self.sessionid = sessionid
        self.csrf_token = csrf_token
        self.session = requests.Session()
        self.session.headers.update(self._build_headers())
        self.rate_limit_delay = 2
        
    def _build_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "x-ig-app-id": APP_ID,
            "x-ig-device-id": DEVICE_ID,
            "x-ig-android-id": ANDROID_ID,
            "x-ig-connection-type": "WIFI",
            "x-ig-capabilities": "3brTvw==",
            "x-ig-app-locale": "en_US",
            "x-ig-bandwidth-speed-kbps": "10000.000",
            "x-csrftoken": self.csrf_token,
            "cookie": f"sessionid={self.sessionid};"
        }
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 429:  
                    console.print(f"⏳ Rate limited, waiting {self.rate_limit_delay * 2}s...", style="yellow")
                    time.sleep(self.rate_limit_delay * 2)
                    self.rate_limit_delay = min(self.rate_limit_delay * 1.5, 10)
                    continue
                elif response.status_code in [200, 201]:
                    self.rate_limit_delay = max(self.rate_limit_delay * 0.9, 1)
                    return response
                elif response.status_code == 403:
                    console.print("🔒 Access forbidden - session may be expired", style="red")
                    return None
                elif response.status_code == 404:
                    console.print("❌ Resource not found", style="red")
                    return None
                else:
                    console.print(f"⚠️ Unexpected status code: {response.status_code}", style="yellow")
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(2 ** attempt)
                    
            except requests.exceptions.ConnectionError:
                console.print(f"🌐 Connection error (attempt {attempt + 1}/{max_retries})", style="red")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)
            except requests.exceptions.Timeout:
                console.print(f"⏰ Request timeout (attempt {attempt + 1}/{max_retries})", style="red")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)
            except Exception as e:
                console.print(f"❌ Request error: {str(e)}", style="red")
                return None
        
        return None
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        response = self._make_request("GET", url)
        
        if not response:
            return None
            
        try:
            data = response.json()["data"]["user"]
            return {
                "user_id": data["id"],
                "username": data["username"],
                "full_name": data.get("full_name", ""),
                "followers_count": data["edge_followed_by"]["count"],
                "following_count": data["edge_follow"]["count"],
                "posts_count": data["edge_owner_to_timeline_media"]["count"],
                "is_private": data.get("is_private", False),
                "is_verified": data.get("is_verified", False)
            }
        except (KeyError, TypeError) as e:
            console.print(f"❌ Error parsing user info: {str(e)}", style="red")
            return None
    
    def fetch_followings(self, user_id: str, limit: int) -> List[Tuple[str, str]]:
        users = []
        max_id = ""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Fetching followings...", total=limit)
            
            while len(users) < limit:
                url = f"https://i.instagram.com/api/v1/friendships/{user_id}/following/?count=50&max_id={max_id}"
                response = self._make_request("GET", url)
                
                if not response:
                    break
                
                try:
                    data = response.json()
                    for user in data.get("users", []):
                        users.append((user["pk"], user["username"]))
                        progress.update(task, advance=1)
                        if len(users) >= limit:
                            break
                    
                    max_id = data.get("next_max_id", "")
                    if not max_id:
                        break
                        
                except (KeyError, TypeError):
                    break
                
                time.sleep(self.rate_limit_delay)
            
            progress.update(task, completed=len(users))
        
        return users[:limit]
    
    def unfollow_users(self, users: List[Tuple[str, str]]) -> Dict[str, int]:

        results = {"success": 0, "failed": 0}
        
        max_per_hour = 100
        if len(users) > max_per_hour:
            console.print(f"[yellow]⚠️ Note: Instagram allows maximum 100 unfollows per hour[/yellow]")
            console.print(f"[yellow]Limiting to {max_per_hour} users for safety[/yellow]")
            users = users[:max_per_hour]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Unfollowing users...", total=len(users))
            
            for i, (user_id, username) in enumerate(users, 1):
                url = f"https://i.instagram.com/api/v1/friendships/destroy/{user_id}/"
                response = self._make_request("POST", url)
                
                if response and response.status_code == 200:
                    console.print(f"✅ Unfollowed [bold green]{username}[/bold green] ({i}/{len(users)})")
                    results["success"] += 1
                else:
                    console.print(f"❌ Failed to unfollow [bold red]{username}[/bold red]")
                    results["failed"] += 1
                
                progress.update(task, advance=1)
                time.sleep(self.rate_limit_delay)
        
        return results

def show_banner():
    console.print(Panel.fit(
        "[bold cyan]Instagram Unfollow Tool[/bold cyan]\n"
        "[dim]   [/dim]",
        box=box.ROUNDED,
        padding=(1, 2)
    ))

def main():
    show_banner()
    
    sessionid = Prompt.ask("Session ID enter karo", password=True)
    if not sessionid:
        console.print("❌ Session ID required hai", style="red")
        return
    
    api = InstagramUnfollow(sessionid)
    
    console.print("\n[bold yellow]Account Selection[/bold yellow]")
    username = Prompt.ask("Apna Instagram username enter karo (@ ke bina)")
    
    if not username:
        console.print("❌ Username required hai", style="red")
        return
    
    console.print(f"\n🔍 Getting info for {username}...")
    user_info = api.get_user_info(username)
    
    if not user_info:
        console.print(f"❌ User {username} ka info nahi mil saka", style="red")
        return
    
    console.print(f"✅ User found: {user_info['full_name']}")
    console.print(f"Following: {user_info['following_count']} accounts")
    
    max_unfollow = min(100, user_info['following_count']) 
    
    try:
        count = int(Prompt.ask(f"Kitne users ko unfollow karna hai? (max {max_unfollow})", default="10"))
        if count <= 0 or count > max_unfollow:
            console.print(f"❌ Valid number enter karo (1-{max_unfollow})", style="red")
            return
    except ValueError:
        console.print("❌ Valid number enter karo", style="red")
        return
    
    if not Confirm.ask(f"\n⚠️ Confirm: {count} users ko unfollow karna chahte ho?"):
        console.print("❌ Operation cancelled", style="yellow")
        return
    
    console.print(f"\n📥 Fetching {count} users from following list...")
    following_list = api.fetch_followings(user_info['user_id'], count)
    
    if not following_list:
        console.print("❌ Following list fetch nahi ho saki", style="red")
        return
    
    console.print(f"✅ Got {len(following_list)} users to unfollow")
    
    console.print(f"\n🚀 Starting unfollow process...")
    results = api.unfollow_users(following_list)
    
    console.print(f"\n[bold green]✅ Process Complete![/bold green]")
    console.print(f"Successfully unfollowed: [bold green]{results['success']}[/bold green]")
    console.print(f"Failed: [bold red]{results['failed']}[/bold red]")
    
    if results['success'] > 0:
        console.print(f"\n[dim]Note: Instagram me changes dikhne me thoda time lag sakta hai[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n❌ Process cancelled by user", style="yellow")
    except Exception as e:
        console.print(f"\n❌ Error: {str(e)}", style="red")
