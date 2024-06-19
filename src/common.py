import json
import os
import shutil
import sys
import uuid
from typing import Any
from pathlib import Path
from src.captcha_ import captcha_control
from st_pages import add_page_title, hide_pages, show_pages_from_config

import streamlit as st
import pandas as pd

# set these variables according to your project
APP_NAME = "FLASHViewer"
ALL_SECTIONS = [APP_NAME, "FLASHDeconv", "FLASHTnT", "FLASHQuant"]


def load_params(default: bool = False) -> dict[str, Any]:
    """
    Load parameters from a JSON file and return a dictionary containing them.

    If a 'params.json' file exists in the workspace, load the parameters from there.
    Otherwise, load the default parameters from 'assets/default-params.json'.

    Additionally, check if any parameters have been modified by the user during the current session
    and update the values in the parameter dictionary accordingly. Also make sure that all items from
    the parameters dictionary are accessible from the session state as well.

    Args:
        default (bool): Load default parameters. Defaults to True.

    Returns:
        dict[str, Any]: A dictionary containing the parameters.
    """
    # Construct the path to the parameter file
    path = Path(st.session_state.workspace, "params.json")

    # Load the parameters from the file, or from the default file if the parameter file does not exist
    if path.exists() and not default:
        with open(path, "r") as f:
            params = json.load(f)
    else:
        with open("assets/default-params.json", "r") as f:
            params = json.load(f)

    # Return the parameter dictionary
    return params


def save_params(params: dict[str, Any]) -> None:
    """
    Save the given dictionary of parameters to a JSON file.

    If a 'params.json' file already exists in the workspace, overwrite it with the new parameters.
    Otherwise, create a new 'params.json' file in the workspace directory and save the parameters there.

    Additionally, check if any parameters have been modified by the user during the current session
    and update the values in the parameter dictionary accordingly.

    This function should be run at the end of each page, if the parameters dictionary has been modified directly.
    Note that session states with the same keys will override any direct changes!

    Args:
        params (dict[str, Any]): A dictionary containing the parameters to be saved.

    Returns:
        None
    """
    # Update the parameter dictionary with any modified parameters from the current session
    for key, value in st.session_state.items():
        if key in params.keys():
            params[key] = value

    # Save the parameter dictionary to a JSON file in the workspace directory
    path = Path(st.session_state.workspace, "params.json")
    with open(path, "w") as outfile:
        json.dump(params, outfile, indent=4)


def page_setup(page: str = "", help_text: str = "") -> dict[str, Any]:
    """
    Set up the Streamlit page configuration and determine the workspace for the current session.

    This function should be run at the start of every page for setup and to get the parameters dictionary.

    Args:
        page (str, optional): The name of the current page, by default "".

    Returns:
        dict[str, Any]: A dictionary containing the parameters loaded from the parameter file.
    """
    # Set Streamlit page configurations
    configuration = {
        "page_title" : APP_NAME,
        "page_icon" : "assets/OpenMS.png",
        "layout" : "wide",
        "initial_sidebar_state" : "auto",
        "menu_items" : None
    }

    # Setup sidebar
    if 'current_tool_name' in st.session_state:
        hide_pages(list(set(ALL_SECTIONS) - {APP_NAME} - {st.session_state.current_tool_name}))
        add_page_title(**configuration)

    else:
        show_pages_from_config()
        add_page_title(**configuration)

    st.markdown("""
        <style>
            .stMultiSelect [data-baseweb=select] span{
                max-width: 500px;
                font-size: 1rem;
            }
        </style>
        """, unsafe_allow_html=True)

    # Determine the workspace for the current session
    if "workspace" not in st.session_state:
        # Clear any previous caches
        st.cache_data.clear()
        st.cache_resource.clear()
        # Check location
        if "local" in sys.argv:
            st.session_state.location = "local"
            st.session_state.controllo = True
        else:
            st.session_state.location = "online"
            st.session_state.controllo = False
        # if we run the packaged windows version, we start within the Python directory -> need to change working directory to ..\streamlit-template
        if "windows" in sys.argv:
            os.chdir("../flashtaggerviewer")
        # Define the directory where all workspaces will be stored
        workspaces_dir = Path("workspaces")
        if st.session_state.location == "online":
            st.session_state.workspace = Path(workspaces_dir, str(uuid.uuid1()))
        else:
            st.session_state.workspace = Path(workspaces_dir, "default")

    # If run in hosted mode, show captcha as long as it has not been solved
    if ("controllo" not in  st.session_state) or (not st.session_state["controllo"]):
        # Hide all pages
        hide_pages(ALL_SECTIONS)
        # Apply captcha by calling the captcha_control function
        captcha_control()

    # Make sure the necessary directories exist
    st.session_state.workspace.mkdir(parents=True, exist_ok=True)
    # checking input directories are done in FileUpload page (to accompany both FLASHDeconv and FLASHQuant)
    # Path(st.session_state.workspace, "mzML-files").mkdir(parents=True, exist_ok=True)


    #st.session_state["workspace"] = Path(str(uuid.uuid1()))
    # Make sure important directories exist
    st.session_state["workspace"].mkdir(parents=True, exist_ok=True)
    # for mzML (deconvolved)
    st.session_state["deconv-mzML-files"] = Path(st.session_state["workspace"], "deconv-mzML-files")
    st.session_state["deconv-mzML-files"].mkdir(parents=True, exist_ok=True)
    # for FASTA
    st.session_state["fasta-files"] = Path(st.session_state["workspace"], "fasta-files")
    st.session_state["fasta-files"].mkdir(parents=True, exist_ok=True)


    # Render the sidebar
    params = render_sidebar(page, help_text)
    return params


def render_sidebar(page: str = "", help_text: str = "") -> dict[str, Any]:
    """
    Renders the sidebar on the Streamlit app, which includes the workspace switcher,
    the mzML file selector, the logo, and settings.

    Args:
        page (str): A string indicating the current page of the Streamlit app.
        help_text (str): If there's information to show on the sidebar
    Returns:
        dict[str, Any]: A dictionary containing the parameters.
    """
    params = load_params()
    with st.sidebar:
        # The main page has workspace switcher
        if (page == "main") or (page == 'FLASHViewer'):
            st.markdown("🖥️ **Workspaces**")
            # Define workspaces directory outside of repository
            workspaces_dir = Path("workspaces")  # workspace inside FLASHViewer directory
            # Online: show current workspace name in info text and option to change to other existing workspace
            if st.session_state.location == "online":
                # Change workspace...
                new_workspace = st.text_input("enter workspace", "")
                if st.button("**Enter Workspace**", type="primary", disabled=not new_workspace) and new_workspace:
                    path = Path(workspaces_dir, new_workspace)
                    if path.exists():
                        st.session_state.workspace = path
                        st.success(f"Switched to workspace **{new_workspace}**")
                    else:
                        st.warning("⚠️ Workspace does not exist.")
                # Display info on current workspace and warning
                st.info(
                    f"""💡 Your workspace ID:

**{st.session_state['workspace'].name}**

You can share this unique workspace ID with other people.

⚠️ Anyone with this ID can access your data!"""
                )
            # Local: user can create/remove workspaces as well and see all available
            elif st.session_state.location == "local":
                # Define callback function to change workspace
                def change_workspace():
                    for key in params.keys():
                        if key in st.session_state.keys():
                            del st.session_state[key]
                    st.session_state.workspace = Path(
                        workspaces_dir, st.session_state["chosen-workspace"]
                    )

                # Get all available workspaces as options
                options = [
                    file.name for file in workspaces_dir.iterdir() if file.is_dir()
                ]
                # Let user chose an already existing workspace
                st.selectbox(
                    "choose existing workspace",
                    options,
                    index=options.index(str(st.session_state.workspace.stem)),
                    on_change=change_workspace,
                    key="chosen-workspace",
                )
                # Create or Remove workspaces
                create_remove = st.text_input("create/remove workspace", "")
                path = Path(workspaces_dir, create_remove)
                # Create new workspace
                if st.button("**Create Workspace**"):
                    path.mkdir(parents=True, exist_ok=True)
                    st.session_state.workspace = path
                    st.rerun()
                # Remove existing workspace and fall back to default
                if st.button("⚠️ Delete Workspace"):
                    if path.exists():
                        shutil.rmtree(path)
                        st.session_state.workspace = Path(workspaces_dir, "default")
                        st.rerun()

        # All pages have settings, workflow indicator and logo
        with st.expander("⚙️ **Settings**"):
            img_formats = ["svg", "png", "jpeg", "webp"]
            st.selectbox(
                "image export format",
                img_formats,
                img_formats.index(params["image-format"]),
                key="image-format",
            )
        if (page != "main") and (page != "FLASHViewer"):
            st.info(f"**{Path(st.session_state['workspace']).stem}**")
        st.image("assets/OpenMS.png", "powered by")
        if help_text:
            st.info(help_text)
        st.image("assets/pyopenms_transparent_background.png", "powered by")
    return params


def v_space(n: int, col=None) -> None:
    """
    Prints empty strings to create vertical space in the Streamlit app.

    Args:
        n (int): An integer representing the number of empty lines to print.
        col: A streamlit column can be passed to add vertical space there.

    Returns:
        None
    """
    for _ in range(n):
        if col:
            col.write("#")
        else:
            st.write("#")


def show_table(df: pd.DataFrame, download_name: str = "") -> pd.DataFrame:
    """
    Displays a pandas dataframe using Streamlit's `dataframe` function and
    provides a download button for the same table.

    Args:
        df (pd.DataFrame): The pandas dataframe to display.
        download_name (str): The name to give to the downloaded file. Defaults to empty string.

    Returns:
        df (pd.DataFrame): The possibly edited dataframe.
    """
    # Show dataframe using container width
    st.dataframe(df, use_container_width=True)
    # Show download button with the given download name for the table if name is given
    if download_name:
        st.download_button(
            "Download Table",
            df.to_csv(sep="\t").encode("utf-8"),
            download_name.replace(" ", "-") + ".tsv",
        )
    return df


def show_fig(fig, download_name: str, container_width: bool = True) -> None:
    """
    Displays a Plotly chart and adds a download button to the plot.

    Args:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure to display.
        download_name (str): The name for the downloaded file.
        container_width (bool, optional): If True, the figure will use the container width. Defaults to True.

    Returns:
        None
    """
    # Display plotly chart using container width and removed controls except for download
    st.plotly_chart(
        fig,
        use_container_width=container_width,
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": [
                "zoom",
                "pan",
                "select",
                "lasso",
                "zoomin",
                "autoscale",
                "zoomout",
                "resetscale",
            ],
            "toImageButtonOptions": {
                "filename": download_name,
                "format": st.session_state["image-format"],
            },
        },
    )


def reset_directory(path: Path) -> None:
    """
    Remove the given directory and re-create it.

    Args:
        path (Path): Path to the directory to be reset.

    Returns:
        None
    """
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


# General warning/error messages
def sidebar(page=""):
    with st.sidebar:
        if (page == "main") or (page == "FLASHViewer"):
            st.markdown("### Workspaces")
            if st.session_state["location"] == "online":
                new_workspace = st.text_input("enter workspace", "")
                if st.button("**Enter Workspace**") and new_workspace:
                    st.session_state["workspace"] = Path(new_workspace)
                st.info(
                    f"""💡 Your workspace ID:

**{st.session_state['workspace']}**

You can share this unique workspace ID with other people.

⚠️ Anyone with this ID can access your data!"""
                )
            elif st.session_state["location"] == "local":
                # Show available workspaces
                options = [
                    file.name
                    for file in Path(".").iterdir()
                    if file.is_dir()
                    and file.name
                    not in (
                        ".git",
                        ".gitignore",
                        ".streamlit",
                        "example-data",
                        "pages",
                        "src",
                        "assets",
                    )
                ]
                chosen_workspace = st.selectbox(
                    "choose existing workspace",
                    options,
                    index=options.index(str(st.session_state["workspace"])),
                )
                if chosen_workspace:
                    st.session_state["workspace"] = Path(chosen_workspace)

                # Create or Remove workspaces
                st.text_input("create/remove workspace", "", key="create-remove")
                path = Path(st.session_state["create-remove"])
                if st.button("**Create Workspace**") and path.name:
                    path.mkdir(parents=True, exist_ok=True)
                    st.session_state["workspace"] = path
                if st.button("⚠️ Delete Workspace") and path.exists:
                    shutil.rmtree(path)
                    st.session_state["workspace"] = Path("default-workspace")
            st.markdown("***")

        # TODO: revive this later
        elif page == "files":
            # Show currently available mzML files
            st.markdown("### Uploaded Files")
            for f in sorted(Path(st.session_state["deconv-mzML-files"]).iterdir()):
                if f.name in st.session_state:
                    checked = st.session_state[f.name]
                else:
                    checked = True
                st.checkbox(f.name, checked, key=f.name)

            for f in sorted(Path(st.session_state["fasta-files"]).iterdir()):
                if f.name in st.session_state:
                    checked = st.session_state[f.name]
                else:
                    checked = True
                st.checkbox(f.name, checked, key=f.name)

        #     # Option to remove files
        #     v_space(1)
        #     st.markdown("⚠️ **Remove files**")
        #     c1, c2 = st.columns(2)
        #     if c1.button("**All**"):
        #         reset_directory(st.session_state["mzML-files"])
        #
        #     if c2.button("**Un**selected"):
        #         for file in [
        #             Path(st.session_state["mzML-files"], key)
        #             for key, value in st.session_state.items()
        #             if key.endswith("mzML") and not value  # e.g. unchecked
        #         ]:
        #             file.unlink()
        #         st.experimental_rerun()
        #
            st.markdown("***")
        st.image("assets/OpenMS.png", "powered by")


WARNINGS = {
    "missing-mzML": "Upload or select some mzML files first!",
}

ERRORS = {
    "general": "Something went wrong.",
    "workflow": "Something went wrong during workflow execution.",
    "visualization": "Something went wrong during visualization of results.",
}
