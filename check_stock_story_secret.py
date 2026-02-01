import modal
import os

app = modal.App("check-stock-story")
image = modal.Image.debian_slim(python_version="3.11")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
)
def check_env():
    """Check what environment variables are in Stock_Story secret."""
    keys_to_check = [
        'XAI_API_KEY',
        'DEEPSEEK_API_KEY',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'POLYGON_API_KEY'
    ]

    print("=" * 70)
    print("ENVIRONMENT VARIABLES IN Stock_Story SECRET")
    print("=" * 70)

    for key in keys_to_check:
        value = os.environ.get(key, '')
        if value:
            masked = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
            print(f"✓ {key}: {masked} (length: {len(value)})")
        else:
            print(f"✗ {key}: NOT SET")

    print("=" * 70)

    # Also check all environment variables to see what's actually there
    print("\nAll environment variables (filtered):")
    for key in sorted(os.environ.keys()):
        if any(x in key.upper() for x in ['API', 'KEY', 'TOKEN', 'CHAT', 'TELEGRAM', 'POLYGON', 'XAI', 'DEEPSEEK']):
            value = os.environ[key]
            if len(value) > 8:
                masked = value[:4] + '...' + value[-4:]
            else:
                masked = '***'
            print(f"  {key}: {masked}")

    return "Check complete"

@app.local_entrypoint()
def main():
    check_env.remote()
