"""
Python file that compiles the main lea csv file for which data will be pulled from.
The file should include the following variables for each lea:
    ->county
    ->population
    ->urban/rural pop split
    ->census saps
    ->electoral data for 2024 local and european elections
"""
#Packages
import pandas as pd

#Urban/Rural classifcations -> taking this data that is aggregated by small area and discerning the population urban/rural composition for LEAs
pop_class_df = pd.read_csv("census-22-saps/small-area-pop-classifications.csv")
pop_class_df = pop_class_df.rename(columns={'Small Area': 'SA_ID',
                                            'Type of Urban or Rural Area': 'UR_category',
                                            'VALUE': 'population'})

pop_class_df['population'] = pd.to_numeric(pop_class_df['population'], errors='coerce')

pop_class_widedf = pd.pivot_table(
    data=pop_class_df,
    index='SA_ID',
    columns='UR_category',
    values='population',
    aggfunc='sum',   
    fill_value=0
)

small_area_boundary_df = pd.read_csv("boundary-data-22/small-area-geo-boundaries.csv", usecols=['SA_PUB2022', 'CSO_LEA'])
pop_class_merged_df = pop_class_widedf.merge(
    small_area_boundary_df,
    left_on='SA_ID',
    right_on='SA_PUB2022',
    how='outer',
)

pop_class_merged_df = pop_class_merged_df.rename(columns={'SA_PUB2022' :'SA_ID' })

category_cols = ['Cities', 'Satellite urban towns', 'Independent urban towns',
                  'Rural areas with high urban influence', 
                  'Rural areas with moderate urban influence',
                  'Highly rural/remote areas']

lea_pop_class_df = pop_class_merged_df.groupby('CSO_LEA')[category_cols].sum().reset_index()

#urban index -> Weights that are assigned to populations living in each class of area - used to calcuate a urban score
urban_weights = {
    'Cities': 1.0,
    'Satellite urban towns': 0.8,
    'Independent urban towns': 0.6,
    'Rural areas with high urban influence': 0.4,
    'Rural areas with moderate urban influence': 0.2,
    'Highly rural/remote areas': 0.0
}

lea_pop_class_df["total_population"] = lea_pop_class_df.select_dtypes('number').sum(axis=1)

lea_pop_class_df['urban_index'] = sum(
    lea_pop_class_df[category] * weight for category, weight in urban_weights.items()
) / lea_pop_class_df['total_population']

#Main dataframe -> Merging other data and cleaning
lea_df = pd.read_csv("census-22-saps/saps-lea.csv", encoding="latin1")
lea_boundaries_df = pd.read_csv("boundary-data-22/lea-geo-boundaries.csv")

lea_df["GEOGID"] = lea_df["GEOGID"].astype(str)
lea_boundaries_df["LEA_ID"] = lea_boundaries_df["LEA_ID"].astype(str)

lea_df = lea_df.merge(
    lea_boundaries_df[["LEA_ID", "COUNTY"]],
    left_on="GEOGID",
    right_on="LEA_ID",
    how="outer",
)

lea_df = lea_df.merge(
    lea_pop_class_df[["CSO_LEA","urban_index"]],
    left_on="GEOGDESC",
    right_on="CSO_LEA",
    how="outer"
)

lea_df = lea_df.drop(columns=["GUID", "LEA_ID", "CSO_LEA"])
lea_df = lea_df[lea_df["GEOGID"] != "Ireland"]

#Glossary lookup
glossary_df = pd.read_excel("census-22-saps/glossary.xlsx")

user_column_input = ["T1_1AGE0M", "urban_index"]
id_cols = ["GEOGID", "COUNTY", "GEOGDESC"]
subset_cols = id_cols + user_column_input
subset_lea_df = lea_df[subset_cols]
print(subset_lea_df)

subset_lea_df.to_csv("output.csv", index=False)