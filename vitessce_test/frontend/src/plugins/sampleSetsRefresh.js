import { DataType, PluginAsyncFunction } from "vitessce"

export const REFRESH_SAMPLE_SETS = "refreshSampleSets"

// Reload the sample sets in place, without remounting Vitessce.
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

    // Refetch every sampleSets query of this dataset
    await queryClient.invalidateQueries({
      queryKey: [dataset, DataType.SAMPLE_SETS],
    })
  },
)
