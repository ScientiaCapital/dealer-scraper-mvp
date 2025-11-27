'use client'

interface PipelineHealth {
  total_contractors: number
  with_email: number
  with_phone: number
  email_rate: number
  phone_rate: number
  multi_license_count: number
  unicorn_count: number
  multi_oem_count: number
  scrapers_working: number
  scrapers_broken: number
  scrapers_untested: number
  scrapers_total: number
  generated_at: string
}

interface ScraperHealth {
  scraper_name: string
  scraper_type: string
  status: string
  fix_difficulty: string | null
  total_records_lifetime: number | null
  last_successful_run: string | null
  source_url: string | null
  notes: string | null
}

interface DataInventory {
  source_name: string
  source_type: string
  record_count: number
  with_email_count: number
  with_phone_count: number
  quality_score: number
  last_updated: string
  notes: string | null
}

interface StateCoverage {
  state: string
  contractor_count: number
  with_email: number
  with_phone: number
}

interface OEMCoverage {
  oem_name: string
  contractor_count: number
}

interface ROIMetrics {
  total_investment_usd: number
  infrastructure_cost: number
  enrichment_cost: number
  outreach_cost: number
  labor_cost: number
  cost_per_lead_usd: number
  pipeline_value_usd: number
  closed_won_count: number
  closed_won_value_usd: number
  roi_percentage: number | null
  conversion_rates: Array<{
    conversion: string
    numerator: number
    denominator: number
    conversion_rate_pct: number | null
  }>
  monthly_costs: Array<{
    month: string
    category: string
    total_cost_usd: number
  }>
}

interface DashboardData {
  pipeline_health: PipelineHealth
  scraper_health: ScraperHealth[]
  data_inventory: DataInventory[]
  state_coverage: StateCoverage[]
  oem_coverage: OEMCoverage[]
  roi_metrics?: ROIMetrics
}

function formatNumber(n: number): string {
  return n.toLocaleString()
}

// Format source names for professional display
function formatSourceName(name: string): string {
  // OEM brand names
  const oemMap: Record<string, string> = {
    'briggs_&_stratton': 'Briggs & Stratton',
    'solaredge': 'SolarEdge',
    'goodwe': 'GoodWe',
    'solark': 'Sol-Ark',
    'generac': 'Generac',
    'tesla': 'Tesla',
    'enphase': 'Enphase',
    'carrier': 'Carrier',
    'trane': 'Trane',
    'mitsubishi': 'Mitsubishi',
    'rheem': 'Rheem',
    'york': 'York',
    'cummins': 'Cummins',
    'kohler': 'Kohler',
    'sma': 'SMA Solar',
    'fronius': 'Fronius',
    'delta': 'Delta Electronics',
    'abb': 'ABB',
    'tigo': 'Tigo',
    'simpliphi': 'SimpliPhi',
    'sungrow': 'Sungrow',
    'growatt': 'Growatt',
  }

  // State license names - keep it simple
  const stateMap: Record<string, string> = {
    'ca_license': 'California',
    'fl_license': 'Florida',
    'tx_license': 'Texas',
    'ny_license': 'New York',
    'nj_license': 'New Jersey',
    'pa_license': 'Pennsylvania',
    'ma_license': 'Massachusetts',
    'ga_license': 'Georgia',
    'nc_license': 'North Carolina',
    'oh_license': 'Ohio',
    'al_license': 'Alabama',
    'la_license': 'Louisiana',
    'tn_license': 'Tennessee',
    'co_license': 'Colorado',
    'az_license': 'Arizona',
    'nv_license': 'Nevada',
    'wa_license': 'Washington',
    'or_license': 'Oregon',
    'il_license': 'Illinois',
    'mi_license': 'Michigan',
    'va_license': 'Virginia',
    'md_license': 'Maryland',
    'ct_license': 'Connecticut',
    'sc_license': 'South Carolina',
    'nyc_dob': 'NYC',
  }

  // Third party sources
  const thirdPartyMap: Record<string, string> = {
    'spw_master': 'Solar Power World',
    'spw': 'Solar Power World',
    'amicus': 'Amicus Solar',
  }

  // Source types
  const typeMap: Record<string, string> = {
    'state_license': 'State License DB',
    'oem_dealer': 'OEM Dealer Network',
    'both': 'Multi-Source',
  }

  const lowerName = name.toLowerCase()

  // Check each map
  if (oemMap[lowerName]) return oemMap[lowerName]
  if (stateMap[lowerName]) return stateMap[lowerName]
  if (thirdPartyMap[lowerName]) return thirdPartyMap[lowerName]
  if (typeMap[lowerName]) return typeMap[lowerName]

  // Skip invalid entries
  if (name.startsWith('-') || /^\d+_/.test(name)) return ''

  // Default: Title case with underscores replaced
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// Format state for display (filter empty/invalid)
function formatState(state: string | null): string {
  if (!state || state.trim() === '' || state === 'null') return ''
  return state.toUpperCase()
}

function MetricCard({ title, value, subtitle }: { title: string; value: string | number; subtitle?: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="text-sm text-gray-500 uppercase tracking-wide">{title}</div>
      <div className="text-3xl font-bold text-gray-900 mt-1">
        {typeof value === 'number' ? formatNumber(value) : value}
      </div>
      {subtitle && <div className="text-sm text-gray-400 mt-1">{subtitle}</div>}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    WORKING: 'bg-green-100 text-green-800 border-green-200',
    BROKEN: 'bg-red-100 text-red-800 border-red-200',
    UNTESTED: 'bg-gray-100 text-gray-600 border-gray-200',
  }
  const icons: Record<string, string> = {
    WORKING: '✓',
    BROKEN: '✗',
    UNTESTED: '?',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold border ${colors[status] || colors.UNTESTED}`}>
      <span className="font-bold">{icons[status]}</span>
      {status}
    </span>
  )
}

function formatCurrency(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

function ROISection({ roi, totalLeads }: { roi: ROIMetrics; totalLeads: number }) {
  const leadsPerDollar = roi.total_investment_usd > 0 ? totalLeads / roi.total_investment_usd : 0
  const efficiencyMultiple = roi.cost_per_lead_usd > 0 ? Math.round(5 / roi.cost_per_lead_usd) : 0

  return (
    <section className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">💰 ROI Dashboard</h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Investment</div>
          <div className="text-2xl font-bold text-gray-900">{formatCurrency(roi.total_investment_usd)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Cost per Lead</div>
          <div className="text-2xl font-bold text-green-600">{formatCurrency(roi.cost_per_lead_usd)}</div>
          <div className="text-xs text-gray-400">Industry avg: $5-50</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Leads per $1</div>
          <div className="text-2xl font-bold text-blue-600">{formatNumber(Math.round(leadsPerDollar))}</div>
          <div className="text-xs text-gray-400">Industry avg: 0.02-0.2</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Efficiency vs Market</div>
          <div className="text-2xl font-bold text-purple-600">
            {efficiencyMultiple > 0 ? `${formatNumber(efficiencyMultiple)}x` : '∞'}
          </div>
          <div className="text-xs text-gray-400">Better than avg</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Investment Breakdown */}
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="font-medium text-gray-700 mb-3">Investment Breakdown</h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Infrastructure</span>
              <span className="font-medium">{formatCurrency(roi.infrastructure_cost)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Labor</span>
              <span className="font-medium">{formatCurrency(roi.labor_cost)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Enrichment</span>
              <span className="font-medium">{formatCurrency(roi.enrichment_cost)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Outreach</span>
              <span className="font-medium">{formatCurrency(roi.outreach_cost)}</span>
            </div>
            <div className="border-t pt-2 flex justify-between font-bold">
              <span>Total</span>
              <span>{formatCurrency(roi.total_investment_usd)}</span>
            </div>
          </div>
        </div>

        {/* Pipeline Status */}
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="font-medium text-gray-700 mb-3">Pipeline Status</h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Leads</span>
              <span className="font-medium">{formatNumber(totalLeads)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Open Pipeline</span>
              <span className="font-medium">{formatCurrency(roi.pipeline_value_usd)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Closed Won</span>
              <span className="font-medium text-green-600">{roi.closed_won_count} ({formatCurrency(roi.closed_won_value_usd)})</span>
            </div>
            <div className="border-t pt-2 flex justify-between">
              <span className="font-bold">ROI</span>
              <span className={`font-bold ${roi.roi_percentage && roi.roi_percentage > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                {roi.roi_percentage !== null ? `${roi.roi_percentage.toFixed(1)}%` : 'Tracking...'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {roi.closed_won_count === 0 && (
        <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            🎯 <strong>Next milestone:</strong> First closed deal will unlock ROI tracking.
            With {formatNumber(totalLeads)} leads at {formatCurrency(roi.cost_per_lead_usd)} each,
            closing a single $5K deal = {roi.total_investment_usd > 0 ? Math.round((5000 - roi.total_investment_usd) / roi.total_investment_usd * 100) : 0}% ROI.
          </p>
        </div>
      )}
    </section>
  )
}

export default function Dashboard({ data }: { data: DashboardData }) {
  const { pipeline_health: health, scraper_health: scrapers, data_inventory: inventory, state_coverage: states, oem_coverage: oems, roi_metrics: roi } = data

  const generatedDate = new Date(health.generated_at).toLocaleString()

  // Group scrapers by type
  const scrapersByType = scrapers.reduce((acc, s) => {
    if (!acc[s.scraper_type]) acc[s.scraper_type] = []
    acc[s.scraper_type].push(s)
    return acc
  }, {} as Record<string, ScraperHealth[]>)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Pipeline Overview</h2>
          <p className="text-gray-500">Last updated: {generatedDate}</p>
        </div>
      </div>

      {/* Executive Summary */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Executive Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <MetricCard title="Total Contractors" value={health.total_contractors} />
          <MetricCard title="With Email" value={health.with_email} subtitle={`${health.email_rate}%`} />
          <MetricCard title="With Phone" value={health.with_phone} subtitle={`${health.phone_rate}%`} />
          <MetricCard title="Multi-License" value={health.multi_license_count} subtitle="2+ trades" />
          <MetricCard title="Unicorns" value={health.unicorn_count} subtitle="3+ trades" />
          <MetricCard title="Multi-OEM" value={health.multi_oem_count} subtitle="2+ brands" />
        </div>
      </section>

      {/* ROI Dashboard */}
      {roi && <ROISection roi={roi} totalLeads={health.total_contractors} />}

      {/* Scraper Health */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🔧 Scraper Health</h3>
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{health.scrapers_working}</div>
              <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Working</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-red-600">{health.scrapers_broken}</div>
              <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Broken</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-400">{health.scrapers_untested}</div>
              <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Untested</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900">{health.scrapers_total}</div>
              <div className="text-sm text-gray-500 uppercase tracking-wide mt-1">Total</div>
            </div>
          </div>
        </div>

        {Object.entries(scrapersByType).map(([type, items]) => (
          <div key={type} className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-base font-semibold text-gray-900">{type}</h4>
              <span className="text-sm text-gray-500">{items.length} scrapers</span>
            </div>
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Records</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Run</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-96">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {items.map((s) => (
                    <tr key={s.scraper_name} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">{s.scraper_name}</td>
                      <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={s.status} /></td>
                      <td className="px-6 py-4 text-gray-600 whitespace-nowrap">
                        {s.total_records_lifetime ? formatNumber(s.total_records_lifetime) : '-'}
                      </td>
                      <td className="px-6 py-4 text-gray-600 whitespace-nowrap text-sm">
                        {s.last_successful_run ? s.last_successful_run.slice(0, 10) : 'Never'}
                      </td>
                      <td className="px-6 py-4 text-gray-600 text-sm">
                        {s.notes || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </section>

      {/* Data Inventory */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📦 Data Inventory (Top 15)</h3>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Records</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Phone</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quality</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {inventory
                .filter(item => formatSourceName(item.source_name) !== '')
                .slice(0, 15)
                .map((item) => (
                <tr key={`${item.source_name}-${item.source_type}`} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">{formatSourceName(item.source_name)}</td>
                  <td className="px-6 py-4 text-gray-600 whitespace-nowrap">{formatSourceName(item.source_type)}</td>
                  <td className="px-6 py-4 text-gray-900 font-semibold whitespace-nowrap">{formatNumber(item.record_count)}</td>
                  <td className="px-6 py-4 text-gray-600 whitespace-nowrap">
                    {item.with_email_count ? formatNumber(item.with_email_count) : '-'}
                  </td>
                  <td className="px-6 py-4 text-gray-600 whitespace-nowrap">
                    {item.with_phone_count ? formatNumber(item.with_phone_count) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      item.quality_score >= 70 ? 'bg-green-100 text-green-800' :
                      item.quality_score >= 40 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {item.quality_score}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* State & OEM Coverage */}
      <div className="grid md:grid-cols-2 gap-8">
        <section>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🗺️ Top States</h3>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="space-y-2">
              {states
                .filter(s => s.state && s.state.trim() !== '')
                .slice(0, 10)
                .map((s) => (
                <div key={s.state} className="flex justify-between items-center">
                  <span className="font-medium">{s.state}</span>
                  <span className="text-gray-600">{formatNumber(s.contractor_count)} contractors</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🏭 OEM Certifications</h3>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="space-y-2">
              {oems.map((o) => (
                <div key={o.oem_name} className="flex justify-between items-center">
                  <span className="font-medium">{formatSourceName(o.oem_name)}</span>
                  <span className="text-gray-600">{formatNumber(o.contractor_count)} contractors</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
