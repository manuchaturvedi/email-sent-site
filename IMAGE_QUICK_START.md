# 🎨 Quick Image Setup

## What Images to Add

Place these files in: `sendmail/static/images/`

### Required Images:
1. **logo.png** (200x50px) - Your brand logo
2. **hero-bg.jpg** (1920x600px) - Hero section background

### Optional Feature Images:
3. **profile-icon.jpg** (400x400px) - Profile setup card
4. **automation-icon.jpg** (400x400px) - Automation card
5. **jobs-icon.jpg** (400x400px) - Browse jobs card
6. **email-icon.jpg** (400x400px) - Email history card

## Quick Steps

1. Download free images from:
   - https://unsplash.com
   - https://pexels.com
   - https://pixabay.com

2. Rename and save them to: `sendmail/static/images/`

3. Restart your Flask app or Docker container

4. Visit your site - images appear automatically!

## Already Included

✅ **logo.svg** - A default SVG logo is already created as fallback
✅ **IMAGE_GUIDE.html** - Open this file in your browser for detailed instructions
✅ **Templates configured** - No code changes needed!

## Free Logo Makers

Don't have a logo? Create one free:
- Canva: https://canva.com/create/logos/
- LogoMakr: https://logomakr.com
- Hatchful: https://hatchful.shopify.com

## Deploy to Production

```bash
git add sendmail/static/images/
git commit -m "Add custom images and logo"
git push origin cloud-deployment
```

---

**Need help?** Open `IMAGE_GUIDE.html` in your browser for the complete guide!
