"""
models.py — SQLAlchemy ORM models for the HUSTLER PACK store.
CVV Tony — cvvtony.pl
"""

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    """Single-product store — only one row expected."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="HUSTLER PACK")
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=14900)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="pln")
    hero_headline: Mapped[str] = mapped_column(String(300), nullable=False, default="PAKIET METOD HUSTLER")
    hero_subtext: Mapped[str] = mapped_column(Text, nullable=False, default="")
    about_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pdf_filename: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    # Methods grid content (title + subtitle + full description per method)
    method_1_title: Mapped[str] = mapped_column(String(200), nullable=False, default="Reselling cyfrowy")
    method_1_subtitle: Mapped[str] = mapped_column(String(300), nullable=False, default="Najlepsza metoda bez wkładu w 2026!")
    method_1_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    method_2_title: Mapped[str] = mapped_column(String(200), nullable=False, default="Resell fizyczny")
    method_2_subtitle: Mapped[str] = mapped_column(String(300), nullable=False, default="Pomnóż nawet 200 zł w prosty sposób")
    method_2_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    method_3_title: Mapped[str] = mapped_column(String(200), nullable=False, default="Resell kont do gier")
    method_3_subtitle: Mapped[str] = mapped_column(String(300), nullable=False, default="Kup za 20-30 zł → sprzedaj za 30-40$")
    method_3_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    method_4_title: Mapped[str] = mapped_column(String(200), nullable=False, default="Digital e-commerce")
    method_4_subtitle: Mapped[str] = mapped_column(String(300), nullable=False, default="Stwórz raz — sprzedawaj bez limitu")
    method_4_desc: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Instagram mockup configuration
    ig_username: Mapped[str] = mapped_column(String(100), nullable=False, default="cvv_tony")
    ig_posts_count: Mapped[str] = mapped_column(String(50), nullable=False, default="5")
    ig_followers_count: Mapped[str] = mapped_column(String(50), nullable=False, default="13,2k")
    ig_following_count: Mapped[str] = mapped_column(String(50), nullable=False, default="0")
    ig_bio_title: Mapped[str] = mapped_column(String(200), nullable=False, default="Bóg Zarabiania 📲💸")
    ig_bio_text_1: Mapped[str] = mapped_column(String(300), nullable=False, default="hustler, top metody w 🇵🇱, +1200 opinii")
    ig_bio_text_2: Mapped[str] = mapped_column(String(300), nullable=False, default="NOWY PAKIET METOD \"HUSTLER PACK\" 🏆⬇️")
    logo_filename: Mapped[str] = mapped_column(String(500), nullable=False, default="logo_cvvtony.jpg")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def price_display(self) -> str:
        """Format price in PLN: 14900 -> '149.00'"""
        return f"{self.price / 100:.2f}"

    @property
    def price_zloty(self) -> int:
        """Full zloty part: 14900 -> 149"""
        return self.price // 100

    @property
    def price_grosze(self) -> str:
        """Grosze part: 14900 -> '00'"""
        return f"{self.price % 100:02d}"


class Review(Base):
    """Screenshot-based IG review images."""
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str] = mapped_column(String(300), nullable=False, default="Recenzja klienta")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DownloadToken(Base):
    """Time-limited, single-use download tokens for purchased PDFs."""
    __tablename__ = "download_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=48)
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def is_valid(self) -> bool:
        """Check if the token is still usable."""
        now = datetime.now(timezone.utc)
        return not self.used and self.expires_at > now


class Order(Base):
    """Record of completed Stripe payments."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stripe_session_id: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="pln")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class InstagramHighlight(Base):
    """Instagram Highlight bubble link."""
    __tablename__ = "instagram_highlights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emoji: Mapped[str] = mapped_column(String(50), nullable=False, default="⭐️")
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="OPINIE")
    link: Mapped[str] = mapped_column(String(500), nullable=False, default="https://instagram.com")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
