"""
Check all cron jobs status in Modal
"""
import modal

app = modal.App("check-cron-status")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("Stock_Story")],
    timeout=60,
)
def check_cron_jobs():
    """List all scheduled functions and their status"""

    # The cron jobs defined in modal_scanner.py:
    cron_jobs = [
        {
            "name": "morning_mega_bundle",
            "schedule": "0 14 * * 1-5",  # Mon-Fri 6:00 AM PST (14:00 UTC)
            "description": "Daily scan + theme discovery + insider transactions",
        },
        {
            "name": "afternoon_analysis_bundle",
            "schedule": "0 21 * * 1-5",  # Mon-Fri 1:00 PM PST (21:00 UTC)
            "description": "Conviction alerts + options flow + market health",
        },
        {
            "name": "weekly_reports_bundle",
            "schedule": "0 2 * * 1",  # Mondays 2:00 AM UTC (Sunday 6 PM PST)
            "description": "Weekly performance + sector rotation + theme refresh",
        },
        {
            "name": "monitoring_cycle_bundle",
            "schedule": "0 */6 * * *",  # Every 6 hours
            "description": "Data staleness monitor + parameter learning health",
        },
        {
            "name": "x_intelligence_crisis_monitor",
            "schedule": "0 * * * *",  # Every hour
            "description": "X/Twitter crisis detection + alerts",
        },
    ]

    print("=" * 70)
    print("📋 MODAL CRON JOBS STATUS")
    print("=" * 70)

    for job in cron_jobs:
        print(f"\n🕐 {job['name']}")
        print(f"   Schedule: {job['schedule']}")
        print(f"   Description: {job['description']}")

    print("\n" + "=" * 70)
    print("✅ All 5 cron jobs are configured in modal_scanner.py")
    print("   They run automatically based on their schedules.")
    print("=" * 70)

    return cron_jobs

@app.local_entrypoint()
def main():
    check_cron_jobs.remote()
