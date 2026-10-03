"""Official U.S. House Clerk financial-disclosure index adapter (Phase 5, experimental).

The Clerk publishes one yearly ZIP index (``{YEAR}FD.zip``) listing every filing. Periodic
Transaction Reports (FilingType "P") link to a PDF. This adapter:

* downloads at most one index per year requested (polite, cached on disk),
* filters filings for a member's last name (default "Pelosi"),
* returns filing metadata + the official PDF URL.

It does NOT parse transactions out of the PDFs. Transcribe them (or use a vetted parser)
and load them through ``POST /api/trades/import`` with confidence_level=official.
"""
from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import httpx

from ...config import BASE_DIR, get_settings
from .base import CongressionalTradesProvider, RawTrade

log = logging.getLogger(__name__)
INDEX_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
PTR_URL = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
CACHE = BASE_DIR / "data" / "house_index"


@dataclass
class Filing:
    name: str
    filing_type: str
    state_district: str
    filing_date: date
    doc_id: str
    year: int
    pdf_url: str


class HouseClerkProvider(CongressionalTradesProvider):
    name = "house_clerk"

    def __init__(self, last_name: str = "Pelosi") -> None:
        self.last_name = last_name
        self.s = get_settings()

    def _index_bytes(self, year: int) -> bytes:
        CACHE.mkdir(parents=True, exist_ok=True)
        f = CACHE / f"{year}FD.zip"
        # refresh the current year at most once a day; past years are immutable
        if f.exists() and (year < date.today().year or
                           datetime.fromtimestamp(f.stat().st_mtime).date() == date.today()):
            return f.read_bytes()
        r = httpx.get(INDEX_URL.format(year=year), timeout=self.s.http_timeout_s,
                      headers={"User-Agent": self.s.http_user_agent}, follow_redirects=True)
        r.raise_for_status()
        f.write_bytes(r.content)
        return r.content

    def list_filings(self, years: list[int]) -> list[Filing]:
        out: list[Filing] = []
        for y in years:
            try:
                z = zipfile.ZipFile(io.BytesIO(self._index_bytes(y)))
                xml_name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
                root = ET.fromstring(z.read(xml_name))
            except Exception as e:  # network or format problem — never crash the app
                log.warning("House index %s unavailable: %s", y, e)
                continue
            for m in root.iter("Member"):
                last = (m.findtext("Last") or "").strip()
                if last.lower() != self.last_name.lower():
                    continue
                ftype = (m.findtext("FilingType") or "").strip()
                doc = (m.findtext("DocID") or "").strip()
                try:
                    fdate = datetime.strptime((m.findtext("FilingDate") or "").strip(), "%m/%d/%Y").date()
                except ValueError:
                    continue
                out.append(Filing(
                    name=f"{m.findtext('First', '')} {last}".strip(), filing_type=ftype,
                    state_district=m.findtext("StateDst", ""), filing_date=fdate, doc_id=doc,
                    year=y, pdf_url=PTR_URL.format(year=y, doc_id=doc) if ftype == "P" else "",
                ))
        return sorted(out, key=lambda f: f.filing_date, reverse=True)

    def fetch(self, since: date | None = None) -> list[RawTrade]:
        # Transactions live inside PDFs; see module docstring.
        log.info("house_clerk.fetch returns filing metadata only; import transactions via CSV.")
        return []
