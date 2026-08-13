#!/usr/bin/env python3
"""Test SMTP configuration and send a test email."""

import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_smtp_config():
    """Validate SMTP configuration and attempt to send a test email."""
    
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port_str = os.getenv("SMTP_PORT", "587").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from = os.getenv("SMTP_FROM_EMAIL", "").strip()
    
    print("=" * 60)
    print("SMTP Configuration Test")
    print("=" * 60)
    
    # Check for required fields
    errors = []
    
    if not smtp_host:
        errors.append("❌ SMTP_HOST is empty or not set")
    else:
        print(f"✓ SMTP_HOST: {smtp_host}")
    
    if not smtp_user:
        errors.append("❌ SMTP_USER is empty or not set")
    else:
        print(f"✓ SMTP_USER: {smtp_user}")
    
    if not smtp_password:
        errors.append("❌ SMTP_PASSWORD is empty or not set")
    else:
        print(f"✓ SMTP_PASSWORD: [set - {len(smtp_password)} chars]")
    
    if not smtp_from:
        errors.append("❌ SMTP_FROM_EMAIL is empty or not set")
    else:
        print(f"✓ SMTP_FROM_EMAIL: {smtp_from}")
    
    try:
        smtp_port = int(smtp_port_str)
        print(f"✓ SMTP_PORT: {smtp_port}")
    except ValueError:
        errors.append(f"❌ SMTP_PORT must be a number, got: {smtp_port_str}")
        smtp_port = 587
    
    print()
    
    if errors:
        print("Configuration Issues:")
        for error in errors:
            print(f"  {error}")
        print()
        print("To fix:")
        print("  1. Edit .env file in project root")
        print("  2. Fill in your email credentials")
        print("  3. Save and restart app")
        return False
    
    # Test connection
    print("Testing SMTP connection...")
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            print("✓ Successfully connected to SMTP server")
            print("✓ Authentication successful")
            
            # Send test email
            print()
            print("Sending test email...")
            test_email = "test@example.com"
            message = EmailMessage()
            message["Subject"] = "LexAssist Email Test"
            message["From"] = smtp_from
            message["To"] = test_email
            message.set_content("This is a test email from LexAssist.")
            
            server.send_message(message)
            print(f"✓ Test email sent successfully to {test_email}")
            print()
            print("✅ Your email configuration is working!")
            return True
            
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your SMTP_USER and SMTP_PASSWORD")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {e}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print()
        print("Common issues:")
        print("  - Wrong SMTP_HOST or SMTP_PORT")
        print("  - Firewall blocking SMTP connection")
        print("  - Credentials are incorrect")
    
    return False


if __name__ == "__main__":
    success = test_smtp_config()
    exit(0 if success else 1)
