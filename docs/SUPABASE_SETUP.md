# Supabase Setup for Dealer Scraper MVP

## Step 1: Create New Supabase Project

1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Choose organization: `scientia-capital` (or create new)
4. Project name: `dealer-scraper-mvp`
5. Database password: Generate strong password, **SAVE IT**
6. Region: `us-east-1` (closest to you)
7. Click "Create new project"

Wait 2-3 minutes for project to provision.

## Step 2: Get Your Credentials

From your Supabase dashboard:

1. Go to **Settings** → **API**
2. Copy these values:

```
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  (public, safe to expose)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  (SECRET - never expose!)
```

## Step 3: Add to .env

Add these to your `.env` file:

```bash
# Supabase (dealer-scraper-mvp project)
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here
```

## Step 4: Run the Schema

1. Go to **SQL Editor** in Supabase dashboard
2. Click "New query"
3. Copy contents of `database/supabase_schema.sql`
4. Click "Run"

This creates:
- `companies` - Master contractor table (THE ANCHOR)
- `offices` - Multi-site locations
- `oem_certifications` - OEM dealer relationships
- `state_licenses` - State license records
- `import_batches` - Audit: every import logged
- `change_history` - Audit: every change logged (CDC)
- `dedup_log` - Audit: every merge decision logged
- `crm_sync_status` - Close CRM sync tracking
- `crm_sync_log` - Close CRM sync history

## Step 5: Verify Setup

Run this query in SQL Editor to verify:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected output:
- change_history
- companies
- crm_sync_log
- crm_sync_status
- dedup_log
- import_batches
- offices
- oem_certifications
- state_licenses

## Database Schema Overview

```
┌─────────────────┐
│    companies    │  ← THE ANCHOR (company_name is primary)
│  (master table) │
├─────────────────┤
│ id              │
│ company_name    │  ← Required, never null
│ normalized_name │  ← For dedup matching
│ phone           │
│ email           │
│ website         │
│ city, state     │
│ icp_tier        │  ← PLATINUM/GOLD/SILVER/BRONZE
│ created_at      │
│ updated_at      │
│ source_file     │  ← Audit: where did this come from?
│ import_batch_id │  ← Audit: which import added this?
└────────┬────────┘
         │
         │ 1:N relationships
         │
    ┌────┴────┐────────────┐─────────────┐
    ▼         ▼            ▼             ▼
┌────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐
│offices │ │oem_certs │ │state_lic  │ │crm_sync  │
└────────┘ └──────────┘ └───────────┘ └──────────┘
```

## Audit Trail Flow

Every action is logged:

```
1. Import CSV file
   └─→ import_batches (records: 500 new, 50 dupes)
       └─→ companies (500 INSERTs)
           └─→ change_history (500 INSERT records)

2. Dedup merge
   └─→ dedup_log (kept: X, merged: Y, match_type: phone)
       └─→ change_history (UPDATE with merged data)

3. CRM sync
   └─→ crm_sync_log (create_lead / update_lead / skip_duplicate)
       └─→ crm_sync_status (synced / needs_update / skipped)
```

## Views for Common Queries

### Clean leads ready for sales-agent:
```sql
SELECT * FROM clean_leads ORDER BY icp_score DESC;
```

### Multi-OEM contractors (high value):
```sql
SELECT * FROM multi_oem_contractors ORDER BY oem_count DESC;
```

### Pending CRM sync:
```sql
SELECT * FROM pending_crm_sync;
```

### Companies needing enrichment push:
```sql
SELECT * FROM needs_crm_enrichment;
```

## Close CRM Sync Workflow

The `crm_sync_status` table tracks Close CRM state:

| sync_status | Meaning | Action |
|------------|---------|--------|
| `pending` | Not in Close yet | Create new lead |
| `synced` | In Close, up to date | Skip |
| `needs_update` | We have new data | Update existing lead |
| `skipped` | Deliberately skipped | Skip (duplicate/bad) |
| `failed` | API error | Retry |

ATL/BTL tiers:
- **ATL (Above the Line)**: High-value, direct sales outreach
- **BTL (Below the Line)**: Nurture campaigns, marketing automation
