"""
main.py — FastAPI application for cvvtony.pl HUSTLER PACK store.
Routes: Landing page, Stripe checkout, webhook, secure download, admin CMS.
"""

import os
import uuid
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any

import stripe
from dotenv import load_dotenv
from fastapi import (
    FastAPI, Request, Depends, HTTPException, Form,
    UploadFile, File, BackgroundTasks, Header
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database import get_db, init_db
from models import Product, Review, DownloadToken, Order, InstagramHighlight

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
load_dotenv()

STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")

stripe.api_key = STRIPE_SECRET_KEY

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="cvvtony.pl — HUSTLER PACK", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/images", StaticFiles(directory=str(BASE_DIR / "images")), name="images")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def check_admin(request: Request):
    """Verify admin session cookie."""
    if not request.session.get("admin_logged_in"):
        raise HTTPException(status_code=401, detail="Unauthorized")


def send_download_email(email: str, download_url: str):
    """Send the PDF download link via SMTP in a background task."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured. Would send to {email}: {download_url}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🔥 Twój HUSTLER PACK jest gotowy!"
    msg["From"] = SMTP_USER
    msg["To"] = email

    html_body = f"""\
    <html>
    <body style="margin:0;padding:0;background:#0a0a0a;font-family:'Segoe UI',Arial,sans-serif;">
      <div style="max-width:600px;margin:0 auto;padding:40px 20px;">
        <div style="text-align:center;margin-bottom:30px;">
          <h1 style="color:#ff00ff;font-size:28px;margin:0;letter-spacing:2px;">HUSTLER PACK</h1>
          <p style="color:#666;font-size:14px;margin-top:5px;">by CVV TONY</p>
        </div>
        <div style="background:#121212;border-radius:12px;padding:30px;border:1px solid #222;">
          <h2 style="color:#fff;font-size:22px;margin:0 0 15px;">Cześć! 👋</h2>
          <p style="color:#ccc;font-size:16px;line-height:1.6;">
            Dziękuję za zakup <strong style="color:#ff00ff;">HUSTLER PACK</strong>.
            Twój link do pobrania jest gotowy — kliknij poniżej:
          </p>
          <div style="text-align:center;margin:30px 0;">
            <a href="{download_url}"
               style="display:inline-block;background:linear-gradient(135deg,#ff00ff,#cc00cc);
                      color:#fff;text-decoration:none;padding:16px 40px;border-radius:8px;
                      font-size:18px;font-weight:bold;letter-spacing:1px;">
              📥 POBIERZ SWÓJ PACK
            </a>
          </div>
          <p style="color:#888;font-size:13px;line-height:1.5;">
            Link jest ważny przez <strong>48 godzin</strong> i może być użyty tylko raz.
            Jeśli masz problem, napisz na IG: <strong>@cvv_tony</strong>
          </p>
        </div>
        <p style="color:#444;font-size:12px;text-align:center;margin-top:30px;">
          © cvvtony.pl — Nie udostępniaj tego linku innym osobom.
        </p>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, email, msg.as_string())
        print(f"[EMAIL] Sent download link to {email}")
    except Exception as e:
        print(f"[EMAIL] Failed to send to {email}: {e}")


# ===========================================================================
# PUBLIC ROUTES
# ===========================================================================

@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request, db: Session = Depends(get_db)):
    """Render the main landing page."""
    product = db.query(Product).first()
    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "product": product,
            "highlights": highlights,
            "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY,
        }
    )


@app.post("/create-checkout-session")
def create_checkout_session(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
):
    """Create a Stripe Checkout Session for one-time payment."""
    product = db.query(Product).first()
    if not product:
        raise HTTPException(status_code=500, detail="Product not found")

    # Validate email
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Nieprawidłowy adres e-mail")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card", "blik", "p24"],
            line_items=[{
                "price_data": {
                    "currency": product.currency,
                    "product_data": {
                        "name": product.name,
                        "description": product.description,
                    },
                    "unit_amount": product.price,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{SITE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{SITE_URL}/#pricing",
            customer_email=email,  # Pre-fill email in Stripe checkout
        )
        if not session.url:
            raise HTTPException(status_code=500, detail="Stripe checkout session URL is empty")
        return RedirectResponse(session.url, status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(None),
):
    """Handle Stripe webhook events — process completed payments."""
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event: Any = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session_data: Any = event["data"]["object"]
        session_id: str = session_data["id"]
        customer_email: str = session_data.get("customer_details", {}).get("email", "") or ""
        amount: int = session_data.get("amount_total", 0) or 0
        currency: str = session_data.get("currency", "pln") or "pln"

        # Check for duplicate
        existing = db.query(Order).filter_by(stripe_session_id=session_id).first()
        if existing:
            return JSONResponse({"status": "already_processed"})

        # Record order
        order = Order(
            stripe_session_id=session_id,
            email=customer_email,
            amount=amount,
            currency=currency,
            status="completed",
        )
        db.add(order)

        # Generate download token
        token = DownloadToken(
            token=uuid.uuid4().hex,
            email=customer_email,
        )
        db.add(token)
        db.commit()

        # Send email with download link in background
        download_url = f"{SITE_URL}/download/{token.token}"
        background_tasks.add_task(send_download_email, customer_email, download_url)

    return JSONResponse({"status": "success"})


@app.get("/download/{token}", response_class=HTMLResponse)
def download_file(token: str, db: Session = Depends(get_db)):
    """Serve the PDF file if the download token is valid."""
    dl_token = db.query(DownloadToken).filter_by(token=token).first()

    if not dl_token or not dl_token.is_valid:
        raise HTTPException(
            status_code=403,
            detail="Link wygasł lub jest nieprawidłowy. Napisz na IG @cvv_tony po pomoc."
        )

    product = db.query(Product).first()
    if not product or not product.pdf_filename:
        raise HTTPException(status_code=404, detail="Plik PDF nie został jeszcze ustawiony.")

    pdf_path = UPLOAD_DIR / product.pdf_filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Plik PDF nie został znaleziony na serwerze.")

    # Mark token as used
    dl_token.used = True
    db.commit()

    return FileResponse(
        path=str(pdf_path),
        filename=product.pdf_filename,
        media_type="application/pdf",
    )


@app.get("/success", response_class=HTMLResponse)
def success_page(request: Request, db: Session = Depends(get_db)):
    """Post-payment thank-you page."""
    product = db.query(Product).first()
    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "product": product,
            "highlights": highlights,
            "reviews": [],
            "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY,
            "show_success": True,
        }
    )


@app.get("/regulamin", response_class=HTMLResponse)
def regulamin_page(request: Request, db: Session = Depends(get_db)):
    """Render Terms of Service page."""
    product = db.query(Product).first()
    return templates.TemplateResponse(
        request=request,
        name="regulamin.html",
        context={
            "product": product,
        }
    )


@app.get("/polityka-prywatnosci", response_class=HTMLResponse)
def polityka_page(request: Request, db: Session = Depends(get_db)):
    """Render Privacy Policy page."""
    product = db.query(Product).first()
    return templates.TemplateResponse(
        request=request,
        name="polityka.html",
        context={
            "product": product,
        }
    )


# ===========================================================================
# ADMIN ROUTES
# ===========================================================================

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request, db: Session = Depends(get_db)):
    """Show admin login form."""
    product = db.query(Product).first()
    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "logged_in": False,
            "product": product,
            "highlights": highlights,
            "reviews": [],
            "message": "",
        }
    )


@app.post("/admin/login")
def admin_login(request: Request, db: Session = Depends(get_db), password: str = Form(...)):
    """Authenticate admin."""
    product = db.query(Product).first()
    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()
    if password == ADMIN_PASSWORD:
        request.session["admin_logged_in"] = True
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "logged_in": False,
            "product": product,
            "highlights": highlights,
            "reviews": [],
            "message": "❌ Nieprawidłowe hasło",
        }
    )


@app.get("/admin/logout")
def admin_logout(request: Request):
    """Logout admin."""
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Render admin CMS panel."""
    if not request.session.get("admin_logged_in"):
        return RedirectResponse("/admin/login", status_code=303)
    product = db.query(Product).first()
    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "logged_in": True,
            "product": product,
            "highlights": highlights,
            "reviews": [],
            "message": "",
        }
    )


@app.post("/admin/product")
def update_product(
    request: Request,
    db: Session = Depends(get_db),
    price: str = Form(""),
    hero_headline: str = Form(""),
    hero_subtext: str = Form(""),
    description: str = Form(""),
    method_1_title: str = Form(""),
    method_1_subtitle: str = Form(""),
    method_1_desc: str = Form(""),
    method_2_title: str = Form(""),
    method_2_subtitle: str = Form(""),
    method_2_desc: str = Form(""),
    method_3_title: str = Form(""),
    method_3_subtitle: str = Form(""),
    method_3_desc: str = Form(""),
    method_4_title: str = Form(""),
    method_4_subtitle: str = Form(""),
    method_4_desc: str = Form(""),
    ig_username: str = Form(""),
    ig_posts_count: str = Form(""),
    ig_followers_count: str = Form(""),
    ig_following_count: str = Form(""),
    ig_bio_title: str = Form(""),
    ig_bio_text_1: str = Form(""),
    ig_bio_text_2: str = Form(""),
):
    """Update product details from admin form."""
    check_admin(request)
    product = db.query(Product).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Convert price from PLN string to grosze int
    try:
        price_float = float(price.replace(",", "."))
        product.price = int(price_float * 100)
    except (ValueError, AttributeError):
        pass

    if hero_headline:
        product.hero_headline = hero_headline
    if hero_subtext:
        product.hero_subtext = hero_subtext
    if description:
        product.description = description
    
    if method_1_title:
        product.method_1_title = method_1_title
    if method_1_subtitle:
        product.method_1_subtitle = method_1_subtitle
    if method_1_desc:
        product.method_1_desc = method_1_desc

    if method_2_title:
        product.method_2_title = method_2_title
    if method_2_subtitle:
        product.method_2_subtitle = method_2_subtitle
    if method_2_desc:
        product.method_2_desc = method_2_desc

    if method_3_title:
        product.method_3_title = method_3_title
    if method_3_subtitle:
        product.method_3_subtitle = method_3_subtitle
    if method_3_desc:
        product.method_3_desc = method_3_desc

    if method_4_title:
        product.method_4_title = method_4_title
    if method_4_subtitle:
        product.method_4_subtitle = method_4_subtitle
    if method_4_desc:
        product.method_4_desc = method_4_desc

    # Save Instagram mock configuration fields
    if ig_username:
        product.ig_username = ig_username
    if ig_posts_count:
        product.ig_posts_count = ig_posts_count
    if ig_followers_count:
        product.ig_followers_count = ig_followers_count
    if ig_following_count:
        product.ig_following_count = ig_following_count
    if ig_bio_title:
        product.ig_bio_title = ig_bio_title
    if ig_bio_text_1:
        product.ig_bio_text_1 = ig_bio_text_1
    if ig_bio_text_2:
        product.ig_bio_text_2 = ig_bio_text_2

    db.commit()
    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "logged_in": True,
            "product": product,
            "highlights": highlights,
            "reviews": [],
            "message": "✅ Produkt zaktualizowany!",
        }
    )


@app.post("/admin/upload-pdf")
def upload_pdf(
    request: Request,
    db: Session = Depends(get_db),
    pdf_file: UploadFile = File(...),
):
    """Upload or replace the product PDF file."""
    check_admin(request)

    if not pdf_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Dozwolone są tylko pliki PDF.")

    product = db.query(Product).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Remove old file if exists
    if product.pdf_filename:
        old_path = UPLOAD_DIR / product.pdf_filename
        if old_path.exists():
            old_path.unlink()

    # Save new file with sanitized name
    safe_name = f"hustler_pack_{uuid.uuid4().hex[:8]}.pdf"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        content = pdf_file.file.read()
        f.write(content)

    product.pdf_filename = safe_name
    db.commit()

    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "logged_in": True,
            "product": product,
            "highlights": highlights,
            "reviews": [],
            "message": f"✅ PDF wgrany: {safe_name}",
        }
    )


@app.post("/admin/upload-logo")
def upload_logo(
    request: Request,
    db: Session = Depends(get_db),
    logo_file: UploadFile = File(...),
):
    """Upload or replace the store profile logo/image."""
    check_admin(request)

    # Validate image mime/ext
    ext = logo_file.filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp", "gif"]:
        raise HTTPException(status_code=400, detail="Dozwolone formaty obrazów: JPG, PNG, WEBP, GIF.")

    product = db.query(Product).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    logo_dir = BASE_DIR / "logo"
    logo_dir.mkdir(parents=True, exist_ok=True)

    # Remove old logo if it wasn't the default or if we want to save a clean name
    # We will save the file with a unique name to prevent browser cache problems!
    if product.logo_filename and product.logo_filename != "logo_cvvtony.jpg":
        old_path = logo_dir / product.logo_filename
        if old_path.exists():
            try:
                old_path.unlink()
            except Exception:
                pass

    # Save new image with a cache-busting unique name
    safe_name = f"logo_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = logo_dir / safe_name
    with open(file_path, "wb") as f:
        content = logo_file.file.read()
        f.write(content)

    product.logo_filename = safe_name
    db.commit()

    highlights = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "logged_in": True,
            "product": product,
            "highlights": highlights,
            "reviews": [],
            "message": "✅ Logo zaktualizowane pomyślnie!",
        }
    )


# ===========================================================================
# INSTAGRAM HIGHLIGHTS CRUD
# ===========================================================================

@app.post("/admin/highlight/add")
def add_highlight(
    request: Request,
    db: Session = Depends(get_db),
    emoji: str = Form("⭐️"),
    title: str = Form(""),
    link: str = Form(""),
):
    """Add a new Instagram highlight."""
    check_admin(request)

    if not title or not link:
        raise HTTPException(status_code=400, detail="Tytuł i link są wymagane.")

    # Get the highest sort_order and add 10
    last = db.query(InstagramHighlight).order_by(InstagramHighlight.sort_order.desc()).first()
    next_order = (last.sort_order + 10) if last else 10

    highlight = InstagramHighlight(
        emoji=emoji,
        title=title.strip(),
        link=link.strip(),
        sort_order=next_order,
    )
    db.add(highlight)
    db.commit()

    return RedirectResponse("/admin?tab=instagram", status_code=303)


@app.post("/admin/highlight/delete/{highlight_id}")
def delete_highlight(
    highlight_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete an Instagram highlight by ID."""
    check_admin(request)

    highlight = db.query(InstagramHighlight).filter_by(id=highlight_id).first()
    if highlight:
        db.delete(highlight)
        db.commit()

    return RedirectResponse("/admin?tab=instagram", status_code=303)


@app.post("/admin/highlight/edit/{highlight_id}")
def edit_highlight(
    highlight_id: int,
    request: Request,
    db: Session = Depends(get_db),
    emoji: str = Form("⭐️"),
    title: str = Form(""),
    link: str = Form(""),
):
    """Edit an existing Instagram highlight."""
    check_admin(request)

    highlight = db.query(InstagramHighlight).filter_by(id=highlight_id).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    if emoji:
        highlight.emoji = emoji
    if title:
        highlight.title = title.strip()
    if link:
        highlight.link = link.strip()

    db.commit()

    return RedirectResponse("/admin?tab=instagram", status_code=303)


@app.post("/admin/highlight/clear-all")
def clear_all_highlights(
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete all highlights from the database."""
    check_admin(request)
    db.query(InstagramHighlight).delete()
    db.commit()
    return RedirectResponse("/admin?tab=instagram", status_code=303)


# Run entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
