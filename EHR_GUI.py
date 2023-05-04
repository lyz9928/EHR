import streamlit as st
from annotated_text import util
from streamlit_timeline import st_timeline
from st_aggrid import GridOptionsBuilder, AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder
#import streamlit_scrollable_textbox as stx
from streamlit.components.v1 import html
import re
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
from ast import literal_eval as le

# -- Set page config
apptitle = 'EHR summary' #website name
st.set_page_config(page_title=apptitle, page_icon=":eyeglasses:",layout="wide")


# side bar
st.sidebar.markdown("## Input files") #side bar name
my_upload = st.sidebar.file_uploader("Upload an file or a folder", type=["csv"]) #file upload panel

#default path to load current data
default_upload = "corpus_test.csv"

select_event = None
if my_upload is not None: # if there is no new data, show the old processed csv
    rawin = pd.read_csv(my_upload)
    rawin["PatientID"] = rawin["PatientID"].map(str)
    rawin["TimeID"] = rawin["TimeID"].map(str)
    names = rawin["PatientID"].unique().tolist()
    st.sidebar.markdown("## Select a patient")
    select_event = st.sidebar.selectbox('select a patient?', names)
    xldf = rawin[rawin["PatientID"] == select_event]
else:
    rawin = pd.read_csv(default_upload)
    rawin["PatientID"] = rawin["PatientID"].map(str)
    rawin["TimeID"] = rawin["TimeID"].map(str)
    names = rawin["PatientID"].unique().tolist()
    st.sidebar.markdown("## Select a patient")
    select_event = st.sidebar.selectbox('select a patient?', names)
    xldf = rawin[rawin["PatientID"] == select_event]

# get the time for creating timeline
filetime_list = []
for text_tag_str in xldf["Real_text_tag"].tolist():
    #remove the first and last []
    text_tag_str = text_tag_str[1:-1]
    #split by , and get the first one
    time_tag_str = text_tag_str.split(",")[2]
    #remove the first and last ''
    time_tag_str = time_tag_str[2:-1]
    filetime = time_tag_str.split(" ")[0]
    filetime_list.append(filetime)
# print(filetime_list)

    

# main page
st.title('Patient Overview')
st.markdown("""
* Use the menu at left to select a patient
* Patient's summary will appear below
""")
if select_event is not None:
    # create df for checkbox
    all_cat = ["CAD", "MEDICATION", "SMOKER", "HYPERTENSION", "DIABETES",'FAMILY_HIST','OBESE','HYPERLIPIDEMIA']
    dat_cat = pd.DataFrame(all_cat, columns=['Category'])
    dat_doc = pd.DataFrame()
    for i in range(xldf["TimeID"].shape[0]):
        tf = [x in le(xldf["Pred_tag_doc"].iloc[i]) for x in all_cat]
        # here change the value to reflect true categories for each docu
        dat_doc.insert(loc=i, column=filetime_list[i], value=tf)
    df = pd.concat([dat_doc,dat_cat], axis = 1)

    # render check box from Java
    checkbox_renderer = JsCode(
            """
            class CheckboxRenderer{
            init(params) {
                this.params = params;
                this.eGui = document.createElement('input');
                this.eGui.type = 'checkbox';
                this.eGui.checked = params.value;
                this.checkedHandler = this.checkedHandler.bind(this);
                this.eGui.addEventListener('click', this.checkedHandler);
            }
            checkedHandler(e) {
                let checked = e.target.checked;
                let colId = this.params.column.colId;
                this.params.node.setDataValue(colId, checked);
            }
            getGui(params) {
                return this.eGui;
            }
            destroy(params) {
            this.eGui.removeEventListener('click', this.checkedHandler);
            }
            }//end class
        """
        )
    cellstyle_jscode = JsCode(
            """
            function(params) {
                if (params.value == "CAD") {
                    return {'color': 'black', 'backgroundColor': '#8ef'};
                } else if (params.value == "SMOKER") {
                    return {'color': 'black', 'backgroundColor': '#faa'};
                }  else if (params.value == "MEDICATION") {
                    return {'color': 'black', 'backgroundColor': '#fea'};
                } else if (params.value == "HYPERTENSION") {
                    return {'color': 'black', 'backgroundColor': '#afa'};
                } else if (params.value == "DIABETES") {
                    return {'color': 'black', 'backgroundColor': '#faf'};
                } else if (params.value == "FAMILY_HIST") {
                    return {'color': 'black', 'backgroundColor': '#664444'};
                } else if (params.value == "OBESE") {
                    return {'color': 'black', 'backgroundColor': '#69c'};
                } else if (params.value == "HYPERLIPIDEMIA") {
                    return {'color': 'black', 'backgroundColor': '#48929b'};
                }
            }
        """
        )
    
    # make check box
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_default_column(groupable = False)
    gd.configure_column("Category", minWidth=150, maxWidth=150, suppressMovable=True)
    #pin the first column
    gd.configure_column("Category", pinned='left', lockPinned=True)

    #make the cell color as the category
    gd.configure_column("Category", cellStyle=cellstyle_jscode)

    
    for i in range(len(filetime_list)):
        gd.configure_column(filetime_list[i], editable=True, cellRenderer=checkbox_renderer, resizable=True, suppressMovable=True)
    gd.configure_selection(selection_mode = 'multiple', use_checkbox = False)
    
    
    gridOption = gd.build()

    ag_grid = AgGrid(
            df,
            gridOptions=gridOption,
            allow_unsafe_jscode=True,
            data_return_mode="as_input",
            update_mode="grid_changed")
    
    # update the session_state based on check box changes so the website can update
    if "df" not in st.session_state:
        st.session_state.df = df
    
    st.session_state.df = ag_grid["data"]


    # make timeline
    items = []
    for i in range(xldf["TimeID"].shape[0]):
        # add the date to "start": date
        temp = {"content": filetime_list[i], "start": filetime_list[i]}
        items.append(temp)
    opts = {
        "height": '200px',
        "moveable": False,
        "zoomable": False,
        "timeAxis": {"scale": "year", "step": 1}
    }
    timeline = st_timeline(items, groups=[], options=opts)
    #hide the time under the timeline

    
# show text
    if timeline is not None:
        st.subheader("Health Record: "+timeline["content"])
        num = filetime_list.index(timeline["content"])

        ## get what check box is selected for a document
        if "selected_rows_array" not in st.session_state:
            st.session_state.selected_rows_array = []
        st.session_state.selected_rows_array = st.session_state.df.iloc[:,num].array
        ## check if the array matched the checkbox. if not, check box changed and re-run the website
        if not np.array_equal(st.session_state.selected_rows_array, st.session_state.df.iloc[:,num].array):
            st.session_state.selected_rows_array = st.session_state.df.iloc[:,num+1].array
            st.experimental_rerun()
        
        rows = [idx for idx, value in enumerate(list(st.session_state.selected_rows_array)) if value == True]
        categories = list(st.session_state.df["Category"].iloc[rows])

        # get the True risk factor for showing
        True_rows = le(xldf["Pred_tag_doc"].iloc[num])
        True_rows = str(True_rows).replace("'",'').replace("[",'').replace("]",'')
        #modify the order of the risk factor
        True_rows = True_rows.replace("CAD", "1CAD").replace("MEDICATION", "2MEDICATION").replace("SMOKER", "3SMOKER").replace("HYPERTENSION", "4HYPERTENSION").replace("DIABETES", "5DIABETES").replace("FAMILY_HIST", "6FAMILY_HIST").replace("OBESE", "7OBESE").replace("HYPERLIPIDEMIA", "8HYPERLIPIDEMIA")
        True_rows = True_rows.split(", ")
        True_rows.sort()
        True_rows = ", ".join(True_rows)
        True_rows = True_rows.replace("1CAD", "CAD").replace("2MEDICATION", "MEDICATION").replace("3SMOKER", "SMOKER").replace("4HYPERTENSION", "HYPERTENSION").replace("5DIABETES", "DIABETES").replace("6FAMILY_HIST", "FAMILY_HIST").replace("7OBESE", "OBESE").replace("8HYPERLIPIDEMIA", "HYPERLIPIDEMIA")

        
        col1, col2 = st.columns(2)

        st.markdown(
        """
        <style>
        [data-testid="stMetricLabel"] {
            color: #69c;
        }
        [data-testid="stMetricValue"] {
            font-size: 25px;
            color: #69c;
            font-weight: bold;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        if len(True_rows) == 0:
            col1.metric("0 Risk factor detected","No risk factor detected")
        else:
            length_Truerows = len(True_rows.split(", "))
            col1.metric(f"{length_Truerows} Risk factor detected", True_rows)
        
        if len(categories) == 0:
            col2.metric(" 0 Risk factor selected","No risk factor selected")
        else:
            categories_list = ', '.join(categories)
            col2.metric( f"{len(categories)} Risk factor selected", categories_list)
        
            #if there is no risk factor selected is in True risk factor, show the unmatched risk factor
            unmatched_list = []
            matched_list = []
            for i in range(len(categories)):
                if categories[i] not in True_rows:
                    unmatched_list.append(categories[i])
                else:
                    matched_list.append(categories[i])
            if len(unmatched_list) != 0:
                if len(matched_list) == 0 and len(True_rows) != 0:
                    st.markdown('<b style="color:#69c"> *'+ str(len(unmatched_list))+' risk factor selected but not detected: '+ ', '.join(unmatched_list)+' . Please re-select risk factor according to the detection.</b>', unsafe_allow_html=True)
                else:
                    st.markdown('<b style="color:#69c"> *'+ str(len(unmatched_list))+' risk factor selected but not detected: '+ ', '.join(unmatched_list)+'</b>', unsafe_allow_html=True)
        
                

        text = xldf["CleanedText"].iloc[num]
        words = text.strip().split()


        annotated = []

        for i,word in enumerate(words):
            TAG = le(xldf["Pred_text_tag"].iloc[num])[i].split()[2]

            if TAG in categories:
                if TAG == "CAD":
                    color = "#8ef"
                    add = (word+' ', "CAD", color)
                elif TAG == "SMOKER":
                    color = "#faa"
                    add = (word+' ', "SMOKER", color)
                elif TAG == "MEDICATION":
                    color = "#fea"
                    add = (word+' ', "MEDICATION", color)
                elif TAG == "HYPERTENSION":
                    color = "#afa"
                    add = (word+' ', "HYPERTENSION", color)
                elif TAG == "DIABETES":
                    color = "#faf"
                    add = (word+' ', "DIABETES", color)
                elif TAG == "HYPERLIPIDEMIA":
                    color = "#48929b"
                    add = (word+' ', "HYPERLIPIDEMIA", color)
                elif TAG == "OBESE":
                    color = "#69c"
                    add = (word+' ', "OBESE", color)
                elif TAG == "FAMILY_HIST":
                    color = "#664444"
                    add = (word+' ', "FAMILY_HIST", color)
            else:
                add = word+' '

            annotated.append(add)

        tt = util.get_annotated_html(annotated)
        html(tt, height=700, scrolling=True)
    else:
        tt = util.get_annotated_html([ "Please ", "select ", ("a ", "verb"), " file ", "in ","the ","timeline ","to ", "start."])
        st.subheader('Annotated Example')
        html(tt, height=100, scrolling=True)
    