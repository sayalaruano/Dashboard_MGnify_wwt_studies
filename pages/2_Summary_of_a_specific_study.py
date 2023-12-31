# Web app
import glob
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from skbio.diversity import beta_diversity
from skbio.stats.ordination import pcoa
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder


# OS and file management
from PIL import Image

# General options 
im = Image.open("img/favicon.ico")
st.set_page_config(
    page_title="Mgnify waste water treatment studies and samples summary",
    page_icon=im,
    layout="wide",
)

# Attach customized ccs style
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Function to load data for a specific study
@st.cache_data
def load_study_data(all_data, selected_study):
    # Filter data for the selected study
    study_info = all_data[all_data['study_id'] == selected_study]
    
    # Load sample information for the study
    sample_info = pd.read_csv(f"Samples_metadata/{selected_study}/{selected_study}_samples_metadata.csv")
    
    return study_info, sample_info

# Function to download the data
@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')

# Function to load abundance table for a specific study
@st.cache_data
def load_abund_table(selected_study):
    # Set the file name 
    folder_path = f"Abundance_tables/{selected_study}/"
    filename = os.path.join(folder_path, f"{selected_study}*phylum_taxonomy*.tsv")

    # Use glob to find files that match the pattern
    file = glob.glob(filename)

    if not file:
        print(f"No files found for the study '{selected_study}' in folder '{folder_path}'.")
        return None
    
    # Take the first file found (you can modify this if you expect multiple files)
    file_path = file[0]
    
    # Load abundance table for the study
    abund_table = pd.read_csv(file_path, sep='\t')
    
    return abund_table

# Function to preprocess abundance table for a specific study
def preprocess_abund_table(abund_table):
    # Delete kingdom and superkingdom columns
    if 'superkingdom' in abund_table.columns:
        abund_table = abund_table.drop(columns=['kingdom', 'superkingdom'])
    else:
        abund_table = abund_table.drop(columns=['kingdom'])

    # Delete rows with unassigned phylum
    abund_table = abund_table[abund_table['phylum'] != 'Unassigned']

    # Delete rows that contain 'Candidatus' or 'candidate'
    abund_table = abund_table[~abund_table['phylum'].str.contains('Candidatus')]
    abund_table = abund_table[~abund_table['phylum'].str.contains('candidate')]
    
    # Reset index
    abund_table = abund_table.reset_index(drop=True)
    
    return abund_table

# Get unique study names
studies_list = st.session_state.studies_data['study_id'].unique()
studies_list = studies_list[~pd.isnull(studies_list)]

# Add info on the sidebar
# Select study
st.sidebar.header('How it works?')

st.sidebar.write('Select a study in the sidebar to display its information in the main panel.')

# Create a selectbox to choose the study
selected_study = st.sidebar.selectbox("Mgnify study:", studies_list)

# Add aditional info
st.sidebar.header('Data')
st.sidebar.write('The data used in this app was obtained from [Mgnify](https://www.ebi.ac.uk/metagenomics/api/latest/) using the scripts available in this [GitHub repository](https://github.com/Multiomics-Analytics-Group/Retrieve_info_MGnifyAPI)')

st.sidebar.header('Code availability')
st.sidebar.write('The code for this project is available under the [MIT License](https://mit-license.org/) in this [GitHub repo](https://github.com/sayalaruano/Dashboard_MGnify_wwt_studies). If you use or modify the source code of this project, please provide the proper attributions for this work.')

st.sidebar.header('Contact')
st.sidebar.write('If you have any comments or suggestions about this work, please [create an issue](https://github.com/sayalaruano/Dashboard_MGnify_wwt_studies/issues/new) in the GitHub repository of this project.')
    
# Add a title and info about the app
st.title('Summary and EDA of waste water treatment studies from Mgnify')

# Load data for the selected study
study_info, sample_info = load_study_data(st.session_state.studies_data, selected_study)

# Display study information
st.subheader(f'Study {selected_study}')

# Create a df to summarize the study information
summ_df = pd.DataFrame(study_info).T

# Remove study_id row
summ_df = summ_df.drop(index='study_id')

# Replace indices and column names
summ_df.index = ['Description', 'Bioproject ID', 'Centre name', 'Number of samples', 
                 'Biome','Experiment type', 'Pipeline version', 'Instrument platform',
                 'Sampling country']

summ_df.columns = ['Summary metrics']

st.data_editor(
    summ_df,
    width = 1000,
    column_config={
        "widgets": st.column_config.TextColumn(
            f"Summary {selected_study}",
            help= f"Summary of the study {selected_study}"
        )
    },
    hide_index=False,
)

# Display sample information for the selected study
st.subheader("Sample Information")

builder = GridOptionsBuilder.from_dataframe(sample_info)
builder.configure_default_column(editable=True, groupable=True)
builder.configure_side_bar(filters_panel = True, columns_panel = True)
builder.configure_selection(selection_mode="multiple")
builder.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
go = builder.build()

AgGrid(sample_info, gridOptions=go)

# Button to download the data
sample_info_csv = convert_df(sample_info)
st.download_button(
    label="Download sample data as CSV",
    data=sample_info_csv,
    file_name=f'sample_info_{selected_study}.csv',
    mime='text/csv',
)

# Load abundance table for the selected study
st.subheader("Abundance table")
abund_table = load_abund_table(selected_study)
abund_table = preprocess_abund_table(abund_table)

# Display abundance table for the selected study
builder = GridOptionsBuilder.from_dataframe(abund_table)
builder.configure_default_column(editable=True, groupable=True)
builder.configure_side_bar(filters_panel = True, columns_panel = True)
builder.configure_selection(selection_mode="multiple")
builder.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
go = builder.build()

AgGrid(abund_table, gridOptions=go)

# Button to download the data
abund_table_csv = convert_df(abund_table)
st.download_button(
    label="Download abundance data as CSV",
    data=abund_table_csv,
    file_name=f'abund_table_{selected_study}.csv',
    mime='text/csv',
)

# Reshape abundance df so that the assembly_run_ids become a column
abund_df_reshaped = abund_table.melt(id_vars='phylum', var_name='assembly_run_ids', value_name='count')

# Split the multiple IDs in the assembly_run_ids column of df1
sample_info['assembly_run_ids'] = sample_info['assembly_run_ids'].str.split(';')

# Explode the dataframe based on the assembly_run_ids column
sample_info_exploded = sample_info.explode('assembly_run_ids')

# Merge dataframes on the 'assembly_run_ids' column
samples_df = pd.merge(sample_info_exploded, abund_df_reshaped, left_on='assembly_run_ids', right_on='assembly_run_ids')

# Filter the merged df to keep unique rows based on the assembly_run_ids column
samples_df = samples_df.drop_duplicates(subset=['assembly_run_ids'])

# Filter the merged df to keep only the relevant columns
samples_df = samples_df[['assembly_run_ids', 'sample_id', 'biome_feature', 'biome_material']].reset_index(drop=True)

# Combine biome_feature and biome_material columnsm if there is info on the columns, otherwise add 'NA'
samples_df['biome_feature'] = samples_df['biome_feature'].fillna('NA')
samples_df['biome_material'] = samples_df['biome_material'].fillna('NA')
samples_df['biome'] = samples_df['biome_feature'] + ' - ' + samples_df['biome_material']

# Sort df by assembly_run_ids
samples_df = samples_df.sort_values(by=['assembly_run_ids']).reset_index(drop=True)

# Create PCA plot
st.subheader("PCA plot")
st.write('The PCA plot shows the distribution of the analyses from the two selected studies based on the abundance of the phyla present in both studies.')

# Transpose abundance table
abund_table = abund_table.set_index('phylum').T

# Extract OTU names and sample names as numpy arrays
otu_names = list(abund_table.columns.values)

# Convert abundance table to numpy array
# Create a PCA object
pca = PCA(n_components=2)

# Standardize the data
abund_values_std = StandardScaler().fit_transform(abund_table)

# Fit the PCA object to the standardized data
pca.fit_transform(abund_values_std)

# Transform the standardized data using the fitted PCA object
pca_data = pca.transform(abund_values_std)

# Create a df with the PCA data
pca_df = pd.DataFrame(data = pca_data, columns = ['PC1', 'PC2'])

# Add the biome to the PCA df
pca_df['biome'] = samples_df['biome']

# Explained variance ratio
explained_var_ratio = pca.explained_variance_ratio_

# Create a plotly figure
pca_plot = px.scatter(pca_df, x='PC1', y='PC2', opacity=0.8,
                      color='biome', 
                      hover_name=abund_table.index,
                      color_discrete_sequence=px.colors.qualitative.Plotly)

# Add title and axis labels
pca_plot.update_layout(
    xaxis=dict(
        title=f'PC1 ({explained_var_ratio[0]:.2%})',
        tickfont=dict(size=18),
        titlefont=dict(size=20),
        showgrid=False
    ),
    yaxis=dict(
        title=f'PC2 ({explained_var_ratio[1]:.2%})',
        tickfont=dict(size=18),
        titlefont=dict(size=20),
        showgrid=False
    ),
    legend_title=dict(text='Biome', font=dict(size=20)),
    legend=dict(font=dict(size=16))
)

# Show pca plot
st.plotly_chart(pca_plot, use_container_width=True)

# Create PcoA plot
st.subheader('PCoA plot with Bray-Curtis distance')
st.write('The PCoA plot shows the distribution of the analyses from the two selected studies based on the Bray-Curtis distance between them.')

# Extract OTU names and analyses names as numpy arrays
otu_names = list(abund_table.columns.values)
analyses_names = list(abund_table.index.values)

# Convert abundance table to numpy array
abund_table_mat = abund_table.to_numpy()

# Obtain bray-curtis distance matrix
bc_mat = beta_diversity("braycurtis", abund_table_mat, analyses_names)

# Replace NaN values with 0
bc_mat = np.nan_to_num(bc_mat.data, nan=0.0)

# Run PCoA
bc_pcoa = pcoa(bc_mat)

# Extract the data to plot the PcoA
bc_pcoa_data = pd.DataFrame(data = bc_pcoa.samples[['PC1', 'PC2']])

# Reset index
bc_pcoa_data = bc_pcoa_data.reset_index(drop=True)

# Add the biome to the PcoA df
bc_pcoa_data['biome'] = samples_df['biome']

# Create a plotly figure
pcoa_plot = px.scatter(bc_pcoa_data, x='PC1', y='PC2', 
                       opacity=0.8, color='biome', 
                       hover_name=abund_table.index,
                       color_discrete_sequence=px.colors.qualitative.Plotly)

# Add title and axis labels
pcoa_plot.update_layout(
    xaxis=dict(
        title='PC1',
        tickfont=dict(size=18),
        titlefont=dict(size=20),
        showgrid=False
    ),
    yaxis=dict(
        title='PC2',
        tickfont=dict(size=18),
        titlefont=dict(size=20),
        showgrid=False
    ),
    legend_title=dict(text='Biome', font=dict(size=20)),
    legend=dict(font=dict(size=16))
)

# Show pcoa plot
st.plotly_chart(pcoa_plot, use_container_width=True)
