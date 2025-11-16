# Razorpay Payment Gateway Setup

## Overview
JustMailIt now uses Razorpay for processing Pro subscription payments. Razorpay charges 2% + GST per transaction.

## Current Configuration
Your application is configured with the following Razorpay credentials:

**Key ID:** `rzp_live_RgNB6M60lUvK2l`  
**Key Secret:** `i4GM8FcOw34g438OMecg2z78`

⚠️ **Note:** These are LIVE credentials. For testing, you should generate TEST credentials from your Razorpay dashboard.

## Features Implemented

### 1. Payment Order Creation
- Route: `/create_payment` (POST)
- Creates Razorpay order with amount, currency, and receipt
- Stores order details in Firestore `pending_payments` collection
- Returns order details for Razorpay Checkout

### 2. Razorpay Checkout Integration
- Integrated in `pricing.html`
- Opens Razorpay's hosted payment page
- Supports all payment methods (UPI, Cards, Netbanking, Wallets)
- Custom theme color: `#4f46e5` (Indigo)

### 3. Webhook Handler
- Route: `/payment/webhook` (POST)
- Automatically activates subscription when payment is captured
- Verifies webhook signature for security
- Updates Firestore with payment status

### 4. Payment Status Polling
- Frontend polls `/check_payment_status/<order_id>` every 2 seconds
- Automatically detects successful payment and redirects to dashboard
- Shows success message on completion

## Setup Steps

### 1. Access Razorpay Dashboard
Visit https://dashboard.razorpay.com/

### 2. Switch to Test Mode (Recommended for Development)
1. Click the mode toggle in top-left corner
2. Select "Test Mode"
3. Go to Settings → API Keys
4. Generate new test keys (format: `rzp_test_XXXXX`)

### 3. Configure Webhook
1. Go to Settings → Webhooks
2. Create new webhook with URL: `https://your-domain.com/payment/webhook`
3. Select event: `payment.captured`
4. Copy the Webhook Secret
5. Add to environment variables: `RAZORPAY_WEBHOOK_SECRET=your_webhook_secret`

### 4. Update Environment Variables

For **Test Mode** (Development):
```bash
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXXX
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

For **Live Mode** (Production):
```bash
RAZORPAY_KEY_ID=rzp_live_RgNB6M60lUvK2l
RAZORPAY_KEY_SECRET=i4GM8FcOw34g438OMecg2z78
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

### 5. Docker Environment
Add to `docker-compose.yml`:
```yaml
environment:
  - RAZORPAY_KEY_ID=rzp_live_RgNB6M60lUvK2l
  - RAZORPAY_KEY_SECRET=i4GM8FcOw34g438OMecg2z78
  - RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

Or pass at runtime:
```bash
docker run -p 5000:5000 \
  -e RAZORPAY_KEY_ID=rzp_live_RgNB6M60lUvK2l \
  -e RAZORPAY_KEY_SECRET=i4GM8FcOw34g438OMecg2z78 \
  -e RAZORPAY_WEBHOOK_SECRET=your_webhook_secret \
  justmailit-app
```

## Testing

### Test Mode Cards (Use in Test Mode only)
**Successful Payment:**
- Card: `4111 1111 1111 1111`
- CVV: Any 3 digits
- Expiry: Any future date
- OTP: 1234 (for 3D Secure)

**Failed Payment:**
- Card: `4000 0000 0000 0002`

### Test UPI
- UPI ID: `success@razorpay`
- Any other UPI ID will simulate payment

### Webhook Testing
Use Razorpay's webhook simulator in test mode:
1. Go to Settings → Webhooks
2. Click on your webhook
3. Click "Send Test Webhook"
4. Select `payment.captured` event

## Subscription Plans

### Free Plan
- 10 emails per day
- No payment required

### Pro Plan (₹19/month)
- Unlimited emails
- Payment via Razorpay
- Auto-renewal (requires recurring setup)

### Enterprise Plan
- Custom pricing
- Contact admin

## Transaction Flow

1. **User clicks "Choose Pro"**
2. **Payment modal opens** → Backend creates Razorpay order
3. **User completes payment** → Razorpay processes payment
4. **Webhook triggered** → `payment.captured` event sent to `/payment/webhook`
5. **Subscription activated** → User profile updated with Pro status
6. **Frontend detects** → Polling finds subscription active, shows success
7. **Auto-redirect** → User taken to dashboard after 2 seconds

## Security Features

### Webhook Signature Verification
Razorpay signs webhooks with HMAC SHA256. The webhook handler verifies this signature to prevent fraud:
```python
razorpay_client.utility.verify_webhook_signature(
    webhook_body,
    signature_header,
    webhook_secret
)
```

### Order Receipt Tracking
Each order has a unique receipt ID (`JMI_{timestamp}_{plan}`) for tracking and reconciliation.

### Firestore Security
- Pending payments stored temporarily
- Completed payments moved to user profile payment history
- Status tracked: `pending` → `completed`

## Pricing & Fees

**Razorpay Pricing:**
- 2% transaction fee
- + 18% GST on fee
- Effective rate: ~2.36% per transaction

**For ₹19 transaction:**
- Transaction fee: ₹0.38
- GST (18%): ₹0.07
- **Total cost: ₹0.45**
- **You receive: ₹18.55**

## Settlement

- **Test Mode:** No actual money movement
- **Live Mode:** 
  - T+2 settlement (2 business days)
  - Instant settlements available (additional fee)
  - Settlement bank account configured in dashboard

## Troubleshooting

### Payment not activating subscription
1. Check webhook is configured correctly
2. Verify webhook secret in environment variables
3. Check Firestore logs for webhook events
4. Test webhook manually from dashboard

### "Payment gateway not configured" error
- Ensure `razorpay` package is installed: `pip install razorpay==1.4.1`
- Check environment variables are set correctly
- Restart Flask application after setting variables

### Webhook signature verification fails
- Ensure webhook secret matches exactly
- Check webhook payload format
- Verify webhook URL is publicly accessible (not localhost)

### Testing on localhost
Razorpay webhooks require a public URL. For local testing:
1. Use ngrok: `ngrok http 5000`
2. Update webhook URL in dashboard to ngrok URL
3. Or use webhook simulator in test mode

## Support

**Razorpay Support:**
- Dashboard: https://dashboard.razorpay.com/
- Documentation: https://razorpay.com/docs/
- Support: https://razorpay.com/support/

**API Reference:**
- Orders API: https://razorpay.com/docs/api/orders/
- Payments API: https://razorpay.com/docs/api/payments/
- Webhooks: https://razorpay.com/docs/webhooks/

## Next Steps

1. **Switch to Test Mode** for development testing
2. **Configure webhook** with your domain
3. **Test payment flow** with test cards
4. **Verify webhook events** are being received
5. **Switch to Live Mode** when ready for production
6. **Monitor transactions** in Razorpay dashboard

---

✅ **Razorpay integration complete!**  
Your JustMailIt application is now ready to accept payments through Razorpay.
