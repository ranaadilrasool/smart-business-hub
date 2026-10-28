# app.py
# This is the main file for the Smart Business Operations Hub.
# Run this file using the command: streamlit run app.py

import streamlit as st
import pandas as pd
import database as db
from datetime import date

# --- PAGE CONFIGURATION ---
# This sets the browser tab title and the layout style.
st.set_page_config(
    page_title="Smart Business Operations Hub",
    page_icon="📊",
    layout="wide"
)

# Initialize the database (creates tables if they don't exist yet)
db.init_db()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
# This creates the radio buttons in the sidebar to switch pages
page = st.sidebar.radio(
    "Go to",
    ["Dashboard Overview", "Clients", "Projects", "Tasks", "Reports"]
)

# --- PAGE 1: DASHBOARD OVERVIEW ---
if page == "Dashboard Overview":
    st.title("📊 Dashboard Overview")
    st.write("Welcome to your business command center.")

    # 1. Fetch real data from the database
    counts = db.get_dashboard_counts()

    # 2. Display Summary Cards (Metrics)
    # We use 3 columns for the first row
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Clients", counts["total_clients"])
    col2.metric("Total Projects", counts["total_projects"])
    col3.metric("Active Projects", counts["active_projects"])

    # We use 3 columns for the second row
    col4, col5, col6 = st.columns(3)
    col4.metric("Completed Projects", counts["completed_projects"])
    col5.metric("Pending Tasks", counts["pending_tasks"])
    # The delta shows the overdue count in red if it's greater than 0
    col6.metric("Overdue Tasks", counts["overdue_tasks"], delta=counts["overdue_tasks"] if counts["overdue_tasks"] > 0 else None, delta_color="inverse")

    st.divider()

    # 3. Charts Section
    st.subheader("Status Overview")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.write("**Projects by Status**")
        project_data = db.get_project_status_counts()
        if project_data:
            # Convert the dictionary to a Pandas DataFrame for the chart
            df_projects = pd.DataFrame(list(project_data.items()), columns=["Status", "Count"])
            st.bar_chart(df_projects, x="Status", y="Count", color="#1f77b4")
        else:
            st.info("No project data available yet.")

    with chart_col2:
        st.write("**Tasks by Status**")
        task_data = db.get_task_status_counts()
        if task_data:
            df_tasks = pd.DataFrame(list(task_data.items()), columns=["Status", "Count"])
            st.bar_chart(df_tasks, x="Status", y="Count", color="#ff7f0e")
        else:
            st.info("No task data available yet.")

    st.divider()

    # 4. Upcoming Deadlines and Overdue Tasks
    list_col1, list_col2 = st.columns(2)

    with list_col1:
        st.subheader("⏰ Upcoming Deadlines")
        deadlines = db.get_upcoming_deadlines()
        if deadlines:
            # Convert to DataFrame for a clean table display
            df_deadlines = pd.DataFrame([dict(row) for row in deadlines])
            df_deadlines.columns = ["Type", "Title", "Deadline", "Status"]
            st.dataframe(df_deadlines, hide_index=True, use_container_width=True)
        else:
            st.success("No upcoming deadlines! You are all caught up.")

    with list_col2:
        st.subheader("🚨 Overdue Tasks")
        overdue = db.get_overdue_tasks()
        if overdue:
            df_overdue = pd.DataFrame([dict(row) for row in overdue])
            # Select only the columns we want to show
            df_overdue = df_overdue[["title", "project_name", "deadline", "priority"]]
            df_overdue.columns = ["Task", "Project", "Deadline", "Priority"]
            st.dataframe(df_overdue, hide_index=True, use_container_width=True)
        else:
            st.success("No overdue tasks! Great job.")

# --- PLACEHOLDERS FOR OTHER PAGES ---
# We will build these in the next stages.
elif page == "Clients":
    st.title("👥 Clients")
    st.write("Manage your client directory here.")

    # --- 1. ADD A NEW CLIENT ---
    with st.expander("➕ Add New Client", expanded=False):
        with st.form("add_client_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Client Name *")
            company = col2.text_input("Company")
            email = col1.text_input("Email Address")
            phone = col2.text_input("Phone Number")
            notes = st.text_area("Notes (Optional)")
            
            submitted = st.form_submit_button("Save Client")
            if submitted:
                if not name.strip():
                    st.error("Client Name is required.")
                else:
                    db.create_client(name, company, email, phone, notes)
                    st.success(f"Client '{name}' added successfully!")
                    st.rerun() # This refreshes the page so the new client appears immediately

    st.divider()

    # --- 2. VIEW AND SEARCH CLIENTS ---
    st.subheader("All Clients")
    search_query = st.text_input("🔍 Search clients by name, company, or email", "")
    
    # Fetch clients from database based on search
    clients = db.get_clients(search_query)

    if not clients:
        st.info("No clients found. Add one above!")
    else:
        # Loop through each client and create an expander for them
        for client in clients:
            client_title = f"🏢 {client['name']} ({client['company'] or 'No Company'})"
            
            with st.expander(client_title):
                # --- EDIT CLIENT FORM ---
                with st.form(f"edit_client_{client['id']}"):
                    col1, col2 = st.columns(2)
                    edit_name = col1.text_input("Name *", value=client['name'])
                    edit_company = col2.text_input("Company", value=client['company'] or "")
                    edit_email = col1.text_input("Email", value=client['email'] or "")
                    edit_phone = col2.text_input("Phone", value=client['phone'] or "")
                    edit_notes = st.text_area("Notes", value=client['notes'] or "")
                    
                    # Put buttons side by side
                    btn_col1, btn_col2 = st.columns(2)
                    update_btn = btn_col1.form_submit_button("Update Client")
                    delete_btn = btn_col2.form_submit_button("Delete Client", type="primary")
                    
                    if update_btn:
                        if not edit_name.strip():
                            st.error("Name is required.")
                        else:
                            db.update_client(client['id'], edit_name, edit_company, edit_email, edit_phone, edit_notes)
                            st.success("Client updated!")
                            st.rerun()
                            
                    if delete_btn:
                        # Check if they have projects before warning
                        proj_count = db.count_projects_for_client(client['id'])
                        if proj_count > 0:
                            st.warning(f"⚠️ This client has {proj_count} project(s). If you delete the client, those projects will become unassigned.")
                        
                        # Checkbox to confirm deletion
                        if st.checkbox("Confirm delete", key=f"del_check_{client['id']}"):
                            db.delete_client(client['id'])
                            st.success("Client deleted.")
                            st.rerun()

elif page == "Projects":
    st.title("📁 Projects")
    st.write("Manage your projects, deadlines, and budgets.")

    # Fetch all clients to populate the dropdown menu
    all_clients = db.get_clients()
    # Create a dictionary mapping "Client Name" to "Client ID" for the dropdown
    client_options = {c['name']: c['id'] for c in all_clients}

    # --- 1. ADD A NEW PROJECT ---
    with st.expander("➕ Add New Project", expanded=False):
        if not all_clients:
            st.warning("You need to add a Client first before creating a Project.")
        else:
            with st.form("add_project_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                proj_name = col1.text_input("Project Name *")
                # Dropdown to select the client
                selected_client_name = col2.selectbox("Client *", list(client_options.keys()))
                
                description = st.text_area("Description")
                
                col3, col4 = st.columns(2)
                # st.date_input returns a date object. We will convert it to string later.
                start_date = col3.date_input("Start Date")
                deadline = col4.date_input("Deadline")
                
                col5, col6, col7 = st.columns(3)
                budget = col5.number_input("Estimated Budget ($)", min_value=0.0, step=100.0)
                status = col6.selectbox("Status", ["Planned", "In Progress", "On Hold", "Completed"])
                progress = col7.slider("Progress (%)", 0, 100, 0)
                
                submitted = st.form_submit_button("Save Project")
                if submitted:
                    if not proj_name.strip():
                        st.error("Project Name is required.")
                    else:
                        # Convert dates to string format (YYYY-MM-DD) for the database
                        start_str = start_date.strftime("%Y-%m-%d") if start_date else None
                        deadline_str = deadline.strftime("%Y-%m-%d") if deadline else None
                        client_id = client_options[selected_client_name]
                        
                        db.create_project(client_id, proj_name, description, start_str, deadline_str, budget, status, progress)
                        st.success(f"Project '{proj_name}' created successfully!")
                        st.rerun()

    st.divider()

    # --- 2. VIEW AND FILTER PROJECTS ---
    st.subheader("All Projects")
    
    # Filtering options
    filter_col1, filter_col2 = st.columns(2)
    filter_status = filter_col1.selectbox("Filter by Status", ["All", "Planned", "In Progress", "On Hold", "Completed"])
    filter_client_name = filter_col2.selectbox("Filter by Client", ["All"] + list(client_options.keys()))
    
    # Determine which filters to apply
    status_filter = filter_status if filter_status != "All" else None
    client_id_filter = client_options[filter_client_name] if filter_client_name != "All" else None
    
    # Fetch projects from database with filters
    projects = db.get_projects(status=status_filter, client_id=client_id_filter)

    if not projects:
        st.info("No projects found matching your filters.")
    else:
        for proj in projects:
            proj_title = f"📁 {proj['name']} — {proj['client_name'] or 'Unassigned'}"
            
            with st.expander(proj_title):
                # Display progress bar right away
                st.progress(proj['progress'] / 100.0, text=f"Progress: {proj['progress']}%")
                
                with st.form(f"edit_project_{proj['id']}"):
                    col1, col2 = st.columns(2)
                    edit_name = col1.text_input("Project Name *", value=proj['name'])
                    
                    # Find the current client's name to pre-select in the dropdown
                    current_client_name = proj['client_name'] if proj['client_name'] else ""
                    client_list = ["Unassigned"] + list(client_options.keys())
                    # Handle case where current client name might not be in list (rare edge case)
                    default_index = client_list.index(current_client_name) if current_client_name in client_list else 0
                    
                    edit_client_name = col2.selectbox("Client", client_list, index=default_index)
                    
                    edit_desc = st.text_area("Description", value=proj['description'] or "")
                    
                    col3, col4 = st.columns(2)
                    # Parse existing date strings back into date objects for the widget
                    curr_start = date.fromisoformat(proj['start_date']) if proj['start_date'] else None
                    curr_deadline = date.fromisoformat(proj['deadline']) if proj['deadline'] else None
                    
                    edit_start = col3.date_input("Start Date", value=curr_start)
                    edit_deadline = col4.date_input("Deadline", value=curr_deadline)
                    
                    col5, col6, col7 = st.columns(3)
                    edit_budget = col5.number_input("Estimated Budget ($)", value=float(proj['budget']), step=100.0)
                    status_list = ["Planned", "In Progress", "On Hold", "Completed"]
                    edit_status = col6.selectbox("Status", status_list, index=status_list.index(proj['status']))
                    edit_progress = col7.slider("Progress (%)", 0, 100, int(proj['progress']))
                    
                    btn_col1, btn_col2 = st.columns(2)
                    update_btn = btn_col1.form_submit_button("Update Project")
                    delete_btn = btn_col2.form_submit_button("Delete Project", type="primary")
                    
                    if update_btn:
                        if not edit_name.strip():
                            st.error("Project Name is required.")
                        else:
                            edit_start_str = edit_start.strftime("%Y-%m-%d") if edit_start else None
                            edit_deadline_str = edit_deadline.strftime("%Y-%m-%d") if edit_deadline else None
                            
                            # Get the ID for the selected client (or None if Unassigned)
                            edit_client_id = client_options.get(edit_client_name, None)
                            
                            db.update_project(proj['id'], edit_client_id, edit_name, edit_desc, edit_start_str, edit_deadline_str, edit_budget, edit_status, edit_progress)
                            st.success("Project updated!")
                            st.rerun()
                            
                    if delete_btn:
                        task_count = db.count_tasks_for_project(proj['id'])
                        if task_count > 0:
                            st.warning(f"⚠️ Warning: This project has {task_count} task(s). Deleting this project will also delete all of its tasks!")
                        
                        if st.checkbox("Confirm delete project", key=f"del_proj_{proj['id']}"):
                            db.delete_project(proj['id'])
                            st.success("Project deleted.")
                            st.rerun()

elif page == "Tasks":
    st.title("✅ Tasks")
    st.write("Manage your daily tasks and deadlines.")

    # Fetch all projects to populate the dropdown menu
    all_projects = db.get_projects()
    # Create a dictionary mapping "Project Name" to "Project ID"
    project_options = {p['name']: p['id'] for p in all_projects}
    
    # Get today's date for the overdue check
    today_str = date.today().strftime("%Y-%m-%d")

    # --- 1. ADD A NEW TASK ---
    with st.expander("➕ Add New Task", expanded=False):
        if not all_projects:
            st.warning("You need to add a Project first before creating a Task.")
        else:
            with st.form("add_task_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                task_title = col1.text_input("Task Title *")
                selected_project_name = col2.selectbox("Project *", list(project_options.keys()))
                
                description = st.text_area("Description")
                
                col3, col4, col5 = st.columns(3)
                deadline = col3.date_input("Deadline")
                priority = col4.selectbox("Priority", ["Low", "Medium", "High"])
                status = col5.selectbox("Status", ["To Do", "In Progress", "Completed"])
                
                submitted = st.form_submit_button("Save Task")
                if submitted:
                    if not task_title.strip():
                        st.error("Task Title is required.")
                    else:
                        deadline_str = deadline.strftime("%Y-%m-%d") if deadline else None
                        project_id = project_options[selected_project_name]
                        
                        db.create_task(project_id, task_title, description, deadline_str, priority, status)
                        st.success(f"Task '{task_title}' created successfully!")
                        st.rerun()

    st.divider()

    # --- 2. VIEW AND FILTER TASKS ---
    st.subheader("All Tasks")
    
    # Filtering options
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    filter_project = filter_col1.selectbox("Filter by Project", ["All"] + list(project_options.keys()))
    filter_priority = filter_col2.selectbox("Filter by Priority", ["All", "Low", "Medium", "High"])
    filter_status = filter_col3.selectbox("Filter by Status", ["All", "To Do", "In Progress", "Completed"])
    
    # Determine which filters to apply
    proj_filter = project_options[filter_project] if filter_project != "All" else None
    prio_filter = filter_priority if filter_priority != "All" else None
    stat_filter = filter_status if filter_status != "All" else None
    
    # Fetch tasks from database with filters
    tasks = db.get_tasks(project_id=proj_filter, priority=prio_filter, status=stat_filter)

    if not tasks:
        st.info("No tasks found matching your filters.")
    else:
        for task in tasks:
            # Check if the task is overdue
            is_overdue = False
            if task['deadline'] and task['status'] != 'Completed':
                if task['deadline'] < today_str:
                    is_overdue = True
            
            # Create a visual title based on priority and overdue status
            priority_icon = "🔴" if task['priority'] == "High" else "🟡" if task['priority'] == "Medium" else "🟢"
            overdue_badge = " ⚠️ **OVERDUE**" if is_overdue else ""
            
            task_title = f"{priority_icon} {task['title']} ({task['project_name']}){overdue_badge}"
            
            with st.expander(task_title):
                # Show a red error box if it's overdue
                if is_overdue:
                    st.error(f"This task is overdue! Deadline was {task['deadline']}.")
                
                with st.form(f"edit_task_{task['id']}"):
                    col1, col2 = st.columns(2)
                    edit_title = col1.text_input("Task Title *", value=task['title'])
                    
                    # Pre-select the current project
                    current_project_name = task['project_name'] if task['project_name'] else ""
                    proj_list = list(project_options.keys())
                    default_index = proj_list.index(current_project_name) if current_project_name in proj_list else 0
                    
                    edit_project_name = col2.selectbox("Project", proj_list, index=default_index)
                    
                    edit_desc = st.text_area("Description", value=task['description'] or "")
                    
                    col3, col4, col5 = st.columns(3)
                    curr_deadline = date.fromisoformat(task['deadline']) if task['deadline'] else None
                    edit_deadline = col3.date_input("Deadline", value=curr_deadline)
                    
                    prio_list = ["Low", "Medium", "High"]
                    edit_priority = col4.selectbox("Priority", prio_list, index=prio_list.index(task['priority']))
                    
                    status_list = ["To Do", "In Progress", "Completed"]
                    edit_status = col5.selectbox("Status", status_list, index=status_list.index(task['status']))
                    
                    btn_col1, btn_col2 = st.columns(2)
                    update_btn = btn_col1.form_submit_button("Update Task")
                    delete_btn = btn_col2.form_submit_button("Delete Task", type="primary")
                    
                    if update_btn:
                        if not edit_title.strip():
                            st.error("Task Title is required.")
                        else:
                            edit_deadline_str = edit_deadline.strftime("%Y-%m-%d") if edit_deadline else None
                            edit_project_id = project_options.get(edit_project_name, None)
                            
                            db.update_task(task['id'], edit_project_id, edit_title, edit_desc, edit_deadline_str, edit_priority, edit_status)
                            st.success("Task updated!")
                            st.rerun()
                            
                    if delete_btn:
                        if st.checkbox("Confirm delete task", key=f"del_task_{task['id']}"):
                            db.delete_task(task['id'])
                            st.success("Task deleted.")
                            st.rerun()

elif page == "Reports":
    st.title("📈 Reports & Analytics")
    st.write("Analyze your business data and download reports.")

    # --- 1. HIGH-LEVEL STATS ---
    counts = db.get_dashboard_counts()
    total_budget = db.get_budget_total()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Clients", counts["total_clients"])
    col2.metric("Total Projects", counts["total_projects"])
    # Format the budget nicely with commas and 2 decimal places
    col3.metric("Total Estimated Budget", f"${total_budget:,.2f}")

    st.divider()

    # --- 2. DOWNLOAD DATA AS CSV ---
    st.subheader("📥 Download Data")
    st.write("Export your data to CSV files to open in Excel or Google Sheets.")
    
    dl_col1, dl_col2 = st.columns(2)
    
    with dl_col1:
        # Fetch all projects for CSV
        all_projects_csv = db.get_projects()
        if all_projects_csv:
            # Convert to Pandas DataFrame
            df_proj_csv = pd.DataFrame([dict(row) for row in all_projects_csv])
            # Convert to CSV string
            csv_proj = df_proj_csv.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Projects CSV",
                data=csv_proj,
                file_name="projects_report.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("Download Projects CSV", disabled=True, use_container_width=True)

    with dl_col2:
        # Fetch all tasks for CSV
        all_tasks_csv = db.get_tasks()
        if all_tasks_csv:
            df_task_csv = pd.DataFrame([dict(row) for row in all_tasks_csv])
            csv_task = df_task_csv.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Tasks CSV",
                data=csv_task,
                file_name="tasks_report.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("Download Tasks CSV", disabled=True, use_container_width=True)

    st.divider()

    # --- 3. DETAILED PROJECT REPORT TABLE ---
    st.subheader("📁 Project Financial Overview")
    
    projects_data = db.get_projects()
    if projects_data:
        # Prepare data for the table
        table_data = []
        for p in projects_data:
            table_data.append({
                "Project Name": p['name'],
                "Client": p['client_name'] or "Unassigned",
                "Status": p['status'],
                "Progress": f"{p['progress']}%",
                "Start Date": p['start_date'] or "-",
                "Deadline": p['deadline'] or "-",
                "Estimated Budget": f"${p['budget']:,.2f}"
            })
            
        df_table = pd.DataFrame(table_data)
        st.dataframe(df_table, hide_index=True, use_container_width=True)
        
        st.info("💡 Note: 'Estimated Budget' is the planned amount. The system does not track actual expenses or profit yet.")
    else:
        st.info("No project data available to report on.")