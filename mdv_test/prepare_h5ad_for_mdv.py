import numpy as np
from pathlib import Path
import anndata as ad
import pandas as pd
import sys

ad.settings.allow_write_nullable_strings = True

input_path = Path(sys.argv[1])
output_path = input_path.parent / (input_path.stem + "_corrected.h5ad")

adata = ad.read_h5ad(input_path)


def clean_dataframe(df):
    df = df.copy()

    # Remove "/" in column names
    df.columns = [
        str(col).replace("/", "_")
        for col in df.columns
    ]

    # Handle compatibility problem with string index
    df.index = pd.Index(
        [str(x) for x in df.index],
        dtype=object,
        name=df.index.name,
    )

    # Handle also for columns 
    for col in df.columns:
        s = df[col]

        # Categorical columns:
        if str(s.dtype) == "string":
            df[col]  = s.astype(object)

    return df


adata.obs = clean_dataframe(adata.obs)
adata.var = clean_dataframe(adata.var)

adata.write_h5ad(
    output_path,
    convert_strings_to_categoricals=False,
)
