# Email Configuration Setup Guide

## Quick Fix - Use Mailtrap (Free, No Personal Email Required)

### Step 1: Create Mailtrap Account
1. Go to https://mailtrap.io (sign up free)
2. Create a new project/inbox
3. Select "Integrations" → "SMTP"

### Step 2: Create `.env` File
Create a new file called `.env` in your project root folder with this content:

```
SMTP_HOST=live.smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=your-mailtrap-username
SMTP_PASSWORD=your-mailtrap-password
SMTP_FROM_EMAIL=your-email@example.com
```

Replace:
- `your-mailtrap-username` - from Mailtrap SMTP credentials
- `your-mailtrap-password` - from Mailtrap SMTP credentials

### Step 3: Restart Application
1. Stop your Streamlit app (Ctrl+C)
2. Run it again with `streamlit run app.py`

### Testing
- Sign up with any email
- You'll see the verification code in the UI
- Check Mailtrap inbox to see if email was sent
- Use code to verify your account

---

## Alternative - Use Gmail

### Step 1: Enable Gmail App Password
1. Go to https://myaccount.google.com/security
2. Turn ON "2-Step Verification"
3. Go to https://myaccount.google.com/apppasswords
4. Select "Mail" and "Windows Computer"
5. Copy the 16-character password shown

### Step 2: Create `.env` File
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
SMTP_FROM_EMAIL=your-email@gmail.com
```

Replace `your-email@gmail.com` and the 16-char password.

### Step 3: Restart Application

---

## Troubleshooting

**Still seeing error message?**
- Check `.env` file is in the same folder as `app.py`
- Verify no typos in credentials
- Check terminal for detailed error messages
- For Mailtrap: Verify credentials from the SMTP settings

**Need help?**
- Check the console output for error details
- Verify all env variables are set correctly
- Try Mailtrap first (easiest to debug)
