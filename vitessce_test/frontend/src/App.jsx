import { Vitessce } from "vitessce"
import { useEffect, useRef, useState } from "react"
import "./App.css"


function resolveDataUrls(config) {
  const resolvedConfig = structuredClone(config)

  for (const dataset of resolvedConfig.datasets ?? []) {
    for (const file of dataset.files ?? []) {
      if (file.url) {
        file.url = new URL(file.url, window.location.origin).href
      }
    }
  }

  return resolvedConfig
}

export default function App() {
  const [config, setConfig] = useState(null)
  const [error, setError] = useState(null)
  const [vitessceHeight, setVitessceHeight] = useState(null)
  const [gridHeight, setGridHeight] = useState(null)

  const wrapperRef = useRef(null)

  // Load configuration and choose the initial Vitessce height.
  useEffect(() => {
    fetch("/api/config")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        return response.json()
      })
      .then((data) => {
        setConfig(resolveDataUrls(data.config))

        const initialHeight = data.height ?? window.innerHeight
        setVitessceHeight(initialHeight)
      })
      .catch(setError)
  }, [])

  // Keep the wrapper height synchronized with the actual Vitessce grid height
  useEffect(() => {
    if (!config || !wrapperRef.current) return

    let observer

    const frame = requestAnimationFrame(() => {
      const grid =
        wrapperRef.current?.querySelector(".react-grid-layout")

      if (!grid) return

      // Initial measured grid height.
      setGridHeight(grid.getBoundingClientRect().height)

      // Follow subsequent height changes caused by resizing grid items.
      observer = new ResizeObserver(([entry]) => {
        setGridHeight(entry.contentRect.height)
      })

      observer.observe(grid)
    })

    return () => {
      cancelAnimationFrame(frame)
      observer?.disconnect()
    }
  }, [config])

  if (error) {
    return <div>Error loading config: {error.message}</div>
  }

  if (!config || vitessceHeight === null) {
    return <div>Loading configuration...</div>
  }

  return (
    <div
      ref={wrapperRef}
      className="vitessce-wrapper"
      style={{
        height: `${gridHeight ?? vitessceHeight}px`,
      }}
    >
      <Vitessce
        config={config}
        height={vitessceHeight}
        theme="dark"
      />
    </div>
  )
}
