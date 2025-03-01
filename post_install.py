import subprocess

def post_install():
    print("🔹 Installing Playwright Chromium browser...")
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print(f"⚠️ Warning: Failed to install Playwright browser: {e}")

if __name__ == "__main__":
    post_install()