# Cashfree Payment Gateway Setup Guide

## Step 1: Create Cashfree Account
1. Go to https://www.cashfree.com/
2. Click "Sign Up" → Create merchant account
3. Complete KYC verification (Pan Card, Bank Account)
4. Wait for approval (Usually 24-48 hours)

## Step 2: Get API Credentials
1. Login to Cashfree Dashboard
2. Go to "Developers" → "API Keys"
3. You'll see:
   - **Test App ID** (for testing)
   - **Test Secret Key** (for testing)
   - **Production App ID** (after going live)
   - **Production Secret Key** (after going live)

## Step 3: Set Environment Variables

### For Local Docker Testing:
```bash
docker run -d --name justmailit-app \
  -p 5000:5000 \
  -e CASHFREE_APP_ID="your_test_app_id_here" \
  -e CASHFREE_SECRET_KEY="your_test_secret_key_here" \
  -e CASHFREE_ENV="TEST" \
  email-automation-test:sendmail
```

### For Render Production:
1. Go to Render Dashboard → Your Web Service
2. Click "Environment"
3. Add these variables:
   ```
   CASHFREE_APP_ID=your_production_app_id
   CASHFREE_SECRET_KEY=your_production_secret_key
   CASHFREE_ENV=PROD
   ```

## Step 4: Configure Webhook URL
1. Go to Cashfree Dashboard → "Developers" → "Webhooks"
2. Add Webhook URL: `https://your-domain.com/payment/webhook`
3. Select events: "Payment Success", "Payment Failed"
4. Save webhook

## Step 5: Test Payment Flow

### Test Mode (Sandbox):
1. Use test app ID and secret key
2. Test with Cashfree test cards:
   - Card: 4111 1111 1111 1111
   - CVV: 123
   - Expiry: Any future date
   - OTP: 123456

3. Test UPI: Use test UPI ID `success@upi`

### Verification:
1. Make a test payment
2. Check webhook receives notification
3. Verify subscription activates in Firestore
4. Check user gets Pro plan features

## Step 6: Go Live

1. Complete Cashfree KYC verification
2. Submit for production approval
3. Get production API keys
4. Update environment variables to PROD
5. Change Cashfree SDK mode from "sandbox" to "production" in pricing.html

## Pricing
- **UPI/NetBanking**: 2% + GST
- **Credit/Debit Cards**: 2% + GST
- **Wallets**: 2% + GST

For ₹19 plan:
- Transaction fee: ₹0.38 + GST (≈₹0.45 total)
- You receive: ₹18.55

## Important Notes

1. **Webhook Security**: Add signature verification in production
2. **Return URL**: Must be HTTPS in production
3. **Testing**: Always test in sandbox first
4. **Support**: Cashfree support - support@cashfree.com

## Current Setup Status

✅ Code integrated
✅ Dockerfile ready  
✅ Webhook handler added
✅ Automatic subscription activation
⏳ Pending: Get Cashfree credentials
⏳ Pending: Add environment variables

## Next Steps

1. Register at cashfree.com
2. Get test API keys
3. Run: `docker build -t email-automation-test:sendmail -f Dockerfile.render .`
4. Run with credentials (see Step 3)
5. Test payment at http://localhost:5000/pricing
6. Verify webhook at http://localhost:5000/payment/webhook

## Troubleshooting

**Payment not working?**
- Check API keys are correct
- Verify CASHFREE_ENV matches your keys (TEST/PROD)
- Check webhook URL is accessible
- Look at docker logs for errors

**Subscription not activating?**
- Check Firestore permissions
- Verify webhook received (check logs)
- Ensure order_id matches in database

Need help? Check Cashfree docs: https://docs.cashfree.com/
