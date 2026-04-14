import { ConfigPanel } from '../components/ConfigPanel'

export function ConfigPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-0">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Configurazione</h1>
        <p className="text-sm text-gray-500">
          Gestisci le impostazioni del sistema di sollecito automatico
        </p>
      </div>

      <ConfigPanel />
    </div>
  )
}
