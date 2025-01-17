import streamlit as st
import pandas as pd
from pathlib import Path
import os
import shutil

from src.masstable import parseFLASHDeconvOutput
from src.common import page_setup, v_space, save_params, reset_directory


input_file_types = ["deconv-mzMLs", "anno-mzMLs"]
parsed_df_types = ["deconv_dfs", "anno_dfs"]


def initializeWorkspace(input_file_types_: list, parsed_df_types_: list) -> None:
    """
    Set up the required directory and session states
    parameter is needed: this method is used in FLASHQuant
    """
    for dirname in input_file_types_:
        Path(st.session_state.workspace, dirname).mkdir(parents=True, exist_ok=True)
        if dirname not in st.session_state:
            # initialization
            st.session_state[dirname] = []
        # sync session state and default-workspace
        st.session_state[dirname] = os.listdir(Path(st.session_state.workspace, dirname))

    # initializing session state for storing data
    for df_type in parsed_df_types_:
        if df_type not in st.session_state:
            st.session_state[df_type] = {}


@st.cache_data
def getUploadedFileDF(deconv_files_, anno_files_):
    # leave only names
    deconv_files_ = [Path(f).name for f in deconv_files_]
    anno_files_ = [Path(f).name for f in anno_files_]

    # getting experiment name from annotated file (tsv files can be multiple per experiment)
    experiment_names = [f[0: f.rfind('_')] for f in anno_files_]

    df = pd.DataFrame({'Experiment Name': experiment_names,
                       'Deconvolved Files': deconv_files_,
                       'Annotated Files': anno_files_})
    return df


def remove_selected_mzML_files(to_remove: list[str], params: dict) -> dict:
    """
    Removes selected mzML files from the mzML directory. (From fileUpload.py)

    Args:
        to_remove (List[str]): List of mzML files to remove.
        params (dict): Parameters.


    Returns:
        dict: parameters with updated mzML files
    """
    for input_type, df_type, file_postfix in zip(input_file_types, parsed_df_types,
                                                 ['_deconv.mzML', '_annotated.mzML']):
        mzml_dir = Path(st.session_state["workspace"], input_type)
        # remove all given files from mzML workspace directory and selected files
        for exp_name in to_remove:
            file_name = exp_name + file_postfix
            Path(mzml_dir, file_name).unlink()
            del st.session_state[df_type][file_name]  # removing key
        # for k, v in params.items():
        #     if isinstance(v, list):
        #         if f in v:
        #             params[k].remove(f)

    # update the experiment df table
    tmp_df = st.session_state["experiment-df"]
    tmp_df.drop(tmp_df.loc[tmp_df['Experiment Name'].isin(to_remove)].index, inplace=True)
    st.session_state["experiment-df"] = tmp_df

    st.success("Selected mzML files removed!")
    return params


def handleInputFiles(uploaded_files):
    for file in uploaded_files:
        if not file.name.endswith("mzML"):
            continue

        session_name = ''
        if file.name.endswith('_deconv.mzML'):
            session_name = 'deconv-mzMLs'
        elif file.name.endswith('_annotated.mzML'):
            session_name = 'anno-mzMLs'
        if file.name not in st.session_state[session_name]:
            with open(
                    Path(st.session_state.workspace, session_name, file.name), "wb"
            ) as f:
                f.write(file.getbuffer())
            st.session_state[session_name].append(file.name)


def parseUploadedFiles():
    # get newly uploaded files
    deconv_files = st.session_state['deconv-mzMLs']
    anno_files = st.session_state['anno-mzMLs']
    # anno_files = Path(st.session_state['anno-mzMLs']).iterdir()
    new_deconv_files = [f for f in deconv_files if f not in st.session_state['deconv_dfs']]
    new_anno_files = [f for f in anno_files if f not in st.session_state['anno_dfs']]

    # if newly uploaded files are not as needed
    if len(new_deconv_files) == 0 and len(new_anno_files) == 0:  # if no newly uploaded files, move on
        return
    elif len(new_deconv_files) != len(new_anno_files):  # if newly uploaded files doesn't match, write message
        st.error('Added files are not in pair, so not parsed. \n Here are uploaded ones, but not parsed ones:')
        # not_parsed = [f.name for f in new_deconv_files] + [f.name for f in new_anno_files]
        not_parsed = new_deconv_files + new_anno_files
        for i in not_parsed:
            st.markdown("- " + i)
        return

    # parse newly uploaded files
    new_deconv_files = sorted(new_deconv_files)
    new_anno_files = sorted(new_anno_files)

    # parse with progress bar
    with st.session_state['progress_bar_space']:
        for anno_f, deconv_f in zip(new_anno_files, new_deconv_files):
            if not anno_f.endswith('.mzML'):
                continue
            exp_name = anno_f[0: anno_f.rfind('_')]

            with st.spinner('Parsing the experiment %s...' % exp_name):
                spec_df, anno_df, tolerance, massoffset, chargemass = parseFLASHDeconvOutput(
                    Path(st.session_state["workspace"], "anno-mzMLs", anno_f),
                    Path(st.session_state["workspace"], "deconv-mzMLs", deconv_f)
                )
                st.session_state['anno_dfs'][anno_f] = anno_df
                st.session_state['deconv_dfs'][deconv_f] = spec_df
            st.success('Done parsing the experiment %s!' % exp_name)


def showUploadedFilesTable() -> bool:
    ''' return: if showing without error '''
    # for error message or list of uploaded files
    deconv_files = sorted(st.session_state["deconv_dfs"].keys())
    anno_files = sorted(st.session_state["anno_dfs"].keys())

    # error message if files not exist
    if len(deconv_files) == 0 and len(anno_files) == 0:
        st.info('No mzML added yet!', icon="ℹ️")
    elif len(deconv_files) == 0:
        st.error("FLASHDeconv deconvolved mzML file is not added yet!")
    elif len(anno_files) == 0:
        st.error("FLASHDeconv annotated mzML file is not added yet!")
    elif len(deconv_files) != len(anno_files):
        st.error("The same number of deconvolved and annotated mzML file should be uploaded!")
    else:
        v_space(2)
        st.session_state["experiment-df"] = getUploadedFileDF(deconv_files, anno_files)
        st.markdown('**Uploaded experiments in current workspace**')
        st.dataframe(st.session_state["experiment-df"])  # show table
        v_space(1)
        return True
    return False


# for Workflow
def postprocessingAfterUpload_FD(uploaded_files: list) -> None:
    initializeWorkspace(input_file_types, parsed_df_types)
    #handleInputFiles(uploaded_files)
    parseUploadedFiles()
    showUploadedFilesTable()


if __name__ == '__main__':

    # page initialization
    params = page_setup()

    # make directory to store deconv and anno mzML files & initialize data storage
    initializeWorkspace(input_file_types, parsed_df_types)

    st.title("FLASHDeconv output files Upload")

    tabs = st.tabs(["File Upload", "Example Data"])

    # Load Example Data
    with tabs[1]:
        st.markdown("An example truncated file from the ThermoFisher Pierce Intact Protein Standard Mix dataset.")
        _, c2, _ = st.columns(3)
        if c2.button("Load Example Data", type="primary"):
            # loading and copying example files into default workspace
            for filename_postfix, input_file_session_name in zip(['*deconv.mzML', '*annotated.mzML'],
                                                                input_file_types):
                for file in Path("example-data/flashdeconv").glob(filename_postfix):
                    if file.name not in st.session_state[input_file_session_name]:
                        shutil.copy(file, Path(st.session_state["workspace"], input_file_session_name, file.name))
                        st.session_state[input_file_session_name].append(file.name)
            # parsing the example files is done in parseUploadedFiles later
            st.success("Example mzML files loaded!")

    # Upload files via upload widget
    with tabs[0]:
        st.subheader("**Upload FLASHDeconv output files (\*_annotated.mzML & \*_deconv.mzML)**")
        # Display info how to upload files
        st.info(
            """
        **💡 How to upload files**
        
        1. Browse files on your computer or drag and drops files
        2. Click the **Add the uploaded mzML files** button to use them in the workflows
        
        Select data for analysis from the uploaded files shown below.
        
        **💡 Make sure that the same number of deconvolved and annotated mzML files are uploaded!**
        """
        )
        with st.form('input_mzml', clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "FLASHDeconv output mzML files", accept_multiple_files=True
            )
            _, c2, _ = st.columns(3)
            # User needs to click button to upload selected files
            if c2.form_submit_button("Add mzML files to workspace", type="primary"):
                # Copy uploaded mzML files to deconv-mzML-files directory
                if uploaded_file:
                    # A list of files is required, since online allows only single upload, create a list
                    if type(uploaded_file) != list:
                        uploaded_file = [uploaded_file]

                    # opening file dialog and closing without choosing a file results in None upload
                    handleInputFiles(uploaded_file)
                    st.success("Successfully added uploaded files!")
                else:
                    st.warning("Upload some files before adding them.")

    # parse files if newly uploaded
    st.session_state['progress_bar_space'] = st.container()
    parseUploadedFiles()

    if showUploadedFilesTable():
        # Remove files
        with st.expander("🗑️ Remove mzML files"):
            to_remove = st.multiselect(
                "select mzML files", options=st.session_state["experiment-df"]['Experiment Name']
            )
            c1, c2 = st.columns(2)
            if c2.button(
                    "Remove **selected**", type="primary", disabled=not any(to_remove)
            ):
                params = remove_selected_mzML_files(to_remove, params)
                # save_params(params)
                st.rerun()

            if c1.button("⚠️ Remove **all**", disabled=not any(st.session_state["experiment-df"])):
                for file_option, df_option in zip(input_file_types, parsed_df_types):
                    if file_option in st.session_state:
                        reset_directory(Path(st.session_state.workspace, file_option))
                        st.session_state[file_option] = []
                    if df_option in st.session_state:
                        st.session_state[df_option] = {}

                        # for k, v in params.items():
                        #     if df_option in k and isinstance(v, list):
                        #         params[k] = []
                st.success("All mzML files removed!")
                del st.session_state["experiment-df"]  # reset the experiment df table
                # save_params(params)
                st.rerun()

    save_params(params)
