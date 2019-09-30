from scrape import *
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask.helpers import send_file
import io

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
# Indeed Job Scraper

### How it works:

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

**NOTE: This bot is quite slow. (~ 8 seconds per page) as it parses through each job listing sequentially.**

'''

# Hacky way of allowing downloading
global_df = None

# create scrape instance
scraper = scrape()

# better stylesheet
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Create app
app = dash.Dash(external_stylesheets=external_stylesheets)

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
        html.Div(id="results"),
        dcc.Interval(id="interval", interval=1000, n_intervals=0),
    ])
])

@app.callback(
    [Output("results", "children")],
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

    df = scraper.get_scrape(parameters)
    global global_df
    global_df = df

    columns = [
        {"name": i, "id": i} for i in df.columns
    ]

    data = df.iloc[0:10,:].to_dict(orient='records')

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

    return [output_div]

# @app.callback([Output("progress","value")],[Input("interval","n_intervals")])
# def update_progress(n):
#     if scraper.loading == False:
#         raise PreventUpdate
#     else:
#         return scraper.progress


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


if __name__ == "__main__":
    app.run_server(debug=True)