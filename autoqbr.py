import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import logging, requests, csv, re, os, zipfile
from datetime import datetime, timedelta


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API Request functions
def get_tokens():
    try:
        api_token = input("Tell me your API Token: ")
        app_tokens_input = input("Tell me your app(s) token(s), separated by space: ")
        if app_tokens_input.lower() == 'all':
            return api_token, None
        app_tokens = app_tokens_input.split()
        return api_token, app_tokens
    except Exception as e:
        logging.error("Error getting tokens: %s", e)
        return None, None

def get_utc_offset():
    try:
        utc_offset = input("Which timezone do you want to filter the data? (e.g. +00:00, -03:00, +01:00): ")
        if re.match(r"^[+-]\d{2}:00$", utc_offset):
            return utc_offset
        else:
            raise ValueError("Invalid UTC offset format.")
    except ValueError as ve:
        logging.error("Validation error: %s", ve)
        return None

def get_date_period():
    try:
        date_range = input("Which time range do you want the data? (e.g., 2024-01-01/2024-01-31): ")
        start_date, end_date = date_range.split('/')
        return start_date, end_date
    except Exception as e:
        logging.error("Error parsing date period: %s", e)
        return None, None

def format_date_period(start_date, end_date):
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        delta_start = start_date_obj - (datetime.now() - timedelta(days=1))
        delta_end = end_date_obj - (datetime.now() - timedelta(days=1))
        start_days = f"{abs(delta_start.days)}d"
        end_days = f"{abs(delta_end.days)}d"
        return f"-{start_days}:-{end_days}"
    except Exception as e:
        logging.error("Error formatting date period: %s", e)
        return None

def make_api_request(api_token, app_tokens, utc_offset, date_period, dimensions, metrics, filename):
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        app_token_param = ""
        if app_tokens:
            app_token_string = ','.join(app_tokens)
            app_token_param = f"&app_token__in={app_token_string}"
        url = f"https://dash.adjust.com/control-center/reports-service/csv_report?utc_offset={utc_offset}{app_token_param}&reattributed=all&attribution_source=dynamic&attribution_type=all&ad_spend_mode=network&date_period={date_period}&cohort_maturity=immature&sandbox=false&assisting_attribution_type=all&ironsource_mode=ironsource&dimensions={dimensions}&metrics={metrics}&sort=-installs&is_report_setup_open=true"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            with open(filename, 'w') as file:
                file.write(response.text)
            logging.info(f"Data saved to '{filename}'")
            return url  # Return the URL for audit logging
        else:
            logging.error("Failed to fetch data. Status code: %s", response.status_code)
            return None
    except Exception as e:
        logging.error("Error making API request: %s", e)
        return None
    
# Zip file functions
def zip_outputs(output_files, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in output_files:
            if os.path.exists(file):
                zipf.write(file, arcname=os.path.basename(file))
                logging.info(f"Added {file} to {output_zip}")
                os.remove(file)  # This line deletes the file after adding it to the zip
                logging.info(f"Deleted {file} after adding to ZIP")
            else:
                logging.warning(f"File {file} not found and was not added to the ZIP archive.")
    logging.info(f"All specified files are zipped into {output_zip}")

# Plotting functions
def plot_data():
    try:
        if os.path.exists('data_by_month.csv') and os.path.exists('data_by_channel.csv'):
            # Ensure seaborn and matplotlib are configured for plotting
            sns.set_theme(style="whitegrid")
            plt.rc('axes', axisbelow=True)
            
            # Load the data from CSVs
            data_by_month = pd.read_csv('data_by_month.csv')
            data_by_channel = pd.read_csv('data_by_channel.csv')
            
            # Process data for plotting
            top_channels_installs = data_by_channel[~data_by_channel['channel'].str.contains("Organic", case=False)]
            top_channels_installs = top_channels_installs.sort_values(by='installs', ascending=False).head(5)
            top_channels_sessions = data_by_channel[~data_by_channel['channel'].str.contains("Organic", case=False)]
            top_channels_sessions = top_channels_sessions.sort_values(by='sessions', ascending=False).head(5)
            data_by_channel['rejected_attributions'] = data_by_channel['rejected_installs'] + data_by_channel['rejected_reattributions']
            top_channels_rejected_attributions = data_by_channel[~data_by_channel['channel'].str.contains("Organic", case=False)]
            top_channels_rejected_attributions = top_channels_rejected_attributions.sort_values(by='rejected_attributions', ascending=False).head(5)
            data_by_month['month'] = pd.to_datetime(data_by_month['month'], format='%Y-%m')  # Convert month to datetime for proper sorting
            data_by_month.sort_values('month', inplace=True)  # Sort data by month
            data_by_month['month'] = data_by_month['month'].dt.strftime('%b/%y')
            data_by_month['total_attributions'] = data_by_month['installs'] + data_by_month['reattributions']
            data_by_month['percent_installs'] = data_by_month['installs'] / data_by_month['total_attributions'] * 100  # Convert installs to percentage of the total attributions
            data_by_month['percent_reattributions'] = data_by_month['reattributions'] / data_by_month['total_attributions'] * 100  # Convert reattributions to percentage of the total attributions
            data_by_month['organic_installs'] = data_by_month['installs'] * data_by_month['organic_install_rate']
            data_by_month['paid_installs'] = data_by_month['installs'] - data_by_month['organic_installs']

            # PLOT 1: Monthly Installs and Reattributions (Percentage) ----------------------------------------------------------------------------
            # Set the figure size for percentage plot
            plt.figure(figsize=(14, 7))

            # Bar chart for installs (percentage)
            bar1 = sns.barplot(x="month", y="percent_installs", data=data_by_month, color='darkblue', label='Installs')

            # Bar chart for reattributions (percentage), stacked
            bar2 = sns.barplot(x="month", y="percent_reattributions", data=data_by_month, bottom=data_by_month['percent_installs'], color='lightblue', label='Reattributions')

            # Add labels to each section (percentage plot)
            for i in range(len(data_by_month)):
                plt.text(i, data_by_month['percent_installs'][i]/2, f"{data_by_month['percent_installs'][i]:.1f}%", ha='center', va='center', color='white', fontweight='bold')
                plt.text(i, data_by_month['percent_installs'][i] + data_by_month['percent_reattributions'][i]/2, f"{data_by_month['percent_reattributions'][i]:.1f}%", ha='center', va='center', color='black', fontweight='bold')

            # Add legend and move it to avoid overlay (percentage plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (percentage plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('Percentage', fontweight='bold')
            plt.title('Monthly Installs and Reattributions (Percentage)', fontweight='bold')

            # Save the plot as a PNG file (percentage plot)
            plt.savefig('percent_installsxreattributions_by_month.png', bbox_inches='tight')

            # PLOT 2: Monthly Installs and Reattributions (Absolute Values) ----------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for installs (absolute values)
            bar3 = sns.barplot(x="month", y="installs", data=data_by_month, color='darkblue', label='Installs')

            # Bar chart for reattributions (absolute values), stacked
            bar4 = sns.barplot(x="month", y="reattributions", data=data_by_month, bottom=data_by_month['installs'], color='lightblue', label='Reattributions')

            # Add labels to each section (absolute values plot)
            for i in range(len(data_by_month)):
                install_height = data_by_month.iloc[i]['installs']
                reattrib_height = data_by_month.iloc[i]['reattributions']
                total_height = install_height + reattrib_height
                # Label for installs
                plt.text(i, install_height/2, f"{install_height:,.0f}", ha='center', va='center', color='white', fontweight='bold')
                # Label for reattributions
                plt.text(i, install_height + reattrib_height/2, f"{reattrib_height:,.0f}", ha='center', va='center', color='black', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('Count', fontweight='bold')
            plt.title('Monthly Installs and Reattributions (Absolute Values)', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('absolute_installsxreattributions_by_month.png', bbox_inches='tight')

            # PLOT 3: Monthly Paid Installs and Organic Installs (Absolute Values) ----------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for organic installs (absolute values)
            bar5 = sns.barplot(x="month", y="organic_installs", data=data_by_month, color='lightblue', label='Organic Installs')

            # Bar chart for paid installs (absolute values), stacked
            bar6 = sns.barplot(x="month", y="paid_installs", data=data_by_month, bottom=data_by_month['organic_installs'], color='darkblue', label='Paid Installs')

            # Add labels to each section (absolute values plot)
            for i in range(len(data_by_month)):
                org_install_height = data_by_month.iloc[i]['organic_installs']
                paid_install_height = data_by_month.iloc[i]['paid_installs']
                total_height = org_install_height + paid_install_height
                # Label for paid installs
                plt.text(i, org_install_height/2, f"{org_install_height:,.0f}", ha='center', va='center', color='black', fontweight='bold')
                # Label for organic installs
                plt.text(i, org_install_height + paid_install_height/2, f"{paid_install_height:,.0f}", ha='center', va='center', color='white', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('Count', fontweight='bold')
            plt.title('Monthly Paid Installs and Organic Installs (Absolute Values)', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('absolute_paidinstallsxorganicinstalls_by_month.png', bbox_inches='tight')

            # PLOT 4: Monthly Paid Installs (Absolute Values) --------------------------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for paid installs (absolute values)
            bar7 = sns.barplot(x="month", y="paid_installs", data=data_by_month, color='darkblue', label='Paid Installs')

            # Add labels to each section (absolute values plot)
            for i in range(len(data_by_month)):
                paid_install_height = data_by_month.iloc[i]['paid_installs']
                # Label for paid installs
                plt.text(i, paid_install_height / 2, f"{paid_install_height:,.0f}", ha='center', va='center', color='white', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('Count', fontweight='bold')
            plt.title('Monthly Paid Installs (Absolute Values)', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('absolute_paidinstalls_by_month.png', bbox_inches='tight')

            # PLOT 5: Top 5 installs by channel (Absolute Values) --------------------------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for installs by channel (absolute values)
            bar8 = sns.barplot(x="channel", y="installs", data=top_channels_installs, color='darkblue', label='Channel')

            # Add labels to each section (absolute values plot)
            for i, row in enumerate(top_channels_installs.itertuples()):
                label_position = row.installs / 2 if row.installs > 0 else 0.1 * max(top_channels_installs['installs'])
                # Ensure the label is visible even for very small values
                label_text = f"{row.installs:,.0f}" if row.installs > 0 else "<0.1"
                plt.text(i, label_position, label_text, ha='center', va='center', color='white', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Channel', fontweight='bold')
            plt.ylabel('Installs', fontweight='bold')
            plt.title('Top 5 Installs by Channel (Excluding Organic)', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('top_installs_by_channel.png', bbox_inches='tight')

            # PLOT 6: Top 5 sessions by channel (Absolute Values) --------------------------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for sessions by channel (absolute values)
            bar9 = sns.barplot(x="channel", y="sessions", data=top_channels_sessions, color='darkblue', label='Channel')

            # Add labels to each section (absolute values plot)
            for i, row in enumerate(top_channels_sessions.itertuples()):
                label_position = row.sessions / 2 if row.sessions > 0 else 0.1 * max(top_channels_sessions['sessions'])
                # Ensure the label is visible even for very small values
                label_text = f"{row.sessions:,.0f}" if row.sessions > 0 else "<0.1"
                plt.text(i, label_position, label_text, ha='center', va='center', color='white', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Channel', fontweight='bold')
            plt.ylabel('Sessions', fontweight='bold')
            plt.title('Top 5 Sessions by Channel (Excluding Organic)', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('top_sessions_by_channel.png', bbox_inches='tight')

            # PLOT 7: MAUs by month (Absolute Values) --------------------------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Line chart for MAUs by month (absolute values)
            line = sns.lineplot(x="month", y="maus", data=data_by_month, marker='o', color='darkblue', label='MAUs', markersize=8)

            # Add labels to each point on the line plot
            for i, row in enumerate(data_by_month.itertuples()):
                # Position labels above each marker
                plt.text(i, row.maus + 0.02 * max(data_by_month['maus']), f"{row.maus:,.0f}", ha='center', va='bottom', color='black', fontweight='bold')

            # Customize grid lines
            plt.grid(True)
            plt.gca().grid(which='major', axis='y', linestyle='-', linewidth='0.5', color='gray')  # Enable only horizontal lines
            plt.gca().grid(which='major', axis='x', visible=False)  # Disable vertical lines

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('MAUs', fontweight='bold')
            plt.title('MAUs by Month', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('maus_by_month.png', bbox_inches='tight')

            # PLOT 8: Monthly Rejected Installs and Rejected Reattributions (Absolute Values) ----------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for rejected reattributions (absolute values)
            bar10 = sns.barplot(x="month", y="rejected_reattributions", data=data_by_month, color='lightblue', label='Rejected Reattributions')

            # Bar chart for rejected installs (absolute values), stacked
            bar11 = sns.barplot(x="month", y="rejected_installs", data=data_by_month, bottom=data_by_month['rejected_reattributions'], color='darkblue', label='Rejected Installs')

            # Add labels to each section (absolute values plot)
            for i in range(len(data_by_month)):
                rejected_reattributions_height = data_by_month.iloc[i]['rejected_reattributions']
                rejected_installs_height = data_by_month.iloc[i]['rejected_installs']
                total_height = rejected_reattributions_height + rejected_installs_height
                # Label for rejected reattributions
                plt.text(i, rejected_reattributions_height/2, f"{rejected_reattributions_height:,.0f}", ha='center', va='center', color='black', fontweight='bold')
                # Label for rejected installs
                plt.text(i, rejected_reattributions_height + rejected_installs_height/2, f"{rejected_installs_height:,.0f}", ha='center', va='center', color='white', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('Count', fontweight='bold')
            plt.title('Monthly Rejected Attributions', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('absolute_rejected_attributions_by_month.png', bbox_inches='tight')

            # PLOT 9: Rejected Attributions (Installs and Reattributions) by Channel (Absolute Values) ----------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for rejected attributions (absolute values)
            bar12 = sns.barplot(x="channel", y="rejected_attributions", data=top_channels_rejected_attributions, color='darkblue', label='Channel')

            # Add labels to each section (absolute values plot)
            for i, row in enumerate(top_channels_rejected_attributions.itertuples()):
                label_position = row.rejected_attributions / 2 if row.rejected_attributions > 0 else 0.1 * max(top_channels_rejected_attributions['rejected_attributions'])
                # Ensure the label is visible even for very small values
                label_text = f"{row.rejected_attributions:,.0f}" if row.rejected_attributions > 0 else "<0.1"
                plt.text(i, label_position, label_text, ha='center', va='center', color='white', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Channel', fontweight='bold')
            plt.ylabel('Rejected Attributions', fontweight='bold')
            plt.title('Top 5 Rejected Attributions by Channel (Installs + Reattributions)', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('top_rejected_attributions_by_channel.png', bbox_inches='tight')

            # PLOT 10: Monthly Sessions and Revenue Events (Absolute Values) ----------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for revenue events (absolute values)
            bar13 = sns.barplot(x="month", y="revenue_events", data=data_by_month, color='lightblue', label='Revenue Events')

            # Bar chart for sessions (absolute values), stacked
            bar14 = sns.barplot(x="month", y="sessions", data=data_by_month, bottom=data_by_month['revenue_events'], color='darkblue', label='Sessions')

            # Add labels to each section (absolute values plot)
            for i in range(len(data_by_month)):
                revenue_events_height = data_by_month.iloc[i]['revenue_events']
                sessions_height = data_by_month.iloc[i]['sessions']
                total_height = revenue_events_height + sessions_height
                # Label for revenue events
                plt.text(i, revenue_events_height/2, f"{revenue_events_height:,.0f}", ha='center', va='center', color='black', fontweight='bold')
                # Label for sessions
                plt.text(i, revenue_events_height + sessions_height/2, f"{sessions_height:,.0f}", ha='center', va='center', color='white', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('Count', fontweight='bold')
            plt.title('Monthly Sessions and Revenue Events', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('absolute_sessions_revevents_by_month.png', bbox_inches='tight')

            # PLOT 11: Monthly Clicks and Impressions (Absolute Values) ----------------------------------------------------------------------------
            # Set the figure size for absolute values plot
            plt.figure(figsize=(14, 7))

            # Bar chart for revenue events (absolute values)
            bar13 = sns.barplot(x="month", y="clicks", data=data_by_month, color='darkblue', label='Clicks')

            # Bar chart for sessions (absolute values), stacked
            bar14 = sns.barplot(x="month", y="impressions", data=data_by_month, bottom=data_by_month['clicks'], color='lightblue', label='Impressions')

            # Add labels to each section (absolute values plot)
            for i in range(len(data_by_month)):
                clicks_height = data_by_month.iloc[i]['clicks']
                impression_height = data_by_month.iloc[i]['impressions']
                total_height = clicks_height + impression_height
                # Label for revenue events
                plt.text(i, clicks_height/2, f"{clicks_height:,.0f}", ha='center', va='center', color='white', fontweight='bold')
                # Label for sessions
                plt.text(i, clicks_height + impression_height/2, f"{impression_height:,.0f}", ha='center', va='center', color='black', fontweight='bold')

            # Add legend and move it to avoid overlay (absolute values plot)
            plt.legend(title="Metric", loc='upper left', bbox_to_anchor=(1, 1))

            # Adding labels for clarity with bold font (absolute values plot)
            plt.xlabel('Month', fontweight='bold')
            plt.ylabel('Count', fontweight='bold')
            plt.title('Monthly Clicks and Impressions', fontweight='bold')

            # Save the plot as a PNG file (absolute values plot)
            plt.savefig('absolute_clicks_impressions_by_month.png', bbox_inches='tight')
        else:
            logging.error("Data files not found. Ensure API request was successful.")
    except Exception as e:
        logging.error("Error during plotting: %s", e)

if __name__ == "__main__":
    api_token, app_tokens = get_tokens()
    if api_token:
        utc_offset = get_utc_offset()
        if utc_offset:
            start_date, end_date = get_date_period()
            if start_date and end_date:
                date_period = format_date_period(start_date, end_date)
                if date_period:
                    urls = []
                    url1 = make_api_request(api_token, app_tokens, utc_offset, date_period, 'month', 'installs,reattributions,sessions,rejected_installs,rejected_reattributions,organic_install_rate,maus,clicks,impressions,events,revenue_events', 'data_by_month.csv')
                    if url1:
                        urls.append(url1)
                    url2 = make_api_request(api_token, app_tokens, utc_offset, date_period, 'channel', 'installs,reattributions,sessions,rejected_installs,rejected_reattributions', 'data_by_channel.csv')
                    if url2:
                        urls.append(url2)
                    try:
                        plot_data()
                        with open('audit_trail.csv', 'w', newline='') as csvfile:
                            audit_writer = csv.writer(csvfile)
                            audit_writer.writerow(['Request Header', 'Requested URL'])
                            for url in urls:
                                audit_writer.writerow(['API Token: Bearer ' + api_token, url])
                        logging.info("Audit trail saved to 'audit_trail.csv'")
                        # After all processing and plotting:
                        files_to_zip = ['data_by_month.csv', 'data_by_channel.csv', 'audit_trail.csv', 'percent_installsxreattributions_by_month.png', 'absolute_installsxreattributions_by_month.png', 'absolute_paidinstallsxorganicinstalls_by_month.png', 'absolute_paidinstalls_by_month.png', 'top_installs_by_channel.png', 'top_sessions_by_channel.png', 'maus_by_month.png', 'absolute_rejected_attributions_by_month.png', 'top_rejected_attributions_by_channel.png', 'absolute_sessions_revevents_by_month.png', 'absolute_clicks_impressions_by_month.png']
                        zip_outputs(files_to_zip, 'qbr_outputs.zip')
                    except Exception as e:
                            logging.error("Failed during zipping: %s", e)
