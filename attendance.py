import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Office Attendance Analyzer", layout="wide")
st.title("📊 Office Attendance Analyzer")

# Default values for excluded and low-requirement users
default_excluded_users = "Yuval Shir, Ana Pereira, Jose Silva, Yivgeny Romanenko, Itamar Bul"
default_low_req_users = "Silvia Johanna-Benquis-Hes, Oren Hadar, Dean Becker, Moshe Maizels"

uploaded_file = st.file_uploader("Upload the attendance CSV file", type="csv")
exclude_users_input = st.text_area("Exclude Users (comma-separated)", value=default_excluded_users)
low_requirement_users_input = st.text_area("Users with Low Attendance Requirement (comma-separated)", value=default_low_req_users)
total_employees_input = st.text_input("Total Number of Employees (optional)", value="")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Filter for valid entry events
    entry_df = df[(df['Event'] == 'Entry Unlock') & (df['Result'] == 'Granted') & (df['User'].notna())].copy()

    # Handle excluded users
    exclude_users = [u.strip() for u in exclude_users_input.split(',') if u.strip()]
    if exclude_users:
        entry_df = entry_df[~entry_df['User'].isin(exclude_users)]

    # Identify users with lower attendance requirement
    low_req_users = [u.strip() for u in low_requirement_users_input.split(',') if u.strip()]

    # Time conversion
    entry_df['timestamp'] = pd.to_datetime(entry_df['Browser time'], errors='coerce')
    entry_df['date'] = entry_df['timestamp'].dt.date
    entry_df['weekday'] = entry_df['timestamp'].dt.day_name()
    entry_df['month'] = entry_df['timestamp'].dt.to_period('M')

    # Unique user per day
    unique_daily = entry_df.drop_duplicates(subset=['date', 'User'])
    daily_counts = unique_daily.groupby(['date', 'weekday']).size().reset_index(name='unique_user_count')

    # Averages
    avg_daily = daily_counts['unique_user_count'].mean()
    avg_mon_thu = daily_counts[daily_counts['weekday'].isin(['Monday', 'Thursday'])]['unique_user_count'].mean()
    avg_sun_tue_wed = daily_counts[daily_counts['weekday'].isin(['Sunday', 'Tuesday', 'Wednesday'])]['unique_user_count'].mean()

    # Attendance percentages
    try:
        total_employees = int(total_employees_input)
        percent_daily = (avg_daily / total_employees * 100)
        percent_mon_thu = (avg_mon_thu / total_employees * 100)
    except:
        percent_daily = None
        percent_mon_thu = None

    # User breakdown for Mon/Thu (summed)
    mon_thu_attendance = unique_daily[unique_daily['weekday'].isin(['Monday', 'Thursday'])]
    mon_thu_summary = mon_thu_attendance.groupby('User').size().reset_index(name='Mon_Thu_Total')

    # Total attendance per user
    total_attendance = unique_daily.groupby('User').size().reset_index(name='Total_Attendance')

    # Compliance check (>=8 or >=4 based on user type)
    compliance_counts = unique_daily.groupby(['User', 'month']).size().reset_index(name='attendance_days')
    compliance_summary = compliance_counts.groupby('User')['attendance_days'].sum().reset_index()
    compliance_summary['Compliant'] = compliance_summary.apply(
        lambda row: row['attendance_days'] >= 4 if row['User'] in low_req_users else row['attendance_days'] >= 8,
        axis=1
    )

    # Merge all summaries with total attendance placed between Mon_Thu and Compliant
    final_summary = pd.merge(mon_thu_summary, total_attendance, on='User', how='left')
    final_summary = pd.merge(final_summary, compliance_summary[['User', 'Compliant']], on='User', how='left')

    # Compliance percentage
    percent_compliant = (final_summary['Compliant'].sum() / len(final_summary) * 100) if len(final_summary) > 0 else None

    # Results Display
    st.subheader("📈 Summary Statistics")
    st.write(f"**Average Daily Attendance:** {avg_daily:.2f}")
    st.write(f"**Average Monday & Thursday Attendance:** {avg_mon_thu:.2f}")
    st.write(f"**Average Sun/Tue/Wed Attendance:** {avg_sun_tue_wed:.2f}")

    if percent_daily is not None:
        st.write(f"**% Daily Attendance:** {percent_daily:.1f}%")
        st.write(f"**% Monday & Thursday Attendance:** {percent_mon_thu:.1f}%")

    st.subheader("👤 Per-User Monday/Thursday Attendance, Total Attendance, and Compliance")
    st.dataframe(final_summary)

    if percent_compliant is not None:
        st.write(f"**% of Users Compliant:** {percent_compliant:.1f}%")
else:
    st.info("Please upload a CSV file to begin analysis.")