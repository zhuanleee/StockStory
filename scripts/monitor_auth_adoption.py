#!/usr/bin/env python3
"""
API Authentication Adoption Monitor

Tracks adoption of API authentication during grace period and after enforcement.

Usage:
    python scripts/monitor_auth_adoption.py

Reports:
- Requests with API keys vs without
- Unique users authenticated
- Error rates (401 Unauthorized)
- Adoption percentage
- Projected enforcement impact
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List
import time

# Configuration
API_BASE = "https://your-api-url.modal.run"
CHECK_INTERVAL = 300  # 5 minutes

def get_api_metrics() -> Dict:
    """Fetch current API metrics"""
    try:
        response = requests.get(f"{API_BASE}/admin/metrics")
        data = response.json()
        return data.get('metrics', {})
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return {}

def calculate_adoption_stats(metrics: Dict) -> Dict:
    """Calculate authentication adoption statistics"""
    total_requests = metrics.get('total_requests', 0)
    status_codes = metrics.get('status_codes', {})

    # Count authenticated vs unauthenticated
    # 401 errors = missing/invalid API key
    unauthorized_count = status_codes.get('401', 0)

    # Estimate authenticated requests
    # (total - 401 errors - other errors)
    authenticated_requests = total_requests - unauthorized_count

    # Calculate adoption rate
    adoption_rate = 0
    if total_requests > 0:
        adoption_rate = (authenticated_requests / total_requests) * 100

    return {
        'total_requests': total_requests,
        'authenticated_requests': authenticated_requests,
        'unauthorized_requests': unauthorized_count,
        'adoption_rate': round(adoption_rate, 2),
        'timestamp': datetime.now().isoformat()
    }

def analyze_error_trends(metrics: Dict) -> Dict:
    """Analyze error rate trends"""
    total_errors = metrics.get('total_errors', 0)
    total_requests = metrics.get('total_requests', 0)
    error_rate = metrics.get('error_rate', 0)

    status_codes = metrics.get('status_codes', {})

    # Break down errors
    auth_errors = status_codes.get('401', 0)  # Unauthorized
    rate_limit_errors = status_codes.get('429', 0)  # Rate limited
    server_errors = status_codes.get('500', 0)  # Server errors

    return {
        'total_errors': total_errors,
        'error_rate': error_rate,
        'auth_errors': auth_errors,
        'rate_limit_errors': rate_limit_errors,
        'server_errors': server_errors,
        'auth_error_percentage': round((auth_errors / max(total_requests, 1)) * 100, 2)
    }

def check_enforcement_readiness(adoption_rate: float, unauthorized_count: int) -> Dict:
    """Check if system is ready for enforcement"""
    is_ready = adoption_rate >= 80 and unauthorized_count < 100

    warnings = []
    if adoption_rate < 80:
        warnings.append(f"Adoption rate is {adoption_rate}%, target is 80%+")
    if unauthorized_count >= 100:
        warnings.append(f"{unauthorized_count} requests without keys in last period")

    return {
        'ready_for_enforcement': is_ready,
        'adoption_threshold_met': adoption_rate >= 80,
        'low_unauthenticated_requests': unauthorized_count < 100,
        'warnings': warnings,
        'recommendation': 'Proceed with enforcement' if is_ready else 'Extend grace period'
    }

def project_enforcement_impact(metrics: Dict, adoption_stats: Dict) -> Dict:
    """Project impact of enforcing API keys"""
    unauthorized_requests = adoption_stats['unauthorized_requests']
    total_requests = adoption_stats['total_requests']

    # Calculate projected rejection rate
    projected_rejections = unauthorized_requests
    projected_rejection_rate = 0
    if total_requests > 0:
        projected_rejection_rate = (projected_rejections / total_requests) * 100

    # Estimate affected users (rough estimate)
    # Assume each user makes ~100 requests/day
    estimated_affected_users = max(1, unauthorized_requests // 100)

    return {
        'projected_rejected_requests': projected_rejections,
        'projected_rejection_rate': round(projected_rejection_rate, 2),
        'estimated_affected_users': estimated_affected_users,
        'recommendation': 'Low impact' if projected_rejection_rate < 10 else 'High impact - extend grace period'
    }

def generate_report() -> str:
    """Generate comprehensive adoption report"""
    print("Fetching metrics...")
    metrics = get_api_metrics()

    if not metrics:
        return "❌ Unable to fetch metrics"

    print("Calculating statistics...")
    adoption = calculate_adoption_stats(metrics)
    errors = analyze_error_trends(metrics)
    readiness = check_enforcement_readiness(adoption['adoption_rate'], adoption['unauthorized_requests'])
    impact = project_enforcement_impact(metrics, adoption)

    # Build report
    report = f"""
╔══════════════════════════════════════════════════════════════════╗
║          API Authentication Adoption Report                      ║
║          Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                          ║
╚══════════════════════════════════════════════════════════════════╝

📊 ADOPTION STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Requests:        {adoption['total_requests']:,}
  Authenticated:         {adoption['authenticated_requests']:,}
  Unauthorized:          {adoption['unauthorized_requests']:,}

  📈 Adoption Rate:      {adoption['adoption_rate']}%
  {'✅ Target Met (80%+)' if adoption['adoption_rate'] >= 80 else '⚠️  Below Target (80%+)'}

🚨 ERROR ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Errors:          {errors['total_errors']:,}
  Error Rate:            {errors['error_rate']}%

  Auth Errors (401):     {errors['auth_errors']:,} ({errors['auth_error_percentage']}%)
  Rate Limit (429):      {errors['rate_limit_errors']:,}
  Server Errors (500):   {errors['server_errors']:,}

🎯 ENFORCEMENT READINESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Status: {'✅ READY' if readiness['ready_for_enforcement'] else '⚠️  NOT READY'}

  ✓ Adoption Threshold:  {'✅ Met' if readiness['adoption_threshold_met'] else '❌ Not Met'}
  ✓ Low Unauthenticated: {'✅ Met' if readiness['low_unauthenticated_requests'] else '❌ Not Met'}

  Recommendation: {readiness['recommendation']}
"""

    if readiness['warnings']:
        report += "\n  ⚠️  Warnings:\n"
        for warning in readiness['warnings']:
            report += f"     • {warning}\n"

    report += f"""
📉 PROJECTED ENFORCEMENT IMPACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Projected Rejections:  {impact['projected_rejected_requests']:,} requests
  Rejection Rate:        {impact['projected_rejection_rate']}%
  Estimated Users:       ~{impact['estimated_affected_users']} users affected

  Impact Assessment:     {impact['recommendation']}

💡 RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Conditional recommendations
    if readiness['ready_for_enforcement']:
        report += """
  ✅ System is ready for enforcement

  Next Steps:
  1. Send final reminder to users (24h notice)
  2. Set REQUIRE_API_KEYS=true
  3. Monitor error rates closely for 24h
  4. Be ready to extend grace period if needed
"""
    else:
        report += """
  ⚠️  Extend grace period recommended

  Next Steps:
  1. Send reminder email to all users
  2. Identify users without API keys
  3. Offer direct assistance
  4. Re-evaluate in 3-7 days
  5. Target: 80%+ adoption, <100 unauthorized requests
"""

    report += """
╔══════════════════════════════════════════════════════════════════╗
║  Monitoring Dashboard: /admin/dashboard                          ║
║  API Metrics: /admin/metrics                                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

    return report

def continuous_monitor(interval: int = 300):
    """Continuously monitor adoption (every 5 minutes)"""
    print("🔄 Starting continuous monitoring...")
    print(f"   Check interval: {interval} seconds ({interval//60} minutes)")
    print(f"   Press Ctrl+C to stop\n")

    try:
        while True:
            report = generate_report()
            print(report)
            print(f"\n⏰ Next check in {interval//60} minutes...\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped")

def main():
    """Main execution"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        continuous_monitor(CHECK_INTERVAL)
    else:
        # Single report
        report = generate_report()
        print(report)
        print("\n💡 Tip: Run with --continuous flag for ongoing monitoring")

if __name__ == '__main__':
    main()
