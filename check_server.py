import sys
import urllib.request
import urllib.error
import json

def check(url: str, timeout: int = 3) -> int:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "health-check/1.0"}
        )

        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode("utf-8", errors="ignore")
            print("HTTP", r.status)
            try:
                print(json.dumps(json.loads(data), indent=2, ensure_ascii=False))
            except:
                print(data)
            return 0

    except Exception as e:
        print("FAIL :", repr(e))
        return 1

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/health"
    raise SystemExit(check(url))

if __name__ == "__main__":
    main()
