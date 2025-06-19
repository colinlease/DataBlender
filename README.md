DataBlender

Description:
DataBlender is a Streamlit app for combining multiple datasets through join, union, or pivot operations. It supports up to 5 uploaded files and provides validation and previews to ensure datasets are compatible.

Functionality:
	•	Upload up to 5 files (CSV, XLS, XLSX)
	•	Reset all uploads with one button
	•	Select an operation:
	•	Union: Combine all files by stacking them, requires identical column headers
	•	Join: Sequentially join files using 1 or 2 user-selected keys per file; all joins use the same join type
	•	Pivot: Reshape a single file into a pivot table using selected index, columns, values, and aggregation
	•	Provides notes and preview after each join step
	•	Includes a button to open DataWizard for analysis after the files are prepared

Use Case:
This tool is intended for preparing multiple files for analysis, especially when files need to be joined or stacked before use in another tool like DataWizard.
