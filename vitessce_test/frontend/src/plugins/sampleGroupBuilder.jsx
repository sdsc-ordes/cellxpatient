import { useEffect, useMemo, useState } from "react"

import {
  CoordinationType,
  DataType,
  PluginViewType,
} from "vitessce"

import {
  TitleInfo,
  useAsyncFunction,
  useCoordination,
  useLoaders,
  useMatchingLoader,
} from "@vitessce/vit-s"

import {
  REFRESH_SAMPLE_SETS
} from "./sampleSetsRefresh.js"


const EMPTY_DRAFTS = { A: {}, B: {} }


const COORDINATION_TYPES = [
  CoordinationType.DATASET,
  CoordinationType.OBS_TYPE,
  CoordinationType.SAMPLE_TYPE,
  CoordinationType.SAMPLE_SET_SELECTION,
  CoordinationType.SAMPLE_SET_FILTER,
  CoordinationType.SAMPLE_SET_COLOR,
]


function displayValue(value) {
  if (
    value === null
    || value === undefined
    || String(value).trim() === ""
    || String(value).toLowerCase() === "nan"
  ) {
    return "Not available"
  }

  return String(value)
}


// Recursively collect all sample IDs below a node in the sampleSets hierarchy.
function getSampleIdsFromNode(node) {
  if (!node) {
    return []
  }

  if (node.children?.length) {
    return node.children.flatMap(getSampleIdsFromNode)
  }

  return (node.set ?? []).map((entry) =>
    String(Array.isArray(entry) ? entry[0] : entry),
  )
}


function activeCriteria(criteria) {
  return Object.entries(criteria ?? {}).filter(
    ([, values]) => values.length > 0,
  )
}


// OR between values of one category, AND between categories.
function getMatchingSampleIds(sampleSets, criteria) {
  const active = activeCriteria(criteria)

  if (!sampleSets?.tree || active.length === 0) {
    return []
  }

  const perCategory = active.map(([category, values]) => {
    const categoryNode = sampleSets.tree.find(
      (node) => node.name === category,
    )

    return new Set(
      values.flatMap((value) =>
        getSampleIdsFromNode(
          categoryNode?.children?.find((child) => child.name === value),
        ),
      ),
    )
  })

  const [first, ...rest] = perCategory

  return [...first].filter((sampleId) =>
    rest.every((ids) => ids.has(sampleId)),
  )
}


function countCells(sampleEdges, sampleIds) {
  if (!sampleEdges || sampleIds.length === 0) {
    return 0
  }

  const selectedSamples = new Set(sampleIds)
  let count = 0

  sampleEdges.forEach((sampleId) => {
    if (selectedSamples.has(String(sampleId))) {
      count += 1
    }
  })

  return count
}


function formatCriteria(criteria) {
  const active = activeCriteria(criteria)

  if (!active.length) {
    return "No criteria"
  }

  return active
    .map(([category, values]) =>
      `${displayValue(category)}: ${values.map(displayValue).join(" OR ")}`,
    )
    .join("  AND  ")
}


function GroupSummary({ name, criteria, sampleCount, cellCount, active, onEdit }) {
  return (
    <div style={{
      marginTop: "8px",
      padding: "8px",
      border: active ? "2px solid currentColor" : "1px solid currentColor",
      opacity: active ? 1 : 0.8,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <strong>{name}</strong>
        {!active ? (
          <button type="button" onClick={onEdit}>Edit</button>
        ) : <em>editing</em>}
      </div>
      <div>{formatCriteria(criteria)}</div>
      <div>{sampleCount} samples · {cellCount} cells</div>
    </div>
  )
}


export function SampleGroupBuilderSubscriber(props) {
  const {
    coordinationScopes,
    removeGridComponent,
    theme,
    title = "Sample comparison",
    closeButtonVisible,
    customSetName,
    groupLabels,
  } = props


  const customPair = [
    [customSetName, groupLabels.A],
    [customSetName, groupLabels.B],
  ]

  const loaders = useLoaders()

  // Only keep relevant coordination types from defined scope(s)
  const [{
    dataset,
    obsType,
    sampleType,
  }, {
    setSampleSetSelection,
    setSampleSetFilter,
    setSampleSetColor,
  }] = useCoordination(
    COORDINATION_TYPES,
    coordinationScopes,
  )

  // Use built-in Vitessce data loaders
  const sampleSetsLoader = useMatchingLoader(
    loaders,
    dataset,
    DataType.SAMPLE_SETS,
    { sampleType },
  )

  const sampleEdgesLoader = useMatchingLoader(
    loaders,
    dataset,
    DataType.SAMPLE_EDGES,
    { obsType, sampleType },
  )

  const [sampleSets, setSampleSets] = useState(null)
  const [sampleEdges, setSampleEdges] = useState(null)
  const [loadError, setLoadError] = useState(null)

  // External function to refresh the cached samples.csv data
  const refreshSampleSets = useAsyncFunction(REFRESH_SAMPLE_SETS)

  const [drafts, setDrafts] = useState(EMPTY_DRAFTS)
  const [appliedGroups, setAppliedGroups] = useState(null)
  const [applying, setApplying] = useState(false)
  const [applyError, setApplyError] = useState(null)

  const [editingGroup, setEditingGroup] = useState("A")
  const [selectedCategory, setSelectedCategory] = useState("")

  // Load sample-related data
  // (sampleEdges match sample id to cell id, sampleSets are sets of sample id)
  useEffect(() => {
    if (!sampleSetsLoader || !sampleEdgesLoader) {
      return undefined
    }

    let cancelled = false

    async function loadData() {
      try {
        const [sampleSetsResult, sampleEdgesResult] = await Promise.all([
          sampleSetsLoader.load(),
          sampleEdgesLoader.load(),
        ])

        if (cancelled) return

        setSampleSets(sampleSetsResult.data.sampleSets)
        setSampleEdges(sampleEdgesResult.data.sampleEdges)
      } catch (error) {
        if (!cancelled) setLoadError(error)
      }
    }

    loadData()

    return () => {
      cancelled = true
    }
  }, [sampleSetsLoader, sampleEdgesLoader])


  // Filter out the comparison column, not part of real data categories
  const categories = useMemo(
    () => (sampleSets?.tree ?? []).filter(
      (node) => node.name !== customSetName,
    ),
    [sampleSets],
  )

  // Set initially first category as selected category in dropdown
  useEffect(() => {
    if (
      categories.length > 0
      && !categories.some((node) => node.name === selectedCategory)
    ) {
      setSelectedCategory(categories[0].name)
    }
  }, [categories, selectedCategory])

  const categoryValues = useMemo(
    () => (
      categories.find((node) => node.name === selectedCategory)?.children ?? []
    ).map((child) => child.name),
    [categories, selectedCategory],
  )

  // Set which are the values of the selected category (to be ticked)
  const selectedValues = drafts[editingGroup]?.[selectedCategory] ?? []


  // Tick handler for checkbox
  function toggleValue(value) {
    setDrafts((previous) => {
      const groupCriteria = previous[editingGroup] ?? {}
      const current = groupCriteria[selectedCategory] ?? []

      // if current value already selected, removes it, otherwise check it
      const next = current.includes(value)
        ? current.filter((candidate) => candidate !== value)
        : [...current, value]

      const updated = { ...groupCriteria, [selectedCategory]: next }

      if (next.length === 0) {
        delete updated[selectedCategory]
      }

      return { ...previous, [editingGroup]: updated }
    })
  }


  const samplesA = useMemo(
    () => getMatchingSampleIds(sampleSets, drafts.A),
    [sampleSets, drafts.A],
  )

  const samplesB = useMemo(
    () => getMatchingSampleIds(sampleSets, drafts.B),
    [sampleSets, drafts.B],
  )

  const cellsA = useMemo(
    () => countCells(sampleEdges, samplesA),
    [sampleEdges, samplesA],
  )

  const cellsB = useMemo(
    () => countCells(sampleEdges, samplesB),
    [sampleEdges, samplesB],
  )

  const overlappingSamples = useMemo(() => {
    const idsA = new Set(samplesA)
    return samplesB.filter((sampleId) => idsA.has(sampleId))
  }, [samplesA, samplesB])


  // Validate groups (must be non empty and non-overlapping)
  const canApply = samplesA.length > 0
    && samplesB.length > 0
    && overlappingSamples.length === 0

  const draftsMatchApplied = appliedGroups
    && JSON.stringify(appliedGroups) === JSON.stringify(drafts)


  // groups: { A: { category: [values] }, B: {...} }, or null to reset.
  async function applyGroups(groups) {
    setApplying(true)
    setApplyError(null)

    try {
      // Hook in the sample set color manager
      setSampleSetColor(null)

      await refreshSampleSets({ loader: sampleSetsLoader, dataset, groups })

      // Select only once the new sets exist, so views never point at
      // "Group A/B" while the old CSV is still loaded.
      const pair = groups ? customPair : []
      setSampleSetSelection(pair)
      setSampleSetFilter(pair)
      setAppliedGroups(groups)
    } catch (error) {
      setApplyError(error)
    } finally {
      setApplying(false)
    }
  }


  function handleApply() {
    if (!canApply || applying) return
    applyGroups(drafts)
  }


  function handleReset() {
    setDrafts(EMPTY_DRAFTS)
    setEditingGroup("A")
    applyGroups(null)
  }


  return (
    <TitleInfo
      title={title}
      closeButtonVisible={closeButtonVisible}
      removeGridComponent={removeGridComponent}
      theme={theme}
      isReady={Boolean(sampleSets && sampleEdges)}
      errors={[loadError, applyError]}
      isScroll
    >
      <div style={{ padding: "8px", fontSize: "13px" }}>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <strong>Building Group {editingGroup}</strong>

          <label style={{ marginLeft: "12px" }}>
            Clinical metadata:&nbsp;
            <select
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value)}
            >
              {categories.map((category) => (
                <option key={category.name} value={category.name}>
                  {displayValue(category.name)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div style={{ marginTop: "4px", opacity: 0.8 }}>
          Values within a category are combined with OR; categories are combined with AND.
        </div>

        <div style={{
          marginTop: "8px",
          maxHeight: "150px",
          overflowY: "auto",
        }}>
          {categoryValues.map((value) => (
            <label
              key={value}
              style={{ display: "block", marginBottom: "4px" }}
            >
              <input
                type="checkbox"
                checked={selectedValues.includes(value)}
                onChange={() => toggleValue(value)}
              />
              {" "}
              {displayValue(value)}
            </label>
          ))}
        </div>

        <GroupSummary
          name="Group A (control)"
          criteria={drafts.A}
          sampleCount={samplesA.length}
          cellCount={cellsA}
          active={editingGroup === "A"}
          onEdit={() => setEditingGroup("A")}
        />

        <GroupSummary
          name="Group B (case)"
          criteria={drafts.B}
          sampleCount={samplesB.length}
          cellCount={cellsB}
          active={editingGroup === "B"}
          onEdit={() => setEditingGroup("B")}
        />

        {overlappingSamples.length > 0 ? (
          <div style={{ marginTop: "8px", fontWeight: "bold" }}>
            Groups overlap by {overlappingSamples.length} sample(s).
            A sample can only belong to one group.
          </div>
        ) : null}

        <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
          <button
            type="button"
            disabled={!canApply || draftsMatchApplied || applying}
            onClick={handleApply}
          >
            {applying ? "Applying…" : "Apply comparison"}
          </button>

          <button
            type="button"
            disabled={applying || (!appliedGroups && !activeCriteria(drafts.A).length && !activeCriteria(drafts.B).length)}
            onClick={handleReset}
          >
            Reset
          </button>
        </div>

        {appliedGroups ? (
          <div style={{ marginTop: "6px", opacity: 0.8 }}>
            {draftsMatchApplied
              ? "Comparison applied."
              : "Groups changed since the last apply."}
          </div>
        ) : null}
      </div>
    </TitleInfo>
  )
}


export const sampleGroupBuilderPlugin = new PluginViewType(
  "sampleGroupBuilder",
  SampleGroupBuilderSubscriber,
  COORDINATION_TYPES,
)
