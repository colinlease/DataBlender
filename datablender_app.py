import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter

st.set_page_config(layout="wide")

st.title("DataBlender")
st.subheader("Upload and Combine Multiple Datasets")
st.write(
    "Use this tool to upload up to 5 datasets and prepare them for joining or unioning. "
    "Once you've uploaded your files, choose your operation below."
)

# --- Constants ---
MAX_FILES = 5
ACCEPTED_TYPES = ["csv", "xls", "xlsx"]

# --- Session State Init ---
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# --- File Upload UI ---
uploaded_file = st.file_uploader("Upload your file here", type=ACCEPTED_TYPES, key=f"main_file_{len(st.session_state.uploaded_files)}")

if uploaded_file:
    if len(st.session_state.uploaded_files) >= MAX_FILES:
        st.error(f"Cannot upload more than {MAX_FILES} files.")
    else:
        # Try loading file
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            if df.shape[0] > 75000:
                st.error(f"{uploaded_file.name} exceeds 75,000 row limit.")
            else:
                st.session_state.uploaded_files.append({
                    "name": uploaded_file.name,
                    "df": df
                })
                st.success(f"Uploaded: {uploaded_file.name}")

        except Exception as e:
            st.error(f"Failed to read file: {e}")

# --- Add Another File Button ---
if len(st.session_state.uploaded_files) < MAX_FILES:
    if st.button("Add Another File"):
        st.experimental_rerun()  # re-run to trigger another file_uploader

# --- Operation Dropdown ---
if len(st.session_state.uploaded_files) >= 2:
    operation = st.selectbox("Choose an operation", ["Join", "Union"], key="operation_type")

    if operation == "Join":
        join_type = st.selectbox("Select join type", ["inner", "left", "right", "outer"], key="join_type")

# --- File Summaries ---
st.sidebar.markdown("### File Summaries")
for file_data in st.session_state.uploaded_files:
    df = file_data["df"]
    inferred_types = {}
    for col in df.columns:
        dtype = pd.api.types.infer_dtype(df[col], skipna=True)
        if dtype in ["string", "categorical", "object"]:
            inferred = "categorical"
        elif dtype in ["integer", "floating", "mixed-integer-float"]:
            inferred = "numeric"
        elif dtype.startswith("datetime"):
            inferred = "datetime"
        else:
            inferred = "other"
        inferred_types[col] = inferred

    st.sidebar.markdown(f"**{file_data['name']}**")
    st.sidebar.write(f"Rows: {df.shape[0]}")
    st.sidebar.write(f"Columns: {df.shape[1]}")
    st.sidebar.write(f"Missing Values: {int(df.isna().sum().sum())}")

    type_counts = Counter(inferred_types.values())
    for t, count in type_counts.items():
        label = t.capitalize() if t != "other" else "Other/Unknown"
        st.sidebar.write(f"{label}: {count}")

# --- Preview Tables ---
if st.session_state.uploaded_files:
    st.markdown("### Data Previews")
    for file_data in st.session_state.uploaded_files:
        st.markdown(f"**{file_data['name']}**")
        st.dataframe(file_data["df"].head(10), use_container_width=True)
