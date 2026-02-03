"""
Manually trigger the crisis monitor to test it works
"""
import modal

# Import from the scanner app
scanner_app = modal.App.lookup("stockstory-scanner")

@scanner_app.local_entrypoint()
def main():
    # Get the crisis monitor function
    x_intelligence_crisis_monitor = modal.Function.lookup("stockstory-scanner", "x_intelligence_crisis_monitor")

    print("🚨 Triggering X Intelligence Crisis Monitor...")
    result = x_intelligence_crisis_monitor.remote()
    print(f"\n✅ Result: {result}")
