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
  states_covered?: number
  with_phone?: number
  with_email?: number
}

interface ToolCost {
  tool_name: string
  category: string
  monthly_cost_usd: number
  description: string
  percentage: number
}

interface ValueMetrics {
  pipeline_value_usd: number
  closed_won_count: number
  closed_won_value_usd: number
  roi_percentage: number | null
  break_even_deals_needed: number
}

interface ROIMetrics {
  total_investment_usd: number
  monthly_burn_rate_usd: number
  project_start_date: string
  cost_per_lead_usd: number
  cost_per_enriched_lead_usd: number
  total_contractors: number
  with_contact_info: number
  contact_rate_pct: number
  tool_costs: ToolCost[]
  value_metrics: ValueMetrics
  conversion_rates: Array<{
    conversion: string
    numerator: number
    denominator: number
    conversion_rate_pct: number | null
  }>
  funnel_stages: Array<unknown>
}

interface RecentSuccess {
  scraper_name: string
  date: string
  contractors_extracted: number
  email_count: number
  phone_count: number
  email_rate_pct: number
  phone_rate_pct: number
  gold_tier_count: number
  silver_tier_count: number
  highlight: string
}

interface DashboardData {
  pipeline_health: PipelineHealth
  scraper_health: ScraperHealth[]
  data_inventory: DataInventory[]
  state_coverage: StateCoverage[]
  oem_coverage: OEMCoverage[]
  roi_metrics?: ROIMetrics
  recent_successes?: RecentSuccess[]
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

function ROISection({ roi, pipelineHealth, recentSuccesses }: { roi: ROIMetrics; pipelineHealth: PipelineHealth; recentSuccesses?: RecentSuccess[] }) {
  const leadsPerDollar = roi.monthly_burn_rate_usd > 0 ? roi.total_contractors / roi.monthly_burn_rate_usd : 0
  const efficiencyMultiple = roi.cost_per_lead_usd > 0 ? Math.round(5 / roi.cost_per_lead_usd) : 0

  // Category colors for tool costs
  const categoryColors: Record<string, string> = {
    'AI/LLM': 'bg-purple-500',
    'Infrastructure': 'bg-blue-500',
    'Enrichment': 'bg-green-500',
  }

  return (
    <section className="space-y-6">
      {/* Monthly Burn Rate - Hero Section */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg p-6 text-white">
        <h3 className="text-lg font-semibold mb-4">Monthly Burn Rate</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-3xl font-bold">{formatCurrency(roi.monthly_burn_rate_usd)}</div>
            <div className="text-sm text-slate-400">per month</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-400">{formatCurrency(roi.cost_per_lead_usd)}</div>
            <div className="text-sm text-slate-400">per lead (vs $5-50 industry)</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-blue-400">{formatNumber(Math.round(leadsPerDollar))}</div>
            <div className="text-sm text-slate-400">leads per $1</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-400">{efficiencyMultiple > 0 ? `${formatNumber(efficiencyMultiple)}x` : '∞'}</div>
            <div className="text-sm text-slate-400">better than market</div>
          </div>
        </div>
      </div>

      {/* Tool Costs Breakdown */}
      <div className="bg-white rounded-lg shadow p-6">
        <h4 className="font-semibold text-gray-900 mb-4">Tool Costs by Service</h4>
        <div className="space-y-4">
          {roi.tool_costs.map((tool) => (
            <div key={tool.tool_name} className="space-y-2">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className={`inline-block w-3 h-3 rounded-full ${categoryColors[tool.category] || 'bg-gray-500'}`}></span>
                  <div>
                    <span className="font-medium text-gray-900">{tool.tool_name}</span>
                    <span className="ml-2 text-xs text-gray-500">{tool.category}</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="font-bold text-gray-900">{formatCurrency(tool.monthly_cost_usd)}</span>
                  <span className="text-gray-500 text-sm ml-2">({tool.percentage.toFixed(0)}%)</span>
                </div>
              </div>
              <div className="ml-6">
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${categoryColors[tool.category] || 'bg-gray-500'}`}
                    style={{ width: `${tool.percentage}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-1">{tool.description}</p>
              </div>
            </div>
          ))}
          <div className="border-t pt-3 flex justify-between items-center">
            <span className="font-bold text-gray-900">Total Monthly</span>
            <span className="font-bold text-xl text-gray-900">{formatCurrency(roi.monthly_burn_rate_usd)}</span>
          </div>
        </div>
      </div>

      {/* Pipeline Health Snapshot */}
      <div className="bg-white rounded-lg shadow p-6">
        <h4 className="font-semibold text-gray-900 mb-4">Pipeline Health Snapshot</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-900">{formatNumber(pipelineHealth.total_contractors)}</div>
            <div className="text-sm text-gray-500">Total Contractors</div>
          </div>
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{formatNumber(pipelineHealth.with_email)}</div>
            <div className="text-sm text-gray-500">With Email ({pipelineHealth.email_rate}%)</div>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">{formatNumber(pipelineHealth.with_phone)}</div>
            <div className="text-sm text-gray-500">With Phone ({pipelineHealth.phone_rate}%)</div>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-600">{formatNumber(pipelineHealth.multi_license_count)}</div>
            <div className="text-sm text-gray-500">Multi-License (2+ trades)</div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-4">
          <div className="text-center p-3 bg-amber-50 rounded-lg">
            <div className="text-xl font-bold text-amber-600">{formatNumber(pipelineHealth.unicorn_count)}</div>
            <div className="text-xs text-gray-500">Unicorns (3+ trades)</div>
          </div>
          <div className="text-center p-3 bg-indigo-50 rounded-lg">
            <div className="text-xl font-bold text-indigo-600">{formatNumber(pipelineHealth.multi_oem_count)}</div>
            <div className="text-xs text-gray-500">Multi-OEM (2+ brands)</div>
          </div>
          <div className="text-center p-3 bg-teal-50 rounded-lg">
            <div className="text-xl font-bold text-teal-600">{pipelineHealth.scrapers_working}/{pipelineHealth.scrapers_total}</div>
            <div className="text-xs text-gray-500">Scrapers Working</div>
          </div>
        </div>
      </div>

      {/* Recent Wins */}
      {recentSuccesses && recentSuccesses.length > 0 && (
        <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-6 border border-green-200">
          <h4 className="font-semibold text-gray-900 mb-4">Recent Wins</h4>
          <div className="space-y-4">
            {recentSuccesses.slice(0, 3).map((success, idx) => (
              <div key={success.scraper_name} className={`bg-white rounded-lg p-4 shadow-sm ${idx === 0 ? 'ring-2 ring-green-400' : ''}`}>
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      {idx === 0 && <span className="text-green-500 text-lg">🎉</span>}
                      <span className="font-bold text-gray-900">{success.scraper_name}</span>
                      <span className="text-xs text-gray-400">{success.date}</span>
                    </div>
                    <p className="text-sm text-green-700 mt-1">{success.highlight}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-gray-900">{formatNumber(success.contractors_extracted)}</div>
                    <div className="text-xs text-gray-500">contractors</div>
                  </div>
                </div>
                <div className="mt-3 flex gap-4 text-sm">
                  {success.email_count > 0 && (
                    <span className="text-green-600">
                      ✉️ {formatNumber(success.email_count)} emails ({success.email_rate_pct}%)
                    </span>
                  )}
                  {success.phone_count > 0 && (
                    <span className="text-blue-600">
                      📞 {formatNumber(success.phone_count)} phones ({success.phone_rate_pct}%)
                    </span>
                  )}
                  {(success.gold_tier_count > 0 || success.silver_tier_count > 0) && (
                    <span className="text-amber-600">
                      ⭐ {success.gold_tier_count} Gold, {success.silver_tier_count} Silver
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next Milestone */}
      {roi.value_metrics.closed_won_count === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            🎯 <strong>Next milestone:</strong> First closed deal unlocks ROI tracking.
            At {formatCurrency(roi.cost_per_lead_usd)} per lead, closing a single $20K deal = massive ROI.
            Break-even: {roi.value_metrics.break_even_deals_needed} deal(s).
          </p>
        </div>
      )}
    </section>
  )
}

export default function Dashboard({ data }: { data: DashboardData }) {
  const { pipeline_health: health, scraper_health: scrapers, data_inventory: inventory, state_coverage: states, oem_coverage: oems, roi_metrics: roi, recent_successes: successes } = data

  const generatedDate = new Date(health.generated_at).toLocaleString()

  // Group scrapers by type, then sort: WORKING first, then BROKEN, then UNTESTED
  const statusOrder: Record<string, number> = { 'WORKING': 0, 'BROKEN': 1, 'UNTESTED': 2 }
  const scrapersByType = scrapers.reduce((acc, s) => {
    if (!acc[s.scraper_type]) acc[s.scraper_type] = []
    acc[s.scraper_type].push(s)
    return acc
  }, {} as Record<string, ScraperHealth[]>)

  // Sort each group by status (WORKING first)
  Object.keys(scrapersByType).forEach(type => {
    scrapersByType[type].sort((a, b) =>
      (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3)
    )
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center border-b pb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Coperniq Partner Prospecting</h2>
          <p className="text-gray-500">Executive Dashboard • Last updated: {generatedDate}</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-gray-900">{formatNumber(health.total_contractors)}</div>
          <div className="text-sm text-gray-500">Total Contractors</div>
        </div>
      </div>

      {/* ROI Dashboard - Primary Section for CEO/CTO */}
      {roi && <ROISection roi={roi} pipelineHealth={health} recentSuccesses={successes} />}

      {/* Technical Details - Collapsible for Internal Use */}
      <details className="group">
        <summary className="cursor-pointer list-none">
          <div className="flex items-center justify-between bg-slate-100 rounded-lg p-4 hover:bg-slate-200 transition-colors">
            <div className="flex items-center gap-2">
              <span className="text-lg">🔧</span>
              <span className="font-semibold text-gray-700">Technical Details</span>
              <span className="text-sm text-gray-500">(Scraper Health, Data Inventory)</span>
            </div>
            <span className="text-gray-400 group-open:rotate-180 transition-transform">▼</span>
          </div>
        </summary>
        <div className="mt-4 space-y-8">
          {/* Scraper Health */}
          <section>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Scraper Health</h3>
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
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Inventory (Top 15)</h3>
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
                    .sort((a, b) => b.quality_score - a.quality_score)
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
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top States</h3>
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
              <h3 className="text-lg font-semibold text-gray-900 mb-4">OEM Certifications</h3>
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">OEM</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Contractors</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">States</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Phone</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {oems.map((o) => (
                      <tr key={o.oem_name} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-medium text-gray-900">{formatSourceName(o.oem_name)}</td>
                        <td className="px-4 py-2 text-right text-gray-900 font-semibold">{formatNumber(o.contractor_count)}</td>
                        <td className="px-4 py-2 text-right text-gray-600">{o.states_covered || '-'}</td>
                        <td className="px-4 py-2 text-right">
                          {o.with_phone && o.contractor_count > 0 ? (
                            <span className={`text-sm ${Math.round(o.with_phone / o.contractor_count * 100) >= 90 ? 'text-green-600' : 'text-gray-600'}`}>
                              {Math.round(o.with_phone / o.contractor_count * 100)}%
                            </span>
                          ) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </div>
      </details>
    </div>
  )
}
