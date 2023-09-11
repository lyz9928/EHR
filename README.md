# EHR
User interface of EHR team in Biomedical data design project fall 2022. The server is hosted using Streamlit community cloud https://share.streamlit.io/


# How to open it through command line
## First clone the repository
git clone https://github.com/lyz9928/EHR/tree/main

## Second create a conda environment using yml file
conda env create -f EHR_GUI.yml
conda activate streamlit

## Run the script
cd [Path-to-Github]/EHR
streamlit run EHR_GUI.py

## Then upload the corpus_test.csv into the website
