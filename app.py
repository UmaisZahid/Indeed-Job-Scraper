from scrape import *
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask.helpers import send_file
import io
import signal
import logging


######################################################################################################################
# Useful members #
######################################################################################################################

default_parameters = {
        'search_query':'Graduate Python',
        'location':'London',
        'miles':15,
        'ordered_keywords':"Banking, Finance, Hedge, Python, Fintech, SQL, Analysis, Modelling",
        'exclude_keywords': "Recruitment, Headhunting",
        'title_keywords': "Graduate, Junior",
        'pages':10
    }

heading = '''
### How to use me:

You provide a set of standard input parameters: 
- **Search Query**
- **Location**
- **Miles/Range**

in addition to two non-standard paramaters: 
- **Keywords in Description**: This is a list of keywords to search for in job descriptions provided in order of preference. Job roles are rated based on this ordered list. 
- **Keywords in Title**: A list of keywords to search for in a job _title_ which, if matched for, increase the normalised rating. (Has precedence over "ordered_keywords")
- **Keywords to Exclude**: A list of keywords to search for in a job _title_ which renders the rating of that job zero. E.g. if you really hate roles as a recruiter you would include: "Recruitment" or "Headhunter"
- **Pages**: Number of Indeed pages to search. (Maximum that Indeed provides is 100)

The web scraper searches through all the indeed job listings with those paramaters and returns all the listings ordered by the "rating" metric based on the ordered list of keywords.

You can then download the full dataframe as an excel sheet for convenience. 

**NOTE: Parsing through all job descriptions can take sometime. (up to 30 seconds). **

'''

# Hacky way of allowing downloading
global_df = None

######################################################################################################################
# Creating app instance and designing layout #
######################################################################################################################

# create scrape instance
scraper = scrape()

# better stylesheet
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Create app
app = dash.Dash(external_stylesheets=external_stylesheets)

# assign server instance
server = app.server

# Create layout
app.layout = html.Div(children=[
    dcc.Markdown(heading),
    dbc.Progress(id="progress", value=0, striped=True, animated=True),
    html.Div(children=[
        html.Div(children=[
            html.Div(children=[
                html.Label('Search Query'),
                dcc.Input(id='search_query', value=default_parameters['search_query'], type='text')
            ], className="four columns"),
            html.Div(children=[
                html.Label('Location'),
                dcc.Input(id='location', value=default_parameters['location'], type='text')
            ], className="four columns"),
            html.Div(children=[
                html.Label('Range in miles'),
                dcc.Input(id='range', value=default_parameters['miles'], type='number')
            ], className="four columns"),
        ],className="row",style={'padding': 10}),
        html.Div(children=[
            html.Div(children=[
                html.Label('Keywords in Description'),
                dcc.Input(id='ordered_keywords', value=default_parameters['ordered_keywords'], type='text')
            ], className="four columns"),
            html.Div(children=[
                html.Label('Keywords in Title'),
                dcc.Input(id='title_keywords', value=default_parameters['title_keywords'], type='text')
            ], className="four columns"),
            html.Div(children=[
                html.Label('Keywords to Exclude'),
                dcc.Input(id='exclude_keywords', value=default_parameters['exclude_keywords'], type='text')
            ], className="four columns"),
        ],className="row",style={'padding': 10}),
        html.Div(children=[
            html.Div(children=[
                html.Label('Number of pages to search'),
                dcc.Slider(
                    id="pages",
                    min=1,
                    max=default_parameters['pages'],
                    marks={i: f'{i}' for i in range(1, default_parameters['pages'])},
                    value=5
                )
            ], className="twelve columns"),
            html.Br(),
            html.Br()
        ],className="row", style={'padding': 10}),
        html.Div(children=[
            html.Div(children=[
                html.Button('Find Jobs', id='find_jobs',className="button button-primary")
            ], className="twelve columns"),
        ],className="row", style={'padding': 10}),
        dcc.Loading(
            id="loading",
            children=[
                html.Div(id="results")
            ],
            type="circle",
        ),
        dcc.Interval(id="interval", interval=1000, n_intervals=0),
        html.Div(id='trigger',children=0, style=dict(display='none'))
    ])
])


######################################################################################################################
# Callback Functions #
######################################################################################################################

# Callback to update results table upon button click, if button isn't disabled
@app.callback(
    [Output("results", "children"),
     Output('trigger','children')],
    [Input("find_jobs","n_clicks")],
    [State("search_query", "value"),
     State("location", "value"),
     State("range", "value"),
     State("title_keywords", "value"),
     State("ordered_keywords", "value"),
     State("exclude_keywords", "value"),
     State("pages", "value")]
)
def update_results(n_clicks, query, location, range, title_keywords, ordered_keywords, exclude_keywords, pages):

    # Don't bother updating if the page just opened
    if n_clicks == 0 or n_clicks is None:
        raise PreventUpdate

    # Grab input
    ordered_keywords = [x.strip() for x in ordered_keywords.split(",")]
    exclude_keywords = [x.strip() for x in exclude_keywords.split(",")]
    title_keywords = [x.strip() for x in title_keywords.split(",")]

    # Scraping parameters
    parameters = {
        'search_query': query,
        'location': location,
        'miles': range,
        'ordered_keywords': ordered_keywords,
        'exclude_keywords': exclude_keywords,
        'title_keywords': title_keywords,
        'pages': pages
    }

    # To store in log
    print(parameters)

    # Scrape based on parameters given
    df = scraper.get_scrape(parameters)
    global global_df
    global_df = df

    # Column for data-table
    columns = [
        {"name": i, "id": i} for i in df.columns
    ]

    # Convert data to list of dictionaries
    data = df.iloc[0:10,:].to_dict(orient='records')

    # Results table div
    results_div = html.Div(className="row",children=[
                        html.Div(className="twelve columns",children=[
                            dash_table.DataTable(id="data_output",
                                                 style_as_list_view=True,
                                                 style_header={
                                                     'backgroundColor': 'white',
                                                     'fontWeight': 'bold'
                                                 },
                                                 style_cell={
                                                     'overflow': 'hidden',
                                                     'textOverflow': 'ellipsis',
                                                     'minWidth': '0px',
                                                     'maxWidth': '180px'
                                                 },
                                                 data=data,
                                                 columns=columns
                                                 )])])

    # Div to output to results parent
    output_div = html.Div(className="row",children=[
        dcc.Markdown('''
        
        ### Excerpt of results: 
                        
        '''),
        results_div,
        html.Br(),
        html.A(html.Button("Download Full Data as Excel File",className="button button-primary"),
            id='download-link',
            href="/download_excel/"
        )
    ])

    # Return output div as well as an output value to trigger div to start trigger callback
    return ([output_div],1)


# Callback which checks if button has been triggered already or not. Disables it if so.
@app.callback(
    Output('find_jobs', 'disabled'),
    [Input('find_jobs', 'n_clicks'),
     Input('trigger', 'children')])
def trigger_function(n_clicks, trigger):

    # Grab the id of the element that triggered the callback
    context = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

    # If the button triggered the function
    if context == 'find_jobs':

        # Prevent false disabling at page load
        if n_clicks is None:
            return False
        elif n_clicks > 0:
            return True
        else:
            return False
    else:
        return False    # If scrape completes and signals trigger again



# Hacky way of allowing downloading of file.
# Converts excel file to memory stream and then outputs that using Flask's send_file function.
@app.server.route("/download_excel/")
def download_file():

    global global_df

    # Convert DF to memory stream
    strIO = io.BytesIO()
    excel_writer = pd.ExcelWriter(strIO, engine="xlsxwriter",options={'strings_to_urls': False})
    global_df.to_excel(excel_writer, sheet_name="Jobs",index=False)
    excel_writer.save()
    excel_data = strIO.getvalue()
    strIO.seek(0)

    return send_file(strIO, as_attachment=True,
                     attachment_filename="Excel Output.xlsx", cache_timeout=0)



######################################################################################################################
# Main and sigterm handling #
######################################################################################################################

# Handle termination signal if received by server
def signal_handler(sig, frame):
    logging.logger.info("Termination Signal Received")
    print(f"Signum: {sig}")
    print(f"Frame: \n {frame}")


if __name__ == "__main__":
    app.run_server(debug=False)