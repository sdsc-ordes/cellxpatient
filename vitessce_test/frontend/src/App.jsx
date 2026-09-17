import { Vitessce } from "vitessce"
import { useEffect, useState } from "react"

export default function App() {
  const [config, setConfig] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch("/api/config")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        return response.json()
      })
      .then(setConfig)
      .catch(setError)
  }, [])

  if (error) {
    return <div>Error loading config: {error.message}</div>
  }

  if (!config) {
    return <div>Loading configuration...</div>
  }

  return <Vitessce config={config} height={1800} theme="dark" />
}
