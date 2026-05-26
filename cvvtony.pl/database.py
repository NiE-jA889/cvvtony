"""
database.py — SQLAlchemy engine, session factory, and database initialization.
CVV Tony HUSTLER PACK — cvvtony.pl
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Product, Review, DownloadToken, Order, InstagramHighlight

DATABASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'app.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and seed default product if the database is empty."""
    os.makedirs(DATABASE_DIR, exist_ok=True)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        product = db.query(Product).first()
        if product is None:
            default_product = Product(
                name="HUSTLER PACK",
                price=14900,
                currency="pln",
                hero_headline="PAKIET METOD HU$TLER",
                hero_subtext=(
                    "Kompletny zestaw sprawdzonych metod zarabiania — "
                    "od zera do pierwszych realnych pieniędzy. "
                    "Bez kapitału, bez doświadczenia, bez bullshitu."
                ),
                about_text="",
                description=(
                    "PDF zawierający kompletny zestaw metod zarobkowych "
                    "dla ambitnych hustlerów."
                ),
                pdf_filename="",
                method_1_title="Reselling cyfrowy",
                method_1_subtitle="Najlepsza metoda bez wkładu w 2026!",
                method_1_desc=(
                    "Zacznij flipować przeróżnymi produktami cyfrowymi, których domaga się każdy! "
                    "Normalnie kosztują setki złotych, a my ci pokażemy jak i gdzie kupisz je za dosłownie grosze. "
                    "Dokładnie powiemy ci jakimi produktami powinieneś handlować oraz jak i gdzie je sprzedawać, aby robić dobre dniówki."
                ),
                method_2_title="Resell fizyczny",
                method_2_subtitle="Pomnóż nawet 200 zł w prosty sposób",
                method_2_desc=(
                    "W pakiecie HUSTLER handlujemy wieloma rzeczami — nie znajdziesz tutaj tylko jednego typu produktu. "
                    "Posiadamy parę produktów fizycznych, które podbijają 2026 rok swoją sprzedażą i zasięgami! "
                    "Idealna metoda, jeśli masz chociaż trochę wolnego siana i chciałbyś to w prosty i przyjemny sposób pomnożyć."
                ),
                method_3_title="Resell kont do gier",
                method_3_subtitle="Kup za 20-30 zł → sprzedaj za 30-40$",
                method_3_desc=(
                    "W Polsce konta do gier kosztują tyle co kebab — za to te same konta za granicą kosztują minimum 3-4x więcej. "
                    "Flip takim kontem możesz zrobić dosłownie w godzinę. Pokażemy ci dokładnie jakiej kluczowej platformy używamy, "
                    "jak pozyskać takie konta oraz magiczne źródło, gdzie te konta sprzedajesz błyskawicznie i w nielimitowanych ilościach."
                ),
                method_4_title="Digital e-commerce",
                method_4_subtitle="Stwórz raz — sprzedawaj bez limitu",
                method_4_desc=(
                    "Wymarzony biznes e-com — tworzysz produkt raz, a sprzedajesz go w nielimitowanych ilościach. "
                    "Metodę rozpisaliśmy we współpracy z kolegą, który na tego typu produktach zarabia od grubo ponad 3 lat. "
                    "Przekażemy ci wiedzę od zera: jak stworzyć produkt, mieć pierwsze sprzedaże, a potem skalować do paru stówek dziennie pracując 20-30 minut."
                ),
                ig_username="cvv_tony",
                ig_posts_count="5",
                ig_followers_count="13,2k",
                ig_following_count="0",
                ig_bio_title="Bóg Zarabiania 📲💸",
                ig_bio_text_1="hustler, top metody w 🇵🇱, +1200 opinii",
                ig_bio_text_2="NOWY PAKIET METOD \"HUSTLER PACK\" 🏆⬇️",
                logo_filename="logo_cvvtony.jpg",
            )
            db.add(default_product)
            db.commit()
            print("[DB] Default product seeded.")
        else:
            updated = False
            if "HU$TLER PACK" in product.name:
                product.name = product.name.replace("HU$TLER PACK", "HUSTLER PACK")
                updated = True
            if "PAKIET METOD HUSTLER" in product.hero_headline:
                product.hero_headline = product.hero_headline.replace("PAKIET METOD HUSTLER", "PAKIET METOD HU$TLER")
                updated = True
            if "hu$tler, top metody" in product.ig_bio_text_1:
                product.ig_bio_text_1 = product.ig_bio_text_1.replace("hu$tler, top metody", "hustler, top metody")
                updated = True
            if "NOWY PAKIET METOD \"HU$TLER PACK\"" in product.ig_bio_text_2:
                product.ig_bio_text_2 = product.ig_bio_text_2.replace("NOWY PAKIET METOD \"HU$TLER PACK\"", "NOWY PAKIET METOD \"HUSTLER PACK\"")
                updated = True
            if updated:
                db.commit()
                print("[DB] Reverted non-hero HU$TLER to HUSTLER in existing DB.")
            else:
                print("[DB] Product already exists and is up to date, skipping seed.")

        # Seed default highlights if count != 15 to ensure all highlights are present
        highlight_count = db.query(InstagramHighlight).count()
        if highlight_count != 15:
            # Clear existing to prevent duplicates
            db.query(InstagramHighlight).delete()
            default_highlights = [
                InstagramHighlight(
                    emoji="😈",
                    title="NOWY PAKIET",
                    link="https://www.instagram.com/stories/highlights/18057041216718866/",
                    sort_order=10
                ),
                InstagramHighlight(
                    emoji="📈",
                    title="METODY",
                    link="https://www.instagram.com/stories/highlights/18062582147531721/",
                    sort_order=20
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.12",
                    link="https://www.instagram.com/stories/highlights/18094688783007704/",
                    sort_order=30
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.11",
                    link="https://www.instagram.com/stories/highlights/18089808254325694/",
                    sort_order=40
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.10",
                    link="https://www.instagram.com/stories/highlights/18537978247055476/",
                    sort_order=50
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.9",
                    link="https://www.instagram.com/stories/highlights/18183352834354194/",
                    sort_order=60
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.8",
                    link="https://www.instagram.com/stories/highlights/18050313599190258/",
                    sort_order=70
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.7",
                    link="https://www.instagram.com/stories/highlights/18043194260102636/",
                    sort_order=80
                ),
                InstagramHighlight(
                    emoji="🌴",
                    title="życie",
                    link="https://www.instagram.com/stories/highlights/18007462690548378/",
                    sort_order=90
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.6",
                    link="https://www.instagram.com/stories/highlights/17883996675146446/",
                    sort_order=100
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.5",
                    link="https://www.instagram.com/stories/highlights/18126216754332177/",
                    sort_order=110
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.4",
                    link="https://www.instagram.com/stories/highlights/18265572937227167/",
                    sort_order=120
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.3",
                    link="https://www.instagram.com/stories/highlights/17995732634243563/",
                    sort_order=130
                ),
                InstagramHighlight(
                    emoji="⭐️",
                    title="OPINIE V.2",
                    link="https://www.instagram.com/stories/highlights/17994395123012309/",
                    sort_order=140
                ),
                InstagramHighlight(
                    emoji="📲",
                    title="OPINIE",
                    link="https://www.instagram.com/stories/highlights/17986745428674570/",
                    sort_order=150
                ),
            ]
            db.add_all(default_highlights)
            db.commit()
            print("[DB] Default Instagram highlights re-seeded.")
    finally:
        db.close()
