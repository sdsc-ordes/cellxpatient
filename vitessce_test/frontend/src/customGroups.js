import { DataType, PluginAsyncFunction } from "vitessce"

// Keep in sync with serve.py.
export const CUSTOM_SET_NAME = "Custom comparison"

export const GROUP_LABELS = {
  A: "Group A",
  B: "Group B",
}

// Path pair written to sampleSetSelection / sampleSetFilter:
// [control, case], same convention as Vitessce's SampleSetPairManager.
export const CUSTOM_PAIR = [
  [CUSTOM_SET_NAME, GROUP_LABELS.A],
  [CUSTOM_SET_NAME, GROUP_LABELS.B],
]

export const REFRESH_SAMPLE_SETS = "refreshSampleSets"


// Reload the sample sets in place, without remounting Vitessce.
//
// Vitessce passes its own React Query client as the first argument to plugin
// async functions (public API). The two `dataSource` lines are NOT public API:
// they rely on how CsvSource caches the parsed CSV in Vitessce 4.0.x.
// Re-check them when upgrading Vitessce.
export const refreshSampleSetsFunction = new PluginAsyncFunction(
  REFRESH_SAMPLE_SETS,
  async ({ queryClient }, { loader, dataset, groups }) => {
    const source = loader.dataSource
    const url = new URL(source.url, window.location.origin)

    if (groups) {
      url.searchParams.set("groups", JSON.stringify(groups))
    } else {
      url.searchParams.delete("groups")
    }

    // Point the CSV source at the new URL and drop its parsed-CSV cache.
    source.url = url.href
    source._data = undefined

    // Refetch every sampleSets query of this dataset. Query keys start with
    // [dataset, dataType, ...], so this prefix matches all views.
    await queryClient.invalidateQueries({
      queryKey: [dataset, DataType.SAMPLE_SETS],
    })
  },
)
