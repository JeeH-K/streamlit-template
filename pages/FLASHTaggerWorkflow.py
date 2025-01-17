import streamlit as st
from src.common import page_setup
from src.Workflow import TagWorkflow


# The rest of the page can, but does not have to be changed
if __name__ == "__main__":
    
    params = page_setup()

    #wf = Workflow()
    wf = TagWorkflow()

    st.title(wf.name)

    t = st.tabs(["📁 **File Upload**", "⚙️ **Configure**", "🚀 **Run**"])
    with t[0]:
        wf.show_file_upload_section()

    with t[1]:
        wf.show_parameter_section()

    with t[2]:
        wf.show_execution_section()
