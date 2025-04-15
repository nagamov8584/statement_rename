import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_pdf_viewer import pdf_viewer
from streamlit_extras.add_vertical_space import add_vertical_space
#from PyPDF2 import PdfReader
import time
import os
import re
import zipfile
import io
import base64

st.set_page_config(
    page_title="Bank statement renaming", 
    layout="wide")

def extract(lst):
    return [item[0] for item in lst]
def find_account(input_string):
    res = re.search(r'\d{20}', input_string)
    return res[0]
def env_initiation():
    
    if 'rename_matrix' not in st.session_state:
        st.session_state.rename_matrix = None
    if 'raw_files' not in st.session_state:
        st.session_state.raw_files = None
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
    if 'recognized_files' not in st.session_state:
        st.session_state.recognized_files = []
    if 'nonrecognized_files' not in st.session_state:
        st.session_state.nonrecognized_files = []
    if 'files_for_zip' not in st.session_state:
        st.session_state.files_for_zip = {}
def data_prep_load():
    #old chunk of code for database kept in Google spreadsheets
        #conn = st.connection("gsheets", type=GSheetsConnection)
        #url = "https://docs.google.com/spreadsheets/d/1ftUQL2RRga6sXe7gqjv19FmUDinwtkR-o_UNmFBFMXs/edit"
        #data = conn.read(spreadsheet=url, usecols=[0, 1, 2])
    if rename_matrix is None:
        st.warning('Матрица переименования не загружена', icon="⚠️")
        data = pd.DataFrame(columns=['account', 'file_name', 'class'])
    else:
        data = pd.read_excel(rename_matrix)
        data.columns = ['account', 'file_name', 'class']
    return data
def file_segregation(data):
    # Function separates uploaded data into 3 structures:

    # initial - raw_files
    #_________________________________
    # generated - recognized_files
    # generated - nonrecognized_files
    # generated - uploaded_files (all)

    file_not_detected = '❌ Файл не определен ❌'
    account_not_detected = '❌ Номер счета не найден ❌'

    if upload:
        st.session_state.raw_files = upload
        for file in st.session_state.raw_files:

            # First check: account pattern
            if_found = re.search(r'\d{20}', file.name)
            file_name = file.name

            if if_found:
                account_detected = if_found[0]
            # Second check: if in Spreadsheet DB
                if account_detected in data.account.tolist():
                    file.name = account_detected

                    if file_name not in extract(st.session_state.recognized_files):
                        st.session_state.recognized_files.append([file_name, account_detected, True])
                        st.session_state.uploaded_files.append(([file_name, account_detected, True]))

                        st.session_state.files_for_zip[account_detected] = file

                else:
                    if file_name not in extract(st.session_state.nonrecognized_files):
                        st.session_state.nonrecognized_files.append([file_name, account_not_detected, False])
                        st.session_state.uploaded_files.append(([file_name, account_not_detected, False]))
            else:
                if file_name not in extract(st.session_state.nonrecognized_files):
                    st.session_state.nonrecognized_files.append([file_name, file_not_detected, False])
                    st.session_state.uploaded_files.append(([file_name, file_not_detected, False]))
def db_creation(data, db):
    upload_db = pd.DataFrame(data, columns=['upl_filename', 'account', 'recognition_status'])
    rename_db = upload_db.merge(db ,how='left', on='account')[
        ['account', 'upl_filename', 'file_name', 'class']]
    
    return upload_db, rename_db
def recongnition_status(upload, data):
    col1, col2, col3 = st.columns(3)
    #
    upl_m = len(upload)
    recogn_m = len(data)
    nonrecogn_m = upl_m - recogn_m
    #
    col1.metric(label="Файлов загружено", value=upl_m, delta=upl_m, delta_color='off')
    col2.metric("Распознано", recogn_m, recogn_m)
    col3.metric("Нераспознано", nonrecogn_m, nonrecogn_m, delta_color='inverse')
def preview():
    
    if_show_rename = st.toggle('Show upload&rename table')
    if if_show_rename and not len(upload) == 0:
        options = {
            'All': st.session_state.uploaded_files, 
            'Recognized': st.session_state.recognized_files, 
            'Non-recognized': st.session_state.nonrecognized_files}
        
        control = st.segmented_control('Show uploaded files', options)
        
        if control:
            #st.write(options[control])
            st.dataframe(options[control], 
                        use_container_width=True)
        
    elif if_show_rename and len(upload) == 0:
        st.warning('No files uploaded')
def create_zip(files_to_zip, rename_db):
        zip_buffer = io.BytesIO()
        
        # Create a Zip file in memory
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

            for account in files_to_zip:
                    recorded_file = files_to_zip[account]

                    #st.write(files_to_zip[account].name, ' ---> ', account, 'was added to zip')
                    pdf_name = rename_db[rename_db['account'] == account]['file_name'].values[0] + '.pdf'
                    st.write(account, ' ---> ', pdf_name, 'was added to zip')

                    zip_file.writestr(pdf_name, recorded_file.getvalue())
                    recorded_file = []
             
        zip_buffer.seek(0)  # Rewind the buffer to the beginning
        return zip_buffer
def look_at_fund_accounts (db):
    option = st.radio("Choose AMC of interest", options=["None", "S+", "WIM"], index=0)

    if option == "S+":
        st.dataframe(db[db['class'].isin(['S', 'S', 'AFI'])])
    elif option == "WIM":
        st.dataframe(db[db['class'] == 'W'])
    else:
        pass
    ###
def download_zip(files_to_zip, rename_db):
    if st.button('Download ZIP of PDFs'):
        if files_to_zip:
            zip_buffer = create_zip(files_to_zip, rename_db)
            st.download_button(
                label="Download ZIP",
                data=zip_buffer,
                file_name="pdf_files.zip",
                mime="application/zip",
                icon=":material/barcode:"
            )
        else:
            st.warning("Please upload some PDF files first.")


#####################################

with st.popover("Excel", use_container_width=True):
    st.markdown("excel-файл с перечнем фондов 👋")
    rename_matrix = st.file_uploader("Загрузите excel-файл с перечнем фондов", accept_multiple_files=False, type=["csv", "xlsx", "xls"])



gspreadsheet = data_prep_load()

env_initiation()

upload = st.file_uploader(
    "Загружаем файлики", accept_multiple_files=True, type='pdf')

#statements = []
file_segregation(data=gspreadsheet)

upload_db, rename_db = db_creation(data=st.session_state.recognized_files, db=gspreadsheet)
#
#st.dataframe(rename_db)
add_vertical_space(6)
#
recongnition_status(upload, data=st.session_state.recognized_files)
preview()
#
add_vertical_space(6)
#
look_at_fund_accounts(gspreadsheet)
download_zip(st.session_state.files_for_zip, rename_db)

