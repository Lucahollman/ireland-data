"""
Python script that converts wacky xlsx election result format into useful csv file
    ->This requires xml parsing as each LEA is labelled through text boxes in the official csv file (I hate Ireland)
"""

#Packages
import pandas as pd
import openpyxl
import zipfile
import xml.etree.ElementTree as ET
import re

def main():

    #Pulling dataframe from csv
    local_24_df = pd.read_excel(XLSX_PATH, sheet_name=None, header=None)
    sheet_names = list(local_24_df.keys())

    skip_sheets = {'First Preference Counties', '2024 elections', '1st Preference-City_Cos',
                    '1st Preference-City_County  (2', 'Women Candidates', 'Outgoing Members re-elected'}
    county_sheets = [s for s in sheet_names if s not in skip_sheets]

    #Getting LEA names
    z = zipfile.ZipFile(XLSX_PATH)
    wb_xml = z.read('xl/workbook.xml').decode('utf-8')
    sheet_entries = re.findall(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', wb_xml)
    rels_xml = z.read('xl/_rels/workbook.xml.rels').decode('utf-8')
    rid_to_target = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml))

    name_to_sheetfile = {}
    for name, rid in sheet_entries:
        target = rid_to_target.get(rid)
        if target and 'worksheets/sheet' in target:
            sheet_num = re.search(r'sheet(\d+)\.xml', target).group(1)
            name_to_sheetfile[name] = f'sheet{sheet_num}'

    #Looping through each sheet and extracting relevant data
    all_records = []
    for county in county_sheets:
        df = local_24_df[county]

        sheetfile = name_to_sheetfile[county]
        drawing_path = get_drawing_path(z, sheetfile)
        lea_names = get_lea_names(z, drawing_path)

        r = 0
        lea_counter = 0
        while r < len(df):
            col_a = df.iloc[r, 0]

            if isinstance(col_a, str) and 'NAMES OF CANDIDATES' in col_a.upper():
                lea_name = lea_names[lea_counter] if lea_counter < len(lea_names) else None
                lea_counter += 1
                r += 2
                while r < len(df):
                    name = df.iloc[r, 0]
                    gender = df.iloc[r, 1]
                    first_count = df.iloc[r, 2]

                    if isinstance(name, str) and 'TOTALS' in name.upper():
                        r += 1
                        break
                    if isinstance(name, str) and isinstance(first_count, (int, float)) and 'NON-TRANSFERABLE' not in name.upper():
                        all_records.append({
                            'county': county,
                            'lea': lea_name,
                            'candidate': name,
                            'gender': gender,
                            'first_pref_votes': first_count
                        })
                    r += 2
            else:
                r += 1

    #Cleaning results and putting in csv file
    results_df = pd.DataFrame(all_records)

    results_df['lea_total_votes'] = results_df.groupby(['county', 'lea'])['first_pref_votes'].transform('sum')
    results_df['vote_share'] = results_df['first_pref_votes'] / results_df['lea_total_votes']
    results_df = results_df.drop(columns=['county', 'first_pref_votes', 'lea_total_votes'])

    results_df['party'] = results_df['candidate'].str.extract(r'\(([^)]+)\)\s*$')
    results_df['candidate'] = results_df['candidate'].str.replace(r'\s*\([^)]+\)\s*$', '', regex=True).str.strip()

    results_df['lea'] = (
    results_df['lea']
    .str.replace(r'\s*-\s*.*County Council\s*$', '', regex=True) 
    .str.replace(r'\s*LEA\s*$', '', regex=True, case=False)        
    .str.strip()
    .str.upper()
)

    results_df.to_csv('election-data-24/lea-first-preference-results.csv', index=False)

#Functions
XLSX_PATH = "election-data-24/local-24.xlsx"

ns = {
    'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
}

def get_lea_names(z, drawing_path):
        """Return LEA names from a sheet's drawing file, in top-to-bottom order."""
        xml = z.read(drawing_path).decode('utf-8')
        root = ET.fromstring(xml)
        boxes = []
        for anchor in root.findall('xdr:twoCellAnchor', ns):
            row = int(anchor.find('xdr:from/xdr:row', ns).text)
            text = ''.join(t.text or '' for t in anchor.findall('.//a:t', ns))
            if 'CONSTITUENCY OF' in text.upper():
                lea_name = text.strip().split('\n')[-1]
                boxes.append((row, lea_name))
        boxes.sort()  
        return [name for row, name in boxes]

def get_drawing_path(z, sheetfile):
        rels = z.read(f'xl/worksheets/_rels/{sheetfile}.xml.rels').decode('utf-8')
        root = ET.fromstring(rels)
        for rel in root:
            if 'drawing' in rel.attrib.get('Type', ''):
                return rel.attrib['Target'].replace('..', 'xl')
        return None



if __name__ == "__main__":
    main()