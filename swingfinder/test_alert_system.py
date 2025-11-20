"""
Test Alert System Locally
Run this to verify your alert system works before deploying to GitHub Actions
"""

import os
from dotenv import load_dotenv
from check_alerts import get_current_price, check_price_alert, send_email_alert, format_alert_html

# Load environment variables
load_dotenv()

def test_price_fetch():
    """Test fetching current price from Tiingo."""
    print("\n" + "="*60)
    print("TEST 1: Fetching Current Price")
    print("="*60)
    
    ticker = "AAPL"
    print(f"Fetching current price for {ticker}...")
    
    price = get_current_price(ticker)
    
    if price:
        print(f"✅ SUCCESS! Current price: ${price:.2f}")
        return True
    else:
        print(f"❌ FAILED! Could not fetch price")
        return False


def test_alert_logic():
    """Test alert checking logic."""
    print("\n" + "="*60)
    print("TEST 2: Alert Logic")
    print("="*60)
    
    # Test alert
    alert = {
        "type": "price",
        "ticker": "AAPL",
        "condition": "above",
        "target_price": 100.00
    }
    
    current_price = 150.00
    
    print(f"Alert: {alert['ticker']} price {alert['condition']} ${alert['target_price']:.2f}")
    print(f"Current price: ${current_price:.2f}")
    
    triggered = check_price_alert("AAPL", current_price, alert)
    
    if triggered:
        print(f"✅ SUCCESS! Alert logic working (should trigger)")
        return True
    else:
        print(f"❌ FAILED! Alert should have triggered")
        return False


def test_email():
    """Test sending email alert."""
    print("\n" + "="*60)
    print("TEST 3: Email Notification")
    print("="*60)
    
    email = os.getenv("ALERT_EMAIL")
    
    if not email:
        print("⚠️ SKIPPED - No ALERT_EMAIL configured in .env")
        return None
    
    print(f"Sending test email to {email}...")
    
    alert = {
        "type": "price",
        "ticker": "AAPL",
        "condition": "above",
        "target_price": 100.00
    }
    
    subject = "🧪 SwingFinder Alert System Test"
    body = "This is a test email from your SwingFinder alert system.\n\nIf you received this, email alerts are working correctly!"
    html = format_alert_html(alert, "AAPL", 150.00)
    
    success = send_email_alert(email, subject, body, html)
    
    if success:
        print(f"✅ SUCCESS! Email sent to {email}")
        print(f"📧 Check your inbox!")
        return True
    else:
        print(f"❌ FAILED! Could not send email")
        print(f"💡 Make sure ALERT_EMAIL and ALERT_EMAIL_PASSWORD are set in .env")
        return False


def main():
    """Run all tests."""
    print("\n" + "🧪 SWINGFINDER ALERT SYSTEM TEST")
    print("="*60)
    
    results = []
    
    # Test 1: Price fetching
    results.append(("Price Fetch", test_price_fetch()))
    
    # Test 2: Alert logic
    results.append(("Alert Logic", test_alert_logic()))
    
    # Test 3: Email
    email_result = test_email()
    if email_result is not None:
        results.append(("Email", email_result))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your alert system is ready!")
        print("\n📋 Next steps:")
        print("1. Add GitHub secrets (see ALERTS_SETUP.md)")
        print("2. Push code to GitHub")
        print("3. Enable GitHub Actions")
        print("4. Create alerts in the app")
    else:
        print("\n⚠️ Some tests failed. Check your configuration:")
        print("1. Make sure TIINGO_API_KEY is set in .env")
        print("2. Make sure ALERT_EMAIL and ALERT_EMAIL_PASSWORD are set in .env")
        print("3. Use Gmail App Password, not regular password")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()

