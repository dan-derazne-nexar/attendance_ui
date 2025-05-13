import streamlit as st
import pandas as pd
import io
import pandas as pd
import csv

def read_csv_auto_delimiter(file_path_or_buffer):
    # Peek at a sample of the file to detect delimiter
    if hasattr(file_path_or_buffer, 'read'):
        sample = file_path_or_buffer.read(1024)
        file_path_or_buffer.seek(0)
    else:
        with open(file_path_or_buffer, 'r') as f:
            sample = f.read(1024)

    dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';'])
    return pd.read_csv(file_path_or_buffer, delimiter=dialect.delimiter)



st.set_page_config(page_title="Office Attendance Analyzer", layout="wide")
st.title("📊 Office Attendance Analyzer")
selected_office = "Porto" if st.toggle("Switch to Porto", value=False) else "TLV"
# Default values for excluded and low-requirement users
default_excluded_users = "Yuval Shir, Ana Pereira, Jose Silva, Yivgeny Romanenko, Itamar Bul" if selected_office == "TLV" else "Office Porto"
default_low_req_users = "Silvia Johanna-Benquis-Hes, Oren Hadar, Dean Becker, Moshe Maizels" if selected_office == "TLV" else ""

# Toggle for name selection


uploaded_file = st.file_uploader("Upload the attendance CSV file", type="csv")
exclude_users_input = st.text_area("Exclude Users (comma-separated)", value=default_excluded_users)
low_requirement_users_input = st.text_area("Users with Low Attendance Requirement (comma-separated)", value=default_low_req_users)
total_employees_input = st.text_input("Total Number of Employees (optional)", value="36" if selected_office == "TLV" else "30")

if uploaded_file:
    if selected_office == "TLV":
        df = pd.read_csv(uploaded_file, delimiter=',')
    else:
        df = pd.read_csv(uploaded_file, delimiter=';')
    
    # Create User column from first and last name if they exist
    if 'User First Name' in df.columns and 'User Last Name' in df.columns:
        df['User'] = df['User First Name'] + ' ' + df['User Last Name']

    # Filter for valid entry events
    if "Event Category" in df.columns:
        entry_df = df[(df['Event Category'] == 'lock_opened') & (df['User'].notna())].copy()
    else:
        entry_df = df[(df['Event'] == 'Entry Unlock') & (df['Result'] == 'Granted') & (df['User'].notna())].copy()

    # Handle excluded users
    exclude_users = [u.strip() for u in exclude_users_input.split(',') if u.strip()]
    if exclude_users:
        entry_df = entry_df[~entry_df['User'].isin(exclude_users)]

    # Identify users with lower attendance requirement
    low_req_users = [u.strip() for u in low_requirement_users_input.split(',') if u.strip()]

    # Time conversion
    if 'Local Time' in entry_df.columns:
        entry_df['timestamp'] = pd.to_datetime(entry_df['Local Time'], errors='coerce')
    else:
        entry_df['timestamp'] = pd.to_datetime(entry_df['Browser time'], errors='coerce')
    entry_df['date'] = entry_df['timestamp'].dt.date
    entry_df['weekday'] = entry_df['timestamp'].dt.day_name()
    entry_df['month'] = entry_df['timestamp'].dt.to_period('M')

    # Unique user per day
    unique_daily = entry_df.drop_duplicates(subset=['date', 'User'])
    daily_counts = unique_daily.groupby(['date', 'weekday']).size().reset_index(name='unique_user_count')

    # Averages
    avg_daily = daily_counts['unique_user_count'].mean()
    mandatory_days = ['Monday', 'Thursday'] if selected_office == "TLV" else ['Tuesday', 'Thursday']
    non_mandatory_days = ['Sunday', 'Tuesday', 'Wednesday'] if selected_office == "TLV" else ['Monday', 'Wednesday', 'Friday']
    avg_mandatory = daily_counts[daily_counts['weekday'].isin(mandatory_days)]['unique_user_count'].mean()
    avg_non_mandatory = daily_counts[daily_counts['weekday'].isin(non_mandatory_days)]['unique_user_count'].mean()

    # Attendance percentages
    try:
        total_employees = int(total_employees_input)
        percent_daily = (avg_daily / total_employees * 100)
        percent_mandatory = (avg_mandatory / total_employees * 100)
        percent_non_mandatory = (avg_non_mandatory / total_employees * 100)
    except:
        percent_daily = None
        percent_mandatory = None
        percent_non_mandatory = None

    # User breakdown for mandatory days (summed)
    mandatory_attendance = unique_daily[unique_daily['weekday'].isin(mandatory_days)]
    mandatory_summary = mandatory_attendance.groupby('User').size().reset_index(name='Mandatory_Days_Total')

    # Total attendance per user
    total_attendance = unique_daily.groupby('User').size().reset_index(name='Total_Attendance')

    # Compliance check (>=8 or >=4 based on user type)
    compliance_counts = unique_daily.groupby(['User', 'month']).size().reset_index(name='attendance_days')
    compliance_summary = compliance_counts.groupby('User')['attendance_days'].sum().reset_index()
    compliance_summary['Compliant'] = compliance_summary.apply(
        lambda row: row['attendance_days'] >= 4 if row['User'] in low_req_users else row['attendance_days'] >= 8,
        axis=1
    )

    # Merge all summaries with total attendance placed between Mandatory_Days and Compliant
    final_summary = pd.merge(mandatory_summary, total_attendance, on='User', how='left')
    final_summary = pd.merge(final_summary, compliance_summary[['User', 'Compliant']], on='User', how='left')

    # Compliance percentage
    percent_compliant = (final_summary['Compliant'].sum() / len(final_summary) * 100) if len(final_summary) > 0 else None

    # Results Display
    st.subheader("📈 Summary Statistics")
    st.write(f"**Average Daily Attendance:** {avg_daily:.2f}")
    st.write(f"**Average Mandatory Days Attendance ({', '.join(mandatory_days)}):** {avg_mandatory:.2f}")
    st.write(f"**Average Non-Mandatory Days Attendance ({', '.join(non_mandatory_days)}):** {avg_non_mandatory:.2f}")
    if percent_compliant is not None:
        st.write(f"**% of Users Compliant:** {percent_compliant:.1f}%")
    if percent_daily is not None:
        st.write(f"**% Daily Attendance:** {percent_daily:.1f}%")
        st.write(f"**% Mandatory Days Attendance:** {percent_mandatory:.1f}%")
        st.write(f"**% Non-Mandatory Days Attendance:** {percent_non_mandatory:.1f}%")

    st.subheader(f"👤 Per-User Mandatory Days ({', '.join(mandatory_days)}) Attendance, Total Attendance, and Compliance")
    st.dataframe(final_summary)

    
else:
    st.info("Please upload a CSV file to begin analysis.")