import Dashboard from '@/components/Dashboard'
import dashboardData from '@/public/data/dashboard_data.json'

export default function Home() {
  return <Dashboard data={dashboardData} />
}
