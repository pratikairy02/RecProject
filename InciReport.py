import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Load and preprocess the data
df = pd.read_excel('inci.xlsx')

# Clean column names
df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\xa0', ' ', regex=False)

# Rename columns for easier access
rename_mapping = {
    'Time (AM or PM)': 'Incident Time',
    'Type of incident  *Must Call Police for asterisked/bold violations': 'Incident Type',
    'Legal Name of Patron (1) involved (put "Unknown" if unable to identify)': 'Patron 1 Name',
    'Patron (1) Email Address': 'Patron 1 Email',
    'Legal Name of Patron (2) involved (put "Unknown" if unable to identify)': 'Patron 2 Name',
    'Patron (2) Email Address ': 'Patron 2 Email',
    'Additional patron(s) and/or witnesses and contact information': 'Additional Contacts',
    'Detailed description of incident (including activity at time of incident). Please give as much information as possible. Example: If a silver MacBook Pro was reported stolen, please describe the it...': 'Description',
    'Action Taken': 'Action Taken',
    'Employee completing this form': 'Form Employee'
}
df = df.rename(columns=rename_mapping)

# Standardize time format
def standardize_time(time_str):
    try:
        if pd.isnull(time_str):
            return 'Unknown'
        time_str = time_str.strip().lower()
        if 'am' in time_str or 'pm' in time_str:
            return pd.to_datetime(time_str, format='%I:%M%p').strftime('%H:%M:%S')
        elif '-' in time_str:
            return 'Unknown'
        else:
            return pd.to_datetime(time_str, format='%H:%M').strftime('%H:%M:%S')
    except:
        return 'Unknown'

df['Standardized Incident Time'] = df['Incident Time'].apply(standardize_time)
df['Incident Hour'] = pd.to_datetime(df['Standardized Incident Time'], format='%H:%M:%S', errors='coerce').dt.hour
df['Incident Hour'] = df['Incident Hour'].fillna(-1)

# Ensure 'Date' column is in datetime format
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df['Day of Week'] = df['Date'].dt.day_name()

# Create time range categories
def time_range(hour):
    if hour < 0:
        return 'Unknown'
    elif 0 <= hour < 6:
        return '12am-6am'
    elif 6 <= hour < 9:
        return '6am-9am'
    elif 9 <= hour < 12:
        return '9am-12pm'
    elif 12 <= hour < 15:
        return '12pm-3pm'
    elif 15 <= hour < 18:
        return '3pm-6pm'
    elif 18 <= hour < 21:
        return '6pm-9pm'
    else:
        return '9pm-12am'

df['Time Range'] = df['Incident Hour'].apply(time_range)

# Get unique incident types for dropdown options
incident_types = df['Incident Type'].dropna().unique()

# Create the Dash layout
app.layout = html.Div(style={'textAlign': 'center', 'padding': '20px'}, children=[
    html.H1("Incident Data Dashboard", style={'color': '#007BFF'}),
    
    # Dropdown for selecting incident types
    html.Div([
        dcc.Dropdown(
            id='incident-type-dropdown',
            options=[{'label': 'All Types', 'value': 'All'}] + [{'label': it, 'value': it} for it in sorted(incident_types)],
            value='All',
            style={'width': '50%', 'padding': '3px'}
        )
    ], style={'margin-bottom': '20px'}),
    
    dcc.Graph(id='total-incidents-graph', style={'height': '400px'}),
    dcc.Graph(id='incident-types-count-graph', style={'height': '400px'}),
    dcc.Graph(id='incident-pie-graph', style={'height': '400px'}),
    dcc.Graph(id='incident-hour-graph', style={'height': '400px'}),
    dcc.Graph(id='incident-time-range-graph', style={'height': '400px'}),
    dcc.Graph(id='incident-day-graph', style={'height': '400px'})
])

# Define callback to update graphs
@app.callback(
    [Output('total-incidents-graph', 'figure'),
     Output('incident-types-count-graph', 'figure'),
     Output('incident-hour-graph', 'figure'),
     Output('incident-time-range-graph', 'figure'),
     Output('incident-day-graph', 'figure')],
    [Input('incident-type-dropdown', 'value')]
)
def update_graphs(selected_type):
    filtered_df = df[df['Incident Type'] == selected_type] if selected_type != 'All' else df

    # Total Incidents Count
    total_incidents_fig = px.bar(filtered_df, x=['Total Incidents'], y=[len(filtered_df)], title='Total Incident Count',
                                  color_discrete_sequence=['black'])

    # Incident Types Count
    incident_types_count_df = filtered_df['Incident Type'].str.replace(r'\s*\(.*?\)', '', regex=True).value_counts().reset_index()
    incident_types_count_df.columns = ['Incident Type', 'Count']
    
    incident_types_count_fig = px.bar(incident_types_count_df,
                                       x='Incident Type', y='Count',
                                       title='Incident Types Count',
                                       color='Count',
                                       color_continuous_scale='Viridis')

    # Number of Incidents by Hour
    hour_fig = px.line(filtered_df.groupby('Incident Hour').size().reset_index(name='Count'), 
                       x='Incident Hour', y='Count', title='Number of Incidents Throughout the Day',
                       markers=True)

    # Number of Incidents by Time Range
    time_range_fig = px.histogram(filtered_df, x='Time Range', title='Number of Incidents by Time Range',
                                   color_discrete_sequence=px.colors.qualitative.Set1)
    time_range_fig.update_layout(barmode='group', xaxis_title='Time Range', yaxis_title='Incident Count',
                                  xaxis={'categoryorder': 'total ascending'}, 
                                  plot_bgcolor='rgba(240, 240, 240, 0.95)',
                                  title_font=dict(size=20, color='#333'), 
                                  xaxis_title_font=dict(size=16, color='#555'),
                                  yaxis_title_font=dict(size=16, color='#555'))

    # Number of Incidents by Day of Week
    day_fig = px.histogram(filtered_df, x='Day of Week', title='Number of Incidents by Day of Week',
                            category_orders={'Day of Week': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']},
                            color_discrete_sequence=px.colors.qualitative.Plotly)
    day_fig.update_layout(barmode='group', xaxis_title='Day of Week', yaxis_title='Incident Count',
                          plot_bgcolor='rgba(240, 240, 240, 0.95)',
                          title_font=dict(size=20, color='#333'), 
                          xaxis_title_font=dict(size=16, color='#555'),
                          yaxis_title_font=dict(size=16, color='#555'))

    return total_incidents_fig, incident_types_count_fig, hour_fig, time_range_fig, day_fig

# Pie chart is not affected by the dropdown selection
@app.callback(
    Output('incident-pie-graph', 'figure'),
    [Input('incident-type-dropdown', 'value')]
)
def update_pie_chart(_):
    pie_fig = px.pie(df, names='Incident Type', title='Proportion of Incidents', 
                     hover_data=['Incident Type'], 
                     labels={'Incident Type': 'Type'},
                     color_discrete_sequence=px.colors.sequential.RdBu)
    
    pie_fig.update_traces(hoverinfo='label+value+percent', opacity=0.8)
    return pie_fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
