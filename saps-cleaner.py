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
lea_pop_class_df.to_csv('lea-urban-rural.csv', index=False)



#lea_df = pd.read_csv("census-22-saps/saps-lea.csv", encoding="latin1")
