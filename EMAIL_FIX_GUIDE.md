# 🚀 Email Setup - Get OTP Working in 2 Minutes

## Problem
You're seeing "Email could not be sent. Use the verification code below:" message during signup.

## Solution - Use Mailtrap (Recommended - Free & Instant)

### Step 1: Create Mailtrap Account (Free)
- Visit: https://mailtrap.io
- Click "Sign up" (takes 1 minute)
- Verify your email
- You'll see your inbox automatically created

### Step 2: Copy Your SMTP Credentials
1. In Mailtrap, go to **"Integrations"** tab
2. Select **"SMTP"** from the dropdown
3. You'll see your credentials:
   - Hostname: `live.smtp.mailtrap.io`
   - Port: `587`
   - Username: (copy this)
   - Password: (copy this)

### Step 3: Update `.env` File
Edit `.env` in your project and replace:
```
SMTP_USER = "paste-mailtrap-username-here"
SMTP_PASSWORD = "paste-mailtrap-password-here"
```

### Step 4: Test Your Setup
Run this command to verify:
```bash
python test_email_config.py
```

You should see:
```
✅ Your email configuration is working!
```

### Step 5: Restart Your App
1. Stop the app (Ctrl+C)
2. Run: `streamlit run app.py`
3. Try signing up again
4. Check Mailtrap inbox to see test emails

---

## Alternative - Use Your Own Gmail

If you prefer using Gmail:

1. Go to: https://myaccount.google.com/security
2. Turn on **"2-Step Verification"**
3. Go to: https://myaccount.google.com/apppasswords
4. Select "Mail" → "Windows Computer"
5. Copy the 16-character password
6. Update `.env`:
   ```
   SMTP_HOST = "smtp.gmail.com"
   SMTP_USER = "your-email@gmail.com"
   SMTP_PASSWORD = "paste-16-char-password"
   SMTP_FROM_EMAIL = "your-email@gmail.com"
   ```

---

## Troubleshooting

**Still not working?**
```bash
python test_email_config.py
```

This will tell you exactly what's wrong:
- ✓ Shows what's configured correctly
- ❌ Shows what needs to be fixed
- Helps diagnose connection issues

**Common Issues:**
- ❌ "your-gmail@gmail.com" - Still using placeholder
  - → Fill in actual Mailtrap username/password
- ❌ "Authentication failed"
  - → Double-check username and password spelling
- ❌ "Connection Error"
  - → Mailtrap server might be down (rare), try Gmail instead

---

## How to Know It's Working

When emails work, you'll see:
- ✅ "Account created successfully!"
- ✅ "Check your email for a verification code."
- Email arrives in your inbox (Mailtrap or Gmail)

Instead of:
- ❌ "Email could not be sent. Use the verification code below:"
