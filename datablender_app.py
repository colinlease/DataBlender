import streamlit as st
import pandas as pd
from filehub_app import download_dataframe, upload_dataframe

# --- Secrets sanity check ---
import os

AWS_ACCESS_KEY_ID = st.secrets.get("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID"))
AWS_SECRET_ACCESS_KEY = st.secrets.get("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY"))
S3_BUCKET_NAME = st.secrets.get("S3_BUCKET_NAME", os.getenv("S3_BUCKET_NAME"))
S3_REGION = st.secrets.get("S3_REGION", os.getenv("S3_REGION"))

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION]):
    st.error("Missing AWS credentials or bucket configuration. Please check your `.streamlit/secrets.toml` or Streamlit Cloud Secrets.")

# Config
st.set_page_config(layout="wide")

st.title("DataBlender")
st.subheader("Upload multiple datasets for joining, unioning, pivoting, and more.")

# DataWizard callout
with st.container():
    st.markdown(
        """
        <div style='background-color:#f0f2f6;padding:15px;border-radius:5px;margin-bottom:20px'>
        <strong>Need to conduct EDA or visualize your dataset?</strong><br>
        <a href='https://datawizardtool.streamlit.app/' target='_blank'>Click here to open DataWizard.</a>
        </div>
        """,
        unsafe_allow_html=True
    )

st.write(
    "This tool allows you to upload up to 5 datasets and prepare them for merging. "
    "After uploading, you can choose to join or union them in a future step."
)
st.write(
    "**Upload at least two files to get started.**"
)

MAX_FILES = 5
# ---------- Sidebar: Import from FileHub ----------
st.sidebar.header("")
transfer_token = st.sidebar.text_input("Enter transfer token to load file from FileHub", key="transfer_token_input")
if st.sidebar.button("Submit Token"):
    if transfer_token:
        try:
            df_from_filehub, original_filename = download_dataframe(transfer_token.strip())
            # Find first empty slot
            target_index = None
            for i in range(MAX_FILES):
                if st.session_state.dataframes[i] is None:
                    target_index = i
                    break
            if target_index is not None:
                st.session_state.uploaded_files[target_index] = f"(FileHub: {original_filename})"
                st.session_state.dataframes[target_index] = df_from_filehub
                if st.session_state.file_count <= target_index:
                    st.session_state.file_count = target_index + 1
                st.sidebar.success(f"✅ Imported '{original_filename}' into File {target_index+1}")
            else:
                st.sidebar.warning("⚠️ All 5 file slots are currently filled. Please remove a file before importing.")
        except Exception as e:
            st.sidebar.error("❌ Error retrieving file: {}".format(e))
    else:
        st.sidebar.warning("Please enter a token before submitting.")

# ---------- Sidebar: Reset + File Summaries ----------
st.sidebar.header("📂 File Summary")

if st.sidebar.button("🔄 Reset All"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ---------- Initialize Session State ----------
MAX_ROWS = 75000

if "file_count" not in st.session_state:
    st.session_state.file_count = 1
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = [None] * MAX_FILES
if "dataframes" not in st.session_state:
    st.session_state.dataframes = [None] * MAX_FILES

# ---------- Main Area: File Uploads ----------
for i in range(st.session_state.file_count):
    df = st.session_state.dataframes[i]
    file = st.session_state.uploaded_files[i]

    if df is not None and isinstance(file, str) and file.startswith("(FileHub:"):
        st.success(f"✅ File {i+1} imported from FileHub: {file.replace('(FileHub: ', '').replace(')', '')}")
    else:
        uploaded_file = st.file_uploader(f"Upload File {i+1}", type=["csv", "xls", "xlsx"], key=f"file_{i}")
        if uploaded_file is not None and st.session_state.uploaded_files[i] is None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)

                if df.shape[0] > MAX_ROWS:
                    st.error(f"❌ File {uploaded_file.name} exceeds the 75,000 row limit.")
                else:
                    st.session_state.uploaded_files[i] = uploaded_file
                    st.session_state.dataframes[i] = df
            except Exception as e:
                st.error(f"Error reading File {i+1}: {e}")

# ---------- Add Another File Button ----------
if st.session_state.file_count < MAX_FILES:
    if st.button("➕ Add Another File"):
        st.session_state.file_count += 1
        st.rerun()  # <- updated from experimental_rerun

# ---------- Operation Dropdown ----------
valid_dataframes = [df for df in st.session_state.dataframes if df is not None]

if len(valid_dataframes) >= 1:
    operation = st.selectbox("Operation", ["", "Join", "Union", "Pivot"], key="operation_select")
    if operation == "":
        st.warning("Please select an operation to proceed.")

    if operation == "Union":
        st.info("You selected Union: This will stack all files vertically. All files must have the same column headers in the same order.")

        if st.button("🚀 DataBlendIt"):
            try:
                base_cols = valid_dataframes[0].columns.tolist()
                for idx, df in enumerate(valid_dataframes):
                    if df.columns.tolist() != base_cols:
                        st.error(f"❌ Column mismatch in File {idx+1}. All files must have identical column names and order.")
                        raise ValueError("Column mismatch")

                combined_df = pd.concat(valid_dataframes, ignore_index=True)
                st.session_state['last_result_df'] = combined_df  # For Union
                st.success("✅ Union completed successfully.")
                st.dataframe(combined_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error during union: {e}")

        df_to_upload = st.session_state.get("last_result_df")
        if df_to_upload is not None and isinstance(df_to_upload, pd.DataFrame) and not df_to_upload.empty:
            if st.button("📤 Send to FileHub"):
                try:
                    st.warning("📡 Attempting to upload to FileHub...")
                    token = upload_dataframe(df_to_upload, source_app="DataBlender", original_filename="datablended_output.csv")
                    st.success(f"✅ File sent to FileHub! Transfer Token: {token}")
                    st.info("To use this file in any other DataWiz app, enter this token on the left side of the screen.")
                except Exception as e:
                    st.error("❌ Upload to FileHub failed.")
                    st.exception(e)
        else:
            st.warning("⚠️ No valid dataset available to send. Please complete an operation first.")

    elif operation == "Join":
        join_type = st.selectbox("Join Type", ["inner", "left", "right", "outer"], key="join_type_select")
        st.info("You selected Join: Each file will be joined sequentially using the selected join type.")

        # Capture join keys for each file
        join_keys = []
        for idx, df in enumerate(valid_dataframes):
            st.markdown(f"**Select join key(s) for File {idx+1}**")
            options = list(df.columns)
            selected_keys = st.multiselect(f"Join Key(s) for File {idx+1}", options, key=f"join_keys_{idx}")
            if len(selected_keys) == 0 or len(selected_keys) > 2:
                st.error("Please select 1 or 2 join keys per file.")
            join_keys.append(selected_keys)

        if st.button("🚀 DataBlendIt"):
            try:
                # Validate join key consistency
                key_length = len(join_keys[0])
                for keys in join_keys:
                    if len(keys) != key_length:
                        raise ValueError("All files must use the same number of join keys.")
                
                result_df = valid_dataframes[0]
                result_keys = join_keys[0]

                for i in range(1, len(valid_dataframes)):
                    next_df = valid_dataframes[i]
                    next_keys = join_keys[i]

                    # Validate data types match
                    for rk, nk in zip(result_keys, next_keys):
                        if result_df[rk].dtype != next_df[nk].dtype:
                            raise TypeError(f"Join key type mismatch between '{rk}' and '{nk}'")

                    st.markdown(f"🔗 **Joining File {i} to result using keys {result_keys} ↔ {next_keys}** with `{join_type}` join")
                    result_df = pd.merge(
                        result_df,
                        next_df,
                        how=join_type,
                        left_on=result_keys,
                        right_on=next_keys,
                        suffixes=(None, f"_file{i+1}")
                    )

                    st.markdown(f"✅ **Preview after joining File {i+1}:**")
                    st.dataframe(result_df.head(), use_container_width=True)

                st.session_state['last_result_df'] = result_df  # For Join
                st.success("✅ All files joined successfully.")
                st.markdown("### Final Joined Dataset")
                st.dataframe(result_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error during join: {e}")

        df_to_upload = st.session_state.get("last_result_df")
        if df_to_upload is not None and isinstance(df_to_upload, pd.DataFrame) and not df_to_upload.empty:
            if st.button("📤 Send to FileHub"):
                try:
                    st.warning("📡 Attempting to upload to FileHub...")
                    token = upload_dataframe(df_to_upload, source_app="DataBlender", original_filename="datablended_output.csv")
                    st.success(f"✅ File sent to FileHub! Transfer Token: {token}")
                    st.info("To use this file in other DataWiz apps, enter the token on the left side of the screen.")
                except Exception as e:
                    st.error("❌ Upload to FileHub failed.")
                    st.exception(e)
        else:
            st.warning("⚠️ No valid dataset available to send. Please complete an operation first.")

    elif operation == "Pivot":
        pivot_df = valid_dataframes[0]

        st.info("You selected Pivot: Create a table by reshaping the data using an index, column, and value.")

        index_col = st.selectbox("Select Index (Row Labels)", pivot_df.columns.tolist(), key="pivot_index")
        column_col = st.selectbox("Select Columns (Pivot Headers)", pivot_df.columns.tolist(), key="pivot_columns")
        numeric_cols = pivot_df.select_dtypes(include=["number"]).columns.tolist()
        value_col = st.selectbox("Select Values (Numeric Data)", numeric_cols, key="pivot_values")

        agg_func = st.selectbox("Aggregation Function", ["sum", "mean", "count", "min", "max"], key="pivot_aggfunc")

        if st.button("🚀 DataBlendIt"):
            try:
                pivot_result = pd.pivot_table(
                    pivot_df,
                    index=index_col,
                    columns=column_col,
                    values=value_col,
                    aggfunc=agg_func
                )
                st.session_state['last_result_df'] = pivot_result  # Save pivot result for export

                cell_count = pivot_result.shape[0] * pivot_result.shape[1]

                if cell_count > 1_000_000:
                    st.error("❌ Pivot result is too large (over 1,000,000 cells). Please refine your selections.")
                else:
                    if cell_count > 75_000:
                        st.warning("⚠️ Pivot result exceeds 75,000 cells. Consider simplifying your pivot.")

                    st.success("✅ Pivot completed successfully.")
                    st.markdown(f"**Shape:** {pivot_result.shape[0]} rows × {pivot_result.shape[1]} columns")
                    st.dataframe(pivot_result.head(50), use_container_width=True)

            except Exception as e:
                st.error(f"Error during pivot: {e}")

        df_to_upload = st.session_state.get("last_result_df")
        if df_to_upload is not None and isinstance(df_to_upload, pd.DataFrame) and not df_to_upload.empty:
            if st.button("📤 Send to FileHub"):
                try:
                    st.warning("📡 Attempting to upload to FileHub...")
                    token = upload_dataframe(df_to_upload, source_app="DataBlender", original_filename="datablended_output.csv")
                    st.success(f"✅ File sent to FileHub! Transfer Token: {token}")
                    st.info("To use this file in other DataWiz apps, enter your token on the left side of the screen.")
                except Exception as e:
                    st.error("❌ Upload to FileHub failed.")
                    st.exception(e)
        else:
            st.warning("⚠️ No valid dataset available to send. Please complete an operation first.")

# ---------- Sidebar: Show File Metadata ----------

for i in range(st.session_state.file_count):
    df = st.session_state.dataframes[i]
    file = st.session_state.uploaded_files[i]
    if df is not None and file is not None:
        file_display_name = file.name if hasattr(file, "name") else file
        st.sidebar.markdown(f"**File {i+1}: {file_display_name}**")
        st.sidebar.write(f"Rows: {df.shape[0]}")
        st.sidebar.write(f"Columns: {df.shape[1]}")
        st.sidebar.write(f"Missing Values: {int(df.isna().sum().sum())}")
        st.sidebar.markdown("---")

# ---------- Sidebar: Show Result Summary ----------
result_df = st.session_state.get("last_result_df")
if result_df is not None and isinstance(result_df, pd.DataFrame):
    st.sidebar.header("📊 Result Summary:")
    st.sidebar.write(f"Rows: {result_df.shape[0]}")
    st.sidebar.write(f"Columns: {result_df.shape[1]}")
    st.sidebar.write(f"Missing Values: {int(result_df.isna().sum().sum())}")
