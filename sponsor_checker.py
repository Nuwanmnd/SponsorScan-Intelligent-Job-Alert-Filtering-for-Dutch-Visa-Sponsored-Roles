
import requests
import pandas as pd
from bs4 import BeautifulSoup
from thefuzz import process, fuzz
import os
import re
import logging
import traceback
from io import StringIO

# Configuration
IND_URL = "https://ind.nl/en/public-register-recognised-sponsors/public-register-regular-labour-and-highly-skilled-migrants"
LOCAL_SPONSOR_FILE = "sponsors.csv"
CACHE_FILE = "cached_sponsors.csv"

class SponsorChecker:
    def __init__(self):
        self.sponsors = set() # Set of clean names for fast lookup
        self.logger = logging.getLogger(__name__)

    def fetch_sponsor_list(self):
        """
        Orchestrates loading and updating the sponsor list.
        Uses SQLite as the primary source of truth.
        """
        try:
            from database import SessionLocal, Sponsor
        except ImportError:
            self.logger.error("Could not import from database.py. Make sure it exists.")
            return

        session = SessionLocal()
        
        # 1. Load from DB
        db_sponsors = session.query(Sponsor).all()
        if db_sponsors:
            self.sponsors = {s.clean_name for s in db_sponsors if s.clean_name}
            self.logger.info(f"Loaded {len(self.sponsors)} sponsors from Database.")
        else:
            self.logger.info("Database empty. Checking for local CSV or scraping...")
            
        # 2. Check for local CSV (migration/backup)
        local_df = pd.DataFrame()
        if os.path.exists(LOCAL_SPONSOR_FILE):
             try:
                local_df = pd.read_csv(LOCAL_SPONSOR_FILE)
                # Migrate CSV to DB if DB was empty
                if not db_sponsors and not local_df.empty:
                    self.logger.info("Migrating local CSV to Database...")
                    for _, row in local_df.iterrows():
                         name = str(row.get('Organisation', '')).strip()
                         clean = str(row.get('clean_name', '')).strip()
                         kvk = str(row.get('KvK number', '')).strip()
                         
                         if clean and len(clean) >= 3:
                             db_sponsor = Sponsor(name=name, clean_name=clean, kvk=kvk)
                             session.add(db_sponsor)
                    session.commit()
                    self.logger.info("Migration complete.")
                    # Reload set
                    db_sponsors = session.query(Sponsor).all()
                    self.sponsors = {s.clean_name for s in db_sponsors}
             except Exception as e:
                self.logger.error(f"Failed to read/migrate local CSV: {e}")

        # 3. Scrape for updates
        new_df = self._scrape_ind_website()
        
        if not new_df.empty:
            self.logger.info("Processing retrieved data...")
            new_df = self._normalize_columns(new_df)
            
            # Generate clean_name
            if 'clean_name' not in new_df.columns:
                name_col = self._get_name_column(new_df)
                if name_col:
                     new_df['clean_name'] = new_df[name_col].astype(str).apply(self._clean_company_name)

            # Update DB (Upsert logic)
            existing_clean_names = {s.clean_name for s in session.query(Sponsor.clean_name).all()} if session.query(Sponsor).first() else set()
            
            added_count = 0
            for _, row in new_df.iterrows():
                clean = row.get('clean_name')
                if clean and isinstance(clean, str) and len(clean) >= 3:
                    if clean not in existing_clean_names:
                        db_sponsor = Sponsor(
                            name=str(row.get('Organisation', '')), 
                            clean_name=clean,
                            kvk=str(row.get('KvK number', ''))
                        )
                        session.add(db_sponsor)
                        existing_clean_names.add(clean)
                        added_count += 1
            
            if added_count > 0:
                session.commit()
                self.logger.info(f"Added {added_count} new sponsors to Database.")
            else:
                self.logger.info("No new sponsors found in scrape.")

            # Update local list in memory
            self.sponsors = existing_clean_names
                 
        else:
            self.logger.warning("Scraping failed or returned empty. Using existing DB data.")

        session.close()

        if self.sponsors:
            self.logger.info(f"Active Sponsor Set loaded with {len(self.sponsors)} names.")
        else:
            self.logger.critical("No sponsor data available explicitly.")

    def _scrape_ind_website(self):
        try:
            self.logger.info(f"Attempting to scrape {IND_URL}")
            response = requests.get(IND_URL, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Download link
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and (href.lower().endswith('.csv') or href.lower().endswith('.xlsx') or href.lower().endswith('.ods')):
                    return self._download_file(href if href.startswith('http') else 'https://ind.nl' + href)

            # 2. HTML Table
            tables = soup.find_all('table')
            if tables:
                html_io = StringIO(str(tables[0]))
                return pd.read_html(html_io, header=None)[0]
                
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            return pd.DataFrame()

    def _download_file(self, url):
        try:
            r = requests.get(url, timeout=30)
            if url.lower().endswith('.csv'):
                return pd.read_csv(StringIO(r.text))
            elif url.lower().endswith('.xlsx'):
                with open(CACHE_FILE, 'wb') as f: f.write(r.content)
                return pd.read_excel(CACHE_FILE)
            elif url.lower().endswith('.ods'):
                with open(CACHE_FILE, 'wb') as f: f.write(r.content)
                return pd.read_excel(CACHE_FILE, engine='odf')
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
        return pd.DataFrame()

    def _normalize_columns(self, df):
        # Header fixing logic
        if not df.empty:
            first_row_vals = [str(x).lower() for x in df.iloc[0].tolist()]
            possible_cols_lower = ['organisation', 'organization', 'company', 'name', 'naam']
            if any(any(p in val for p in possible_cols_lower) for val in first_row_vals):
                new_header = df.iloc[0]
                # Fix dups
                if hasattr(new_header, 'duplicated') and new_header.duplicated().any():
                     new_header = [f"{h}_{i}" if new_header.duplicated()[i] else h for i, h in enumerate(new_header)]
                df = df[1:]
                df.columns = new_header
                df.reset_index(drop=True, inplace=True)
        return df

    def _get_name_column(self, df):
        possible_cols = ['Organisation', 'Organization', 'Company', 'Name', 'Naam']
        for col in df.columns:
            if any(c.lower() in str(col).lower() for c in possible_cols):
                return col
        if list(df.columns): return df.columns[0]
        return None

    def _clean_company_name(self, name):
        if not isinstance(name, str):
            return ""
        
        name = name.lower()
        
        # User defined regex
        LEGAL_NOISE = r"\b(b\.?v\.?|n\.?v\.?|bv|nv|holding|group|gro?p|netherlands|nederland|europe|the|b.v.)\b"
        
        # Remove legal noise
        name = re.sub(LEGAL_NOISE, " ", name)
        # Strip punctuation (keep only alphanumeric and spaces)
        name = re.sub(r"[^a-z0-9 ]+", "", name)
        # Normalize spaces
        name = re.sub(r"\s+", " ", name)
        
        return name.strip()

    def check_company(self, company_name):
        """Checks if company exists in the sponsor list using fuzzy matching."""
        if not company_name or not self.sponsors:
            return False
            
        cleaned_input = self._clean_company_name(company_name)
        if len(cleaned_input) < 4:
            return False
            
        # Blacklist of common words/cities that might be in sponsor list but cause false positives
        BLACKLIST = {
            'amsterdam', 'rotterdam', 'den haag', 'utrecht', 'eindhoven', 'tilburg', 
            'groningen', 'almere', 'breda', 'nijmegen', 'nederland', 'netherlands', 
            'holland', 'europe', 'big', 'the', 'van', 'het', 'act', 'link', 'job'
        }
        
        # 1. Exact match on cleaned name
        if cleaned_input in self.sponsors:
             if cleaned_input not in BLACKLIST:
                return True
        
        # 2. Fuzzy match
        try:
            result = process.extractOne(cleaned_input, list(self.sponsors), scorer=fuzz.token_set_ratio)
            if result:
                match, score = result
                if score >= 90:
                    # Filter out matches that are just blacklisted words
                    if match in BLACKLIST:
                        return False
                        
                    self.logger.info(f"Fuzzy match found: '{company_name}' -> '{match}' (Score: {score})")
                    return True
        except Exception as e:
            self.logger.debug(f"Fuzzy match failed: {e}")
            
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    checker = SponsorChecker()
    checker.fetch_sponsor_list()
    # Debug print
    print(f"Total Sponsors: {len(checker.sponsors)}")
    print(f"Is 'Google' a sponsor? {checker.check_company('Google')}")
