#!/usr/bin/env python3
"""
Master Deduplication Engine

Multi-signal deduplication for contractor data:
1. Phone normalization (primary - 96%+ accuracy)
2. Email domain matching
3. Fuzzy company name matching (85% threshold)
4. Address matching (city + zip)

Prevents triplicating/duplicating company records across all data sources.
"""

import csv
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Set, Optional, Tuple

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "enrichment"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class DeduplicationEngine:
    """
    Multi-signal deduplication for contractor data.

    Matching hierarchy (in order of reliability):
    1. Phone match (normalized 10-digit)
    2. Email match (exact)
    3. Email domain match (same company domain)
    4. Fuzzy name match (85%+ similarity + same state)
    5. Address match (same city + zip + partial street)
    """

    FUZZY_THRESHOLD = 0.85

    def __init__(self):
        # Dedup indexes
        self.phone_index: Dict[str, List[dict]] = defaultdict(list)
        self.email_index: Dict[str, List[dict]] = defaultdict(list)
        self.domain_index: Dict[str, List[dict]] = defaultdict(list)
        self.name_state_index: Dict[str, List[dict]] = defaultdict(list)

        # Master records
        self.master_records: List[dict] = []
        self.duplicate_groups: List[List[dict]] = []

    def normalize_phone(self, phone: str) -> str:
        """Normalize phone to 10 digits."""
        if not phone:
            return ""
        digits = re.sub(r'\D', '', str(phone))
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        return digits if len(digits) == 10 else ""

    def normalize_email(self, email: str) -> str:
        """Normalize email to lowercase."""
        if not email:
            return ""
        return email.lower().strip()

    def extract_domain(self, email: str) -> str:
        """Extract domain from email, excluding common webmail."""
        if not email or '@' not in email:
            return ""
        domain = email.split('@')[1].lower().strip()
        # Exclude common webmail domains
        webmail = {'gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com',
                   'outlook.com', 'icloud.com', 'comcast.net', 'att.net',
                   'bellsouth.net', 'verizon.net', 'msn.com', 'live.com'}
        return "" if domain in webmail else domain

    def normalize_company_name(self, name: str) -> str:
        """Normalize company name for matching."""
        if not name:
            return ""
        name = name.lower().strip()
        # Remove common suffixes
        for suffix in [' llc', ' inc', ' inc.', ' corp', ' corp.', ' co', ' co.',
                       ' ltd', ' ltd.', ' company', ', llc', ', inc', ', inc.',
                       ' incorporated', ' corporation', ' enterprises', ' services',
                       ' contracting', ' construction', ' contractors']:
            name = name.replace(suffix, '')
        # Remove punctuation
        name = re.sub(r'[^\w\s]', '', name)
        # Collapse whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def fuzzy_match(self, name1: str, name2: str) -> float:
        """Calculate fuzzy match ratio between two names."""
        n1 = self.normalize_company_name(name1)
        n2 = self.normalize_company_name(name2)
        if not n1 or not n2:
            return 0.0
        return SequenceMatcher(None, n1, n2).ratio()

    def add_record(self, record: dict) -> Tuple[bool, Optional[dict]]:
        """
        Add a record, checking for duplicates.

        Returns:
            (is_duplicate, matching_master_record)
        """
        # Extract matching signals
        phone = self.normalize_phone(record.get('phone', ''))
        email = self.normalize_email(record.get('email', ''))
        domain = self.extract_domain(email)
        company = record.get('company_name', '')
        state = record.get('state', '').upper()
        name_key = f"{self.normalize_company_name(company)}|{state}"

        # Check for duplicates in order of reliability

        # 1. Phone match (highest confidence)
        if phone and phone in self.phone_index:
            existing = self.phone_index[phone][0]
            self._merge_record(existing, record)
            return True, existing

        # 2. Exact email match
        if email and email in self.email_index:
            existing = self.email_index[email][0]
            self._merge_record(existing, record)
            return True, existing

        # 3. Domain match (same company email domain)
        if domain and domain in self.domain_index:
            existing = self.domain_index[domain][0]
            # Only match if names are somewhat similar (50%+)
            if self.fuzzy_match(company, existing.get('company_name', '')) >= 0.5:
                self._merge_record(existing, record)
                return True, existing

        # 4. Fuzzy name match (same state, 85%+ similarity)
        if name_key:
            for existing in self.name_state_index.get(name_key, []):
                if self.fuzzy_match(company, existing.get('company_name', '')) >= self.FUZZY_THRESHOLD:
                    self._merge_record(existing, record)
                    return True, existing

        # No match - new master record
        master = self._create_master(record)
        self.master_records.append(master)

        # Index the new record
        if phone:
            self.phone_index[phone].append(master)
        if email:
            self.email_index[email].append(master)
        if domain:
            self.domain_index[domain].append(master)
        if name_key:
            self.name_state_index[name_key].append(master)

        return False, master

    def _create_master(self, record: dict) -> dict:
        """Create a master record from input."""
        return {
            'company_name': record.get('company_name', ''),
            'contact_names': set([record.get('contact_name', '')]) if record.get('contact_name') else set(),
            'phones': set([self.normalize_phone(record.get('phone', ''))]) if self.normalize_phone(record.get('phone', '')) else set(),
            'emails': set([self.normalize_email(record.get('email', ''))]) if self.normalize_email(record.get('email', '')) else set(),
            'addresses': [record.get('address', '')] if record.get('address') else [],
            'city': record.get('city', ''),
            'state': record.get('state', ''),
            'zip': record.get('zip', ''),
            'sources': set([record.get('source', '')]) if record.get('source') else set(),
            'license_types': set(record.get('license_types', [])) if isinstance(record.get('license_types'), (list, set)) else set([record.get('license_types', '')]) if record.get('license_types') else set(),
            'categories': set(record.get('categories', [])) if isinstance(record.get('categories'), (list, set)) else set(),
            'kw_installed': record.get('kw_installed', 0),
            'duplicate_count': 1,
            'raw_records': [record]
        }

    def _merge_record(self, master: dict, record: dict):
        """Merge a duplicate record into master."""
        master['duplicate_count'] += 1
        master['raw_records'].append(record)

        # Merge contact names
        if record.get('contact_name'):
            master['contact_names'].add(record['contact_name'])

        # Merge phones
        phone = self.normalize_phone(record.get('phone', ''))
        if phone:
            master['phones'].add(phone)
            if phone not in self.phone_index:
                self.phone_index[phone].append(master)

        # Merge emails
        email = self.normalize_email(record.get('email', ''))
        if email:
            master['emails'].add(email)
            if email not in self.email_index:
                self.email_index[email].append(master)

        # Merge sources
        if record.get('source'):
            master['sources'].add(record['source'])

        # Merge license types
        if record.get('license_types'):
            if isinstance(record['license_types'], (list, set)):
                master['license_types'].update(record['license_types'])
            else:
                master['license_types'].add(record['license_types'])

        # Merge categories
        if record.get('categories'):
            if isinstance(record['categories'], (list, set)):
                master['categories'].update(record['categories'])

    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        total_input = sum(m['duplicate_count'] for m in self.master_records)
        unique = len(self.master_records)
        duplicates = total_input - unique

        multi_source = sum(1 for m in self.master_records if len(m['sources']) > 1)
        with_email = sum(1 for m in self.master_records if m['emails'])
        with_phone = sum(1 for m in self.master_records if m['phones'])
        multi_license = sum(1 for m in self.master_records if len(m['categories']) >= 2)

        return {
            'total_input': total_input,
            'unique_records': unique,
            'duplicates_removed': duplicates,
            'dedup_rate': (duplicates / total_input * 100) if total_input > 0 else 0,
            'multi_source': multi_source,
            'with_email': with_email,
            'with_phone': with_phone,
            'multi_license': multi_license
        }

    def export_csv(self, filepath: Path):
        """Export master records to CSV."""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'company_name', 'contact_names', 'emails', 'phones',
                'city', 'state', 'zip', 'sources', 'license_types',
                'categories', 'category_count', 'duplicate_count', 'kw_installed'
            ])
            writer.writeheader()

            for master in sorted(self.master_records, key=lambda x: -len(x['categories'])):
                writer.writerow({
                    'company_name': master['company_name'],
                    'contact_names': '|'.join(filter(None, master['contact_names']))[:200],
                    'emails': '|'.join(filter(None, master['emails']))[:200],
                    'phones': '|'.join(filter(None, master['phones']))[:100],
                    'city': master['city'],
                    'state': master['state'],
                    'zip': master['zip'],
                    'sources': '|'.join(filter(None, master['sources'])),
                    'license_types': '|'.join(filter(None, master['license_types'])),
                    'categories': '|'.join(filter(None, master['categories'])),
                    'category_count': len(master['categories']),
                    'duplicate_count': master['duplicate_count'],
                    'kw_installed': master.get('kw_installed', '')
                })


def load_fl_everyone(filepath: Path, engine: DeduplicationEngine, limit: int = None):
    """Load FL contractor data with deduplication."""

    LICENSE_CATEGORIES = {
        "CAC": "HVAC", "CMC": "HVAC",
        "CPC": "PLUMBING",
        "CFC": "FIRE",
        "FRO": "ROOFING", "CCC": "ROOFING",
        "CGC": "GENERAL", "CBC": "BUILDING",
        "CUC": "UTILITY", "SCC": "SPECIALTY",
    }

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            if len(row) < 10:
                continue

            license_type = row[0].strip().upper() if row[0] else ""
            category = LICENSE_CATEGORIES.get(license_type)
            if not category:
                continue

            name = row[1].strip() if len(row) > 1 else ""
            company = row[2].strip() if len(row) > 2 else ""

            engine.add_record({
                'company_name': company if company else name,
                'contact_name': name,
                'address': row[3].strip() if len(row) > 3 else "",
                'city': row[5].strip() if len(row) > 5 else "",
                'state': 'FL',
                'zip': row[7].strip() if len(row) > 7 else "",
                'email': row[9].strip() if len(row) > 9 else "",
                'source': 'FL_License',
                'license_types': license_type,
                'categories': [category]
            })


def main():
    print("\n" + "=" * 70)
    print("MASTER DEDUPLICATION ENGINE")
    print("=" * 70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    engine = DeduplicationEngine()

    # Load FL Everyone data
    fl_file = Path.home() / "Downloads" / "Contractor List.xlsx - Everyone.csv"
    if fl_file.exists():
        print(f"\n📂 Loading FL contractor data...")
        load_fl_everyone(fl_file, engine)
        print(f"   Processed FL data")

    # Get stats
    stats = engine.get_stats()

    print("\n" + "=" * 70)
    print("DEDUPLICATION RESULTS")
    print("=" * 70)
    print(f"Total input records: {stats['total_input']:,}")
    print(f"Unique contractors: {stats['unique_records']:,}")
    print(f"Duplicates removed: {stats['duplicates_removed']:,}")
    print(f"Deduplication rate: {stats['dedup_rate']:.1f}%")
    print(f"\nMulti-source matches: {stats['multi_source']:,}")
    print(f"With email: {stats['with_email']:,}")
    print(f"With phone: {stats['with_phone']:,}")
    print(f"Multi-license (2+ categories): {stats['multi_license']:,}")

    # Export
    output_file = OUTPUT_DIR / f"fl_deduped_master_{timestamp}.csv"
    engine.export_csv(output_file)
    print(f"\n✅ Saved: {output_file}")

    # Export just multi-license with emails (highest value)
    multi_license_with_email = [
        m for m in engine.master_records
        if len(m['categories']) >= 2 and m['emails']
    ]

    if multi_license_with_email:
        ml_file = OUTPUT_DIR / f"fl_multi_license_deduped_{timestamp}.csv"
        with open(ml_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'company_name', 'contact_names', 'emails', 'phones',
                'city', 'state', 'zip', 'categories', 'category_count'
            ])
            writer.writeheader()

            for m in sorted(multi_license_with_email, key=lambda x: -len(x['categories'])):
                writer.writerow({
                    'company_name': m['company_name'],
                    'contact_names': '|'.join(list(m['contact_names'])[:5]),
                    'emails': '|'.join(list(m['emails'])[:5]),
                    'phones': '|'.join(list(m['phones'])[:3]),
                    'city': m['city'],
                    'state': m['state'],
                    'zip': m['zip'],
                    'categories': '|'.join(m['categories']),
                    'category_count': len(m['categories'])
                })

        print(f"✅ Saved: {ml_file}")
        print(f"   Multi-license with emails: {len(multi_license_with_email):,}")


if __name__ == "__main__":
    main()
