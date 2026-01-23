"""
customers.utils
===============

Funzioni **side-effect free** riutilizzabili nel blueprint *customers*.

Contenuti principali
--------------------
* **slugify**              – slug ASCII-safe da testo arbitrario
* **snake_to_title**       – “snake_case” → “Title Case”
* **is_valid_phone**       – validazione internazionale semplificata
* **decimal_or_none**      – conversione robusta a ``Decimal``
* **safe_int / safe_date** – parsing numeri / date con fallback
* **chunked / first**      – helper iterabili
* **iter_excel_rows**      – lettura Excel/CSV (dip. facoltativa *pandas*)
* **create_progress_collage** – crea collage progresso confrontando foto
"""

from __future__ import annotations

import csv
import decimal
import itertools
import re
import unicodedata
from contextlib import suppress
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

T = TypeVar("T")

__all__ = [
    "slugify",
    "snake_to_title",
    "is_valid_phone",
    "decimal_or_none",
    "safe_int",
    "safe_date",
    "chunked",
    "first",
    "iter_excel_rows",
    "create_progress_collage",
]

# --------------------------------------------------------------------------- #
#  String helpers                                                             #
# --------------------------------------------------------------------------- #

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, sep: str = "-", lower: bool = True) -> str:
    """
    Ritorna uno *slug* ASCII-safe.

    >>> slugify(\"L'Élite del Benessere!\")
    'l-elite-del-benessere'
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")

    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    if lower:
        ascii_text = ascii_text.lower()

    slug = _SLUG_RE.sub(sep, ascii_text).strip(sep)
    slug = re.sub(rf"{re.escape(sep)}{{2,}}", sep, slug)  # comprime separatori doppi
    return slug


def snake_to_title(identifier: str) -> str:
    """'stato_cliente' → 'Stato Cliente'."""
    return " ".join(part.capitalize() for part in identifier.split("_") if part)


# --------------------------------------------------------------------------- #
#  Validazione telefono                                                       #
# --------------------------------------------------------------------------- #

_PHONE_RE = re.compile(r"^\+?\d{5,15}$")


def is_valid_phone(value: str) -> bool:
    """Controllo molto permissivo (E.164 semplificato)."""
    return bool(_PHONE_RE.match(value or ""))


# --------------------------------------------------------------------------- #
#  Conversion helpers                                                         #
# --------------------------------------------------------------------------- #


def decimal_or_none(value: Any) -> Optional[decimal.Decimal]:
    """Restituisce ``Decimal`` o ``None``."""
    if value in (None, ""):
        return None
    try:
        return decimal.Decimal(str(value))
    except decimal.InvalidOperation as exc:
        raise ValueError(f"Valore non numerico: {value!r}") from exc


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """``int(value)`` con fallback *default*."""
    with suppress((TypeError, ValueError)):
        return int(value)
    return default


def safe_date(value: Any, default: Optional[date] = None) -> Optional[date]:
    """
    Converte *value* in :class:`datetime.date`.

    Supporta:
    • oggetti ``date`` / ``datetime``  
    • ISO string "YYYY-MM-DD"  
    • Seriali Excel (base 1899-12-30)
    """
    if value in (None, ""):
        return default

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    if isinstance(value, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(value))

    if isinstance(value, str):
        with suppress(ValueError):
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()

    return default


# --------------------------------------------------------------------------- #
#  Iterable helpers                                                           #
# --------------------------------------------------------------------------- #


def chunked(iterable: Iterable[T], size: int) -> Iterator[List[T]]:
    """Iterator che restituisce liste di lunghezza ``size``."""
    it = iter(iterable)
    while chunk := list(itertools.islice(it, size)):
        yield chunk


def first(iterable: Iterable[T], default: Optional[T] = None) -> Optional[T]:
    """Primo elemento di ``iterable`` o *default* se vuoto."""
    return next(iter(iterable), default)


# --------------------------------------------------------------------------- #
#  Excel / CSV                                                                #
# --------------------------------------------------------------------------- #

try:
    import pandas as _pd

    _PANDAS_OK = True
except ModuleNotFoundError:  # pragma: no cover
    _PANDAS_OK = False


def iter_excel_rows(
    path: str | Path,
    *,
    sheet_name: str | int | None = 0,
    as_dict: bool = True,
    dtype: Mapping[str, Any] | None = None,
) -> Generator[Dict[str, Any] | List[Any], None, None]:
    """
    Itera le righe di un file Excel/CSV.

    Se *pandas* non è installato, è consentito solo il formato CSV.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    # CSV path o fallback se pandas assente
    if path.suffix.lower() == ".csv" or not _PANDAS_OK:
        if path.suffix.lower() != ".csv":
            raise RuntimeError(
                "Per leggere file Excel installa `pandas` + `openpyxl` "
                "o converti il file in CSV."
            )
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh) if as_dict else csv.reader(fh)
            yield from reader
        return

    df = _pd.read_excel(path, sheet_name=sheet_name, dtype=dtype)
    if as_dict:
        for record in df.to_dict(orient="records"):
            yield record
    else:  # list
        for row in df.itertuples(index=False, name=None):
            yield list(row)


# --------------------------------------------------------------------------- #
#  Collage Progresso                                                          #
# --------------------------------------------------------------------------- #

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:  # pragma: no cover
    _PIL_OK = False


def create_progress_collage(
    initial_photos: Dict[str, Optional[str]],
    latest_photos: Dict[str, Optional[str]],
    *,
    image_size: Tuple[int, int] = (600, 800),
    padding: int = 20,
    label_height: int = 40,
    initial_date: Optional[str] = None,
    latest_date: Optional[str] = None,
) -> bytes:
    """
    Crea un collage progresso confrontando foto iniziali e finali.

    Args:
        initial_photos: Dict con chiavi 'front', 'side', 'back' e valori path file o None
        latest_photos: Dict con chiavi 'front', 'side', 'back' e valori path file o None
        image_size: Dimensione di ogni foto nel collage (width, height)
        padding: Spazio tra le foto
        label_height: Altezza delle etichette
        initial_date: Data prima foto (opzionale)
        latest_date: Data ultima foto (opzionale)

    Returns:
        bytes: Immagine collage in formato JPEG

    Raises:
        RuntimeError: Se PIL non è installato
        ValueError: Se nessuna foto è disponibile
    """
    if not _PIL_OK:
        raise RuntimeError("Pillow (PIL) è richiesto per creare il collage")

    # Verifica che ci sia almeno una foto
    has_photos = any(
        initial_photos.get(k) or latest_photos.get(k)
        for k in ['front', 'side', 'back']
    )
    if not has_photos:
        raise ValueError("Nessuna foto disponibile per creare il collage")

    # Dimensioni canvas finale
    # 3 righe (frontale, laterale, posteriore) × 2 colonne (prima, dopo)
    canvas_width = (image_size[0] * 2) + (padding * 3)
    canvas_height = (image_size[1] * 3) + (label_height * 3) + (padding * 4)

    # Crea canvas bianco
    canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')
    draw = ImageDraw.Draw(canvas)

    # Prova a caricare un font, fallback a default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            small_font = ImageFont.truetype("arial.ttf", 18)
        except (OSError, IOError):
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

    # Funzione helper per caricare e ridimensionare immagine
    def load_and_resize_image(path: Optional[str], target_size: Tuple[int, int]) -> Optional[Image.Image]:
        """Carica e ridimensiona un'immagine mantenendo le proporzioni.

        Supporta:
        - URL remoti (http:// o https://)
        - Path locali assoluti o relativi
        """
        if not path:
            return None

        try:
            import os
            from io import BytesIO
            import logging
            logger = logging.getLogger(__name__)

            img = None

            # Controlla se è un URL remoto
            if path.startswith('http://') or path.startswith('https://'):
                try:
                    import requests
                    logger.debug(f"Scaricando immagine da URL: {path[:100]}...")
                    response = requests.get(path, timeout=30, stream=True)
                    response.raise_for_status()
                    img = Image.open(BytesIO(response.content))
                    logger.debug(f"Immagine scaricata con successo: {img.size}")
                except ImportError:
                    # Fallback a urllib se requests non è disponibile
                    import urllib.request
                    logger.debug(f"Usando urllib per scaricare: {path[:100]}...")
                    with urllib.request.urlopen(path, timeout=30) as response:
                        img = Image.open(BytesIO(response.read()))
                except Exception as e:
                    logger.error(f"Errore download immagine da {path[:100]}: {e}")
                    return None
            else:
                # File locale
                if not os.path.isabs(path):
                    # Path relativo - prova da static/ o dalla root del progetto
                    possible_paths = [
                        path,  # Path originale
                        os.path.join('static', path),  # Da static/
                        os.path.join('corposostenibile', 'static', path),  # Da corposostenibile/static/
                    ]

                    # Prova anche con flask current_app se disponibile
                    try:
                        from flask import current_app
                        if current_app and current_app.static_folder:
                            possible_paths.insert(0, os.path.join(current_app.static_folder, path))
                    except (RuntimeError, ImportError):
                        pass

                    img_path = None
                    for p in possible_paths:
                        if os.path.exists(p):
                            img_path = p
                            break

                    if not img_path:
                        logger.warning(f"File locale non trovato: {path}")
                        return None
                else:
                    img_path = path

                if not os.path.exists(img_path):
                    logger.warning(f"File non esiste: {img_path}")
                    return None

                img = Image.open(img_path)

            if img is None:
                return None

            # Converti RGBA in RGB se necessario
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Ridimensiona mantenendo proporzioni
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # Crea nuova immagine centrata
            new_img = Image.new('RGB', target_size, color='#f0f0f0')
            x_offset = (target_size[0] - img.size[0]) // 2
            y_offset = (target_size[1] - img.size[1]) // 2
            new_img.paste(img, (x_offset, y_offset))

            return new_img
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Errore caricamento immagine {path}: {e}")
            return None

    # Funzione per creare placeholder grigio
    def create_placeholder(size: Tuple[int, int], text: str = "N/A") -> Image.Image:
        """Crea un placeholder grigio con testo."""
        placeholder = Image.new('RGB', size, color='#e0e0e0')
        draw_ph = ImageDraw.Draw(placeholder)
        # Disegna testo centrato
        bbox = draw_ph.textbbox((0, 0), text, font=small_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        draw_ph.text((x, y), text, fill='#999999', font=small_font)
        return placeholder

    # Posizioni per le 3 righe
    views = [
        ('front', 'Frontale'),
        ('side', 'Laterale'),
        ('back', 'Posteriore')
    ]

    y_pos = padding

    for view_key, view_label in views:
        # Etichetta vista
        label_text = f"{view_label}:"
        draw.text((padding, y_pos), label_text, fill='#333333', font=font)
        y_pos += label_height

        # Colonna sinistra: foto iniziale
        x_left = padding
        initial_img = load_and_resize_image(initial_photos.get(view_key), image_size)
        if initial_img:
            canvas.paste(initial_img, (x_left, y_pos))
        else:
            placeholder = create_placeholder(image_size, "Prima")
            canvas.paste(placeholder, (x_left, y_pos))

        # Etichetta "Prima"
        label_y = y_pos + image_size[1] + 5
        date_text = f"Prima{(' - ' + initial_date) if initial_date else ''}"
        draw.text((x_left, label_y), date_text, fill='#666666', font=small_font)

        # Colonna destra: foto ultima
        x_right = padding + image_size[0] + padding
        latest_img = load_and_resize_image(latest_photos.get(view_key), image_size)
        if latest_img:
            canvas.paste(latest_img, (x_right, y_pos))
        else:
            placeholder = create_placeholder(image_size, "Dopo")
            canvas.paste(placeholder, (x_right, y_pos))

        # Etichetta "Dopo"
        date_text = f"Dopo{(' - ' + latest_date) if latest_date else ''}"
        draw.text((x_right, label_y), date_text, fill='#666666', font=small_font)

        # Prossima riga
        y_pos += image_size[1] + label_height + padding

    # Converti in bytes JPEG
    from io import BytesIO
    output = BytesIO()
    canvas.save(output, format='JPEG', quality=90, optimize=True)
    return output.getvalue()
