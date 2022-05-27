#%%Modules
from dash import Dash, html, dcc, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate

import dash_bootstrap_components as dbc

import pandas as pd
import plotly.express as px

from datetime import datetime

import base64
import io

import plotly.io as pio
#import plotly.express as px
pio.renderers.default='browser'


#Import Class
from secdata import SecFactsDownloader

#%%Util Functions


def preprocess_df(df):
    
    '''A data pipeline that renders our dataframe more easy to handle'''
    
    import pandas as pd
    
    def lighten_df(df):
        '''Keep only the bare minimum of our dataframe'''
        
        keep_only_columns = ['end', 'Label', 'Entity', 'Value', 'Year' ]
        
        return df[keep_only_columns]
    
    #Just a rename so that values column appears in a more readable way in the plots
    df["Value"] = df["val"]
    
    #The end of reporting period as a datetime (from string)
    df["end"] = pd.to_datetime(df["end"],format = "%Y-%m-%d")
    
    #Since it's a date, we can easily extract the year as integer
    df["Year"] = df["end"].dt.year
    
    #I noticed that whenever 'frame' column is empty, the figure reported covers previous quarters (for comparison with current)
    df = df.copy().loc[(~pd.isna( df["frame"] ))]
    
    #And we only want quarterly data
    #Unfortunately, 4th quarter's reports contain amount that regard a whole year
    df = df.loc[( df["frame"].str.contains("Q[123]") )]
    
    return lighten_df(df)

def common_values_based_on_a_group(fin_df , common_values_from = "Label", where_groups_lie = "Entity"):

    '''
    Built to return all Label of reported facts that are common among the entities.
    
    E.g. 
    if Company A reports a fact named 'Other Liabilities, Current', 
    but Company B does not have such an account on their Balance Sheet,
    Then 'Other Liabilities, Current' is not a dimension under which we can compare the two companies.
    Thus, it need to be removed.
    
    This function detects the facts that need to stay.
    
    But it can be used in a more generic way.
    
    For example, it can return all common reporting periods ('common_values_from' argument) among companies ('where_groups_lie' argument) 
    or
    all common frames (CY2009Q2I, CY2016Q1I, etc.) among forms (10-Q, 10-K, etc.)
    and so on...
    
    '''    
    
    groups = fin_df[where_groups_lie].unique()    

    for g,group in enumerate(groups):
        
        uniques_of_group = fin_df.loc[fin_df[where_groups_lie] == group,common_values_from].unique().tolist()
    
        #If first iteration
        if g == 0:
            
            common_elements = uniques_of_group
            
        #Otherwise, find only commono elements
        else:
            
            common_elements = list(set(common_elements).intersection(uniques_of_group))
    
    return common_elements



#%%Global Variables - not changing throughout session

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]) # external_stylesheets=external_stylesheets)

on_development = True
on_debug_mode = True
allow_download = True


#%%App Constants

#We need to start from somewhere - assets is a feature everyone will be reporting
starting_x = "Assets"
starting_y = "Assets"

plotting_template = "plotly_white"

  
#Initiate Downloader
my_downloader = SecFactsDownloader("my_email@my_domain.com")

#This will check whether there is any file containing the CIKs
#Otherwise it will download them
available_coms_to_download = my_downloader.fetch_companies_info(return_dataframe = True)

# = my_downloader.sec_companies_info
companies = available_coms_to_download()['title'].unique()


# Main title of the whole page
dash_title = "SEComPair"

my_font = '"Poppins","Poppins ExtraBold"' #'"Courier", "Courier New", "Lucida Console", monospace'


download_button_as_csv_style={
        'width': '30%', 
        'color':'white',
       'background-color':'#08c4d1', 
       'border': '4px solid #dfe8e6',
       'position':'relative',
       'top':'70%',
       'left':'35%',
       'border-radius': '10px',
       'font-family': my_font
       }


collapsable_sections_style = {
    'text-align':'center', 
    'color':'white',
    'fontSize': '110%', 
    'font': my_font,
    'border-radius': '10px',
    'background-color' : '#612140', #'#afc3e0',
    'border': '4px solid #098a8f'
    }

#d9a5c0
header_style = {'font-family': my_font,
        'fontSize': '300%', 
        'color':'white',
        'height':'20%',
        'background-color' : '#2F3B60',#'#abcfc3', 
        'text-align':'center',
        'border-radius': '10px',
        'border': '4px solid #dfe8e6',
        'float': 'center'#, 'display': 'inline-block'
}

collapse_buttons_color = '#0cabf5'

feature_dropdown_style = {'color' :'black'}

info_button_style = {'float': 'right', 
                     'display': 'inline-block', 
                     'border': '4px solid #ebe1e1',
                     'border-radius': '10px',
                     'font-family': my_font,
                     #'fontSize': '300%', 
                     #'color':'white',
                     'background-color' : '#057275'
                     }

info_text = '''
This app was built by [Costavul](https://www.youtube.com/channel/UC2FiYXHqkLwd2XO3M64-CPw) using the Securities and Exchange Commision's (SEC) [API](https://www.sec.gov/developer) to fetch Quarterly and Annual Reports (10-Qs, 10-Ks, etc.) data filed to the SEC.\n 
Its purpose is to enable stakeholders to easily gain:
    1.access and
    2.insights from 
the **data existing** in the SEC's **EDGAR database**. 
It is free to use and modify.
'''

disclaimer_text ='''
According to SEC's [Fair Access Policy](https://www.sec.gov/os/accessing-edgar-data), the **current max request rate** is 10 requests/second.\n

To avoid server overloading by botnets, the API requires a user agent (in other words the e-mail address) of each person requesting data.

**No record** of the **user agents** provided to the app **is kept**.

'''

#%%UI components

#The title of the dashboard


info_button = html.Div([
          dbc.Button(
             html.I(className="bi bi-info-circle-fill me-2"), 
             id="popover-bottom-target", 
             color="info",
             style = info_button_style
             ),
         
         dbc.Popover(
             [
                 dbc.PopoverHeader("About this App"),
                 dbc.PopoverBody(dcc.Markdown(info_text)),
                 dbc.PopoverHeader("Disclaimer"),
                 dbc.PopoverBody(dcc.Markdown(disclaimer_text)),
                 
                 ],
             id = "popover",
             target = "popover-bottom-target",
             placement = "bottom",
             is_open = False,
             offset="50,20"
             )
         
         ] )


header = dbc.Row(
    children = [html.Header(dash_title, 
                        style = {
                            'display': 'inline-block', 
                            'float': 'right'
    }), info_button ],
                     style=header_style)


#header_section = html.Div([ header, info_modal ] )



upload_from_previous_run = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Or Drag and Drop or ',
            html.A('Select CSV File'),
            ' From Previous Run'
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'font-family': my_font,
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Div(id='output-data-upload'),
])



companies_chosen = dcc.Dropdown(
    companies,
    placeholder = "Companies to Compare",
    multi=True,
    id = "choose-companies",
    style={'width': '57%',
           'font-family': my_font,
           'color':'black',
           'height' : "10%" , 
           'display': 'inline-block', 
           'float': 'right'}
)

user_credentials = dcc.Input(id='user-credentials',
                             type="text",
                                placeholder ='Your Email - necessary for the SEC API',
                                style={'width': '35%',  'height' : "10%" , 'float': 'left' ,'display': 'inline-block'}
                                )

fetch_scenario = html.Div([user_credentials, companies_chosen])


fetch_from_edgar_section = html.Div(
    [
        dbc.Button(
            "Fetch from SEC Edgar",
            id="collapse-button",
            className="mb-3",
            color="black",
            n_clicks=0,
            style={'background-color':collapse_buttons_color, 'color' : 'white'}
        ),
        dbc.Collapse(
            fetch_scenario,
            id="collapse",
            is_open=False,
        ),
    ]
)


load_from_previous_run_section = html.Div(
    [
        dbc.Button(
            "Load from Previous Run's CSV",
            id="collapse-button2",
            className="mb-3",
            color="primary",
            n_clicks=0,
            style={'background-color':collapse_buttons_color}
        ),
        dbc.Collapse(
            upload_from_previous_run,
            id="collapse2",
            is_open=False,
        ),
    ]
)

load_button = html.Button('Load Data', 
                          id='load-data', 
                          n_clicks=0, 
                          style = {"background-color":"powderblue"})#, style={'width': '10%', 'height' : "5%" , 'float': 'left' ,'display': 'inline-block'}),

setup = html.Div( [ fetch_from_edgar_section, html.Br(), html.Br(), load_from_previous_run_section ,  load_button] )

setup_ribbon = html.Details(
    
    [html.Summary("Load Data", style = {'font-family': my_font}), setup],
    
    id = "Setup_Ribbon",
    
    style = collapsable_sections_style
    
    )


x_dropdown = html.Div(
            dcc.Dropdown(
                
                ["X"],#df['Label'].unique(),
                
                starting_x,
                id='crossfilter-xaxis-column',
                placeholder = 'Select X',
                style = feature_dropdown_style
            )
)

y_dropdown = dcc.Dropdown(
    
    ["Y"],#df['Label'].unique(),
    
    starting_y,
    placeholder = 'Select Y',
    
    id='crossfilter-yaxis-column',
    
    style = feature_dropdown_style
)



x_scale = dcc.RadioItems(
            ['Linear', 'Log'],
            'Linear',
            id='crossfilter-xaxis-type',
            labelStyle={'display': 'inline-block', 'marginTop': '5px'}
        )

y_scale = dcc.RadioItems(
            ['Linear', 'Log'],
            'Linear',
            id='crossfilter-yaxis-type',
            labelStyle={'display': 'inline-block', 'marginTop': '5px'}
        )


x_side = html.Div(children = [
    x_dropdown,    
    #X Axis Feature Scale
    x_scale
    ],
    style={'width': '49%', 'float': 'right', 'display': 'inline-block'}
)

y_side = html.Div(children =[
        y_dropdown ,
        
        #Y Axis Feature Scale
        y_scale
        
    ], 
    style={'width': '49%',  'display': 'inline-block'}
    )

feature_tuning_section = html.Div(children = [x_side, y_side] )



feature_tuning_collapsible_section = html.Details(
    
    [html.Summary("Features", style = {'font-family': my_font}),
    feature_tuning_section],
    id = "Features_Selection_Details",
    
    style = collapsable_sections_style
    
    )

main_plot_of_averages = html.Div([
    
    dcc.Graph(
        id='crossfilter-indicator-scatter',
        
        hoverData={'points': [{'hovertext': "Random Company"} ]} #, 'customdata': [0] * no_of_entities 
    
    )
    
], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20'})

time_series_plots = html.Div([
        dcc.Graph(id='x-time-series'),
        dcc.Graph(id='y-time-series'),
    ], style={'display': 'inline-block', 'width': '49%'})


years_wanted = html.Div(
        dcc.RangeSlider(
        min = 2008,#df['Year'].min(),
        max = 2022,#df['Year'].max(),
        step= 1 ,
        id='crossfilter-year--slider',
        value=[2008,2022],#[df['Year'].min(), df['Year'].max()],
        marks= { str(year) : {"label":str(year), "style" :{"transform": "rotate(45deg)"}} for year in range(2008,2022)} #{ str(year) : {"label":str(year), "style" :{"transform": "rotate(45deg)"}} for year in df['Year'].unique()}
    ), 
    style={'width': '49%', 'padding': '0px 20px 20px 20px' })




download_section = html.Div(
    [
        html.Button("Download Data as CSV", 
                    id="btn_csv",
                    style = download_button_as_csv_style
                    ),
        dcc.Download(id="download-dataframe-csv"),
        
    ] 
    
)

project_description = "Hello World"



about_section = html.Details(
    
    [html.Summary("About", style = {'font-family': my_font}),
     html.Div(project_description, style = {'font-family': my_font, "color": "white"} )
    ],
    id = "About",
    
    style = {'text-align':'center', 
             'fontSize': '110%',
             
             'background-color' : '#afc3e0','border': '4px solid #d9a5c0'}
    
    )



#%%App Interface

app.layout = html.Div([
    
    #header_section,
    
    header,
    
    setup_ribbon, 
    
    #info_modal,
    
    #upload_from_previous_run,

    #info_section,

    main_plot_of_averages,
    
    time_series_plots,

    years_wanted,
    
    feature_tuning_collapsible_section,
    
    download_section,
    
    # Our base - a table full of fin data
    dcc.Store(id='memory-output',  storage_type  = 'memory', data = 'dict'),
    
    dcc.Store(id = 'random_colors_assigned', storage_type  = 'memory', data = 'dict'),
    
    dcc.Store(id = 'available_features', storage_type  = 'memory', data = 'list')
    
    #dcc.Store(id = 'number_of_clicks', storage_type  = 'memory', data = 'number ')
])

# @app.callback(
    
#     Output('number_of_clicks', 'data'),
#     Input('load-data','n_clicks')
#     )
# def count_clicks(n_clicks):

#%%Server    


@app.callback(Output('popover', 'is_open'),
              
              [Input('popover-bottom-target', 'n_clicks')],
              
              [State('popover','is_open')]
              
              )
def toggle_popover(n,is_open):
    
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("collapse", "is_open"),
    [Input("collapse-button", "n_clicks")],
    [State("collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("collapse2", "is_open"),
    [Input("collapse-button2", "n_clicks")],
    [State("collapse2", "is_open")],
)
def toggle_collapse2(n, is_open):
    if n:
        return not is_open
    return is_open


#Useful to read  CSVs

def parse_contents(contents, filename):
    
    content_type, content_string = contents[0].split(',')

    decoded = base64.b64decode(content_string)
    
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df_from_csv = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
            
            return df_from_csv
        else:
            print("Not a csv")
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])


#Our Base for everything -- we can either download it, load it or both
@app.callback(
    #We want the callback to update the child property 'data' of placeholder memory-update
    Output('memory-output', 'data'),
    
    #Bearing in mind that:
        #The respective action button is pressed
    Input('load-data','n_clicks'),
        #Some companies are selected from the dropdown for download
    Input('choose-companies', 'value'), 
        #The user-agent provided on the text input
    Input('user-credentials', 'value'),
        #And/or the content of a loaded csv file
    Input('upload-data', 'contents'),
        #And its filename
    State('upload-data', 'filename')
    )
def loadData(n_clicks, companies, credentials, upload_data, file):
    
    #changed_id = [p['prop_id'] for p in callback_context.triggered][0]
    button_pressed = callback_context.triggered[0]['prop_id'] == 'load-data.n_clicks'
    
    
    #print("upload-data",upload_data)
    #print("Hi")
    
    #print("Change id", changed_id)
    #print("Context",callback_context.triggered)
    # print("companies", companies)
    # print("companies", type(companies))
    # print("credentials", credentials)
    
    #print("credentials", type(credentials))
    #print("Wanted", callback_context.triggered[0]['prop_id'])
    
    if button_pressed : #n_clicks > 0:
        
        if (credentials is not None) & (companies is not None)  :
            
            print("Inside the download attempt")
            
            #Import Class
            from secdata import SecFactsDownloader
                    
            #Initiate Downloader
            my_downloader = SecFactsDownloader(credentials)
            
            #print("My Downloader", type(my_downloader))
            
            companies_info = my_downloader.fetch_companies_info(return_dataframe = True) #sec_companies_info
            companies_info = companies_info()

            #print("companies_info", (companies_info))
            #print("companies_info type", type(companies_info))
            
            ciks_wanted = [c for c in companies_info.loc[companies_info["title"].isin(companies)]["cik_str"].unique()]
            
            #print("ciks_wanted", ciks_wanted )
            print("starting download")
            data = my_downloader.fetch_facts(ciks_wanted)
            print("Finished download")
            
            
            downloaded_data = preprocess_df(data)
            print("Downloaded Data Columns", downloaded_data.columns)
            
        else:
            #print("Inside the LOAD attempt")
            #print("Loading")
            #data = pd.read_csv("df_deb.csv")
            #print("Loaded")
            downloaded_data = None#preprocess_df(data)
            
        #print("Shape", data.shape)
        
        if upload_data is not None:
            
            print("We have data")
            #print("Upload data", upload_data)
            
            uploaded_df = parse_contents(upload_data, file[0])
            #uploaded_df = pd.read_csv("C:\\Users\\kvoul\\Downloads\\Secdata_Downloaded_at_07_05_2022 14.13.52.csv")
            
            print("Downloaded Data Columns", uploaded_df.columns)
            
            #print("file", file )
            
        else:
            
            uploaded_df = None
            
            print("No Upload data")
            
    else:
        raise PreventUpdate
        
    
    #print("Type of Data", type(data))
    
    if (downloaded_data is not None) & (uploaded_df is not None):
        print("Appending one with the other")
        data = downloaded_data.append(uploaded_df)
        
    elif  (downloaded_data is not None) & (uploaded_df is None):
        print("Only downloaded data found")
        data = downloaded_data
        
    elif (downloaded_data is None) & (uploaded_df is not None):
        print("Only uploaded data found")
        
        data = uploaded_df
    else:
        
        print("You gotta choose something")
        
        raise PreventUpdate
    
    #Keep only these columns to keep it lite
    data = data[['end', 'Label', 'Entity', 'Value', 'Year']]
    
    #Turn it into a dictionary so that we can circulate it between the components
    #Unfortunately, dash does not support dataframes as at May 2022
    data = data.reset_index().to_dict()
    #print("Type of Data", type(data))
    
    return data 


@app.callback(
    
    [Output('crossfilter-year--slider', 'min'),
     Output('crossfilter-year--slider', 'max'),
     Output('crossfilter-year--slider', 'value'),
     Output('crossfilter-year--slider', 'marks')],
    
    [Input('memory-output', 'data')]
    
    )
def updateRangeSlider(df):
    
    #Here, df is a dictionary
    years = [y for y in set(df["Year"].values())]
    
    specific_marks = { str(year) : {"label":str(year), "style" :{"transform": "rotate(45deg)"}} for year in years}
    
    
    return [min(years), max(years), [min(years), max(years)] , specific_marks ]


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn_csv", "n_clicks"),
        #What our placeholder memory-output contains
    Input('memory-output','data'),
    prevent_initial_call=True, #Or do not run without any click
)
def download_for_user(n_clicks, df):
    
    #Update a local variable for easier reference and readability
    button_pressed = callback_context.triggered[0]['prop_id'] == 'btn_csv.n_clicks'
    
    if button_pressed:
        
        df_ = pd.DataFrame(df)
        
        csv_filename = "Secdata_Downloaded_at_" +datetime.now().strftime("%d_%m_%Y %H.%M.%S") + ".csv"
        
        return dcc.send_data_frame(df_.to_csv, csv_filename)
    
    else:
        raise PreventUpdate



@app.callback(
    Output('crossfilter-xaxis-column','options' ),
    Input('memory-output','data')#,
    )
def extract_available_features_for_x(df):
    
    common_elements = common_values_based_on_a_group( fin_df = pd.DataFrame(data = df), common_values_from="Label", where_groups_lie = "Entity" )
    
    #common_elements = common_elements.sort()
    
    return common_elements


@app.callback(
    Output('crossfilter-yaxis-column','options' ),
    Input('memory-output','data')#,
    )
def extract_available_features_for_y(df):
       
    common_elements = common_values_based_on_a_group( fin_df  = pd.DataFrame(data = df), common_values_from="Label", where_groups_lie = "Entity" )
    
    return common_elements
    

@app.callback(
    Output('random_colors_assigned','data' ),
    Input('memory-output','data')#,
    #Input('load-data','n_clicks')
    )
def random_colors(df): #n_clicks):
    
    def generate_color_per_entity(df):

        no_of_entities = len(df["Entity"].unique())

        plotly_colors = [
            '#1f77b4',  # muted blue
            '#ff7f0e',  # safety orange
            '#2ca02c',  # cooked asparagus green
            '#d62728',  # brick red
            '#9467bd',  # muted purple
            '#8c564b',  # chestnut brown
            '#e377c2',  # raspberry yogurt pink
            '#7f7f7f',  # middle gray
            '#bcbd22',  # curry yellow-green
            '#17becf'   # blue-teal
        ]
        
        from random import sample
        random_colors = sample(plotly_colors,no_of_entities)
        
        random_colors_assigned = {df["Entity"].unique()[c]:random_colors[c] for c,color in enumerate(random_colors)}
        
        return(random_colors_assigned)
    
    #button_pressed = callback_context.triggered[0]['prop_id'] == 'load-data.n_clicks'
    
    #print("Button pressed in random colors")
    
    if (df is None) | (isinstance(df,str)) : #| (not button_pressed)  :
        
        raise PreventUpdate
        
    else:
        
        df = pd.DataFrame(data = df)
    
        random_colors_assigned = generate_color_per_entity(df)
        
        return random_colors_assigned

    
        
@app.callback(
    Output('crossfilter-indicator-scatter', 'figure'),
    Input('crossfilter-xaxis-column', 'value'),
    Input('crossfilter-yaxis-column', 'value'),
    Input('crossfilter-xaxis-type', 'value'),
    Input('crossfilter-yaxis-type', 'value'),
    Input('crossfilter-year--slider', 'value'),
    Input('memory-output', 'data'),
    Input('random_colors_assigned','data')#,
    #Input('load-data','n_clicks')
    )
def update_graph(xaxis_column_name, yaxis_column_name,
                 xaxis_type, yaxis_type,
                 year_value, df, random_colors_assigned):
    
    #button_pressed = callback_context.triggered[0]['prop_id'] == 'load-data.n_clicks'
    
    #print("Type of df in scatter plot", type(df))
    
    if (df is None) | (isinstance(df,str)): #| (not button_pressed) :
        
        raise PreventUpdate
        
    else:
        
        df = pd.DataFrame(data = df)
    
        df["Color"] = df["Entity"].map(random_colors_assigned)
            
        low, high = year_value
        
        #print("df.columns",df.columns)
        
        #print("unique labels",df["Label"].unique())
        
        #print("first unique label",df["Label"].unique()[0])
        
        #print("second unique label",df["Label"].unique()[1])
        
        #print("xaxis_column_name",xaxis_column_name,"yaxis_column_name", yaxis_column_name)
        
        #Keep only wanted rows --> filter for Years & Features wanted
        dff = df[(df['Year'] <= year_value[1]) & (df['Year'] >= year_value[0]) & ((df["Label"] == xaxis_column_name)| (df["Label"] == yaxis_column_name))]
    
        #print("shape of dff after filtering", dff.shape )
        
        dff = dff.groupby(["Entity", "Label", "Color"])["Value"].mean().reset_index()
        
        dff_ = dff.pivot(index = ["Entity","Color"], columns = "Label",  values = "Value").reset_index()
        
        dff_["Ratio"] = (dff_[xaxis_column_name] / dff_[yaxis_column_name]) 
        
        dff_["Dummy_Col_for_Size"] = 2
        
        fig = px.scatter(
            data_frame=dff_,
            text="Entity",
            custom_data= ["Ratio", "Color"],
            x=xaxis_column_name ,#dff_[xaxis_column_name],
            y= yaxis_column_name, #dff_[yaxis_column_name],
            hover_name= "Entity", #dff_["Entity"],
            size = "Dummy_Col_for_Size",
            symbol_sequence= dff_.shape[0] * ['x'],
            template = plotting_template,
            color = "Entity",color_discrete_map = random_colors_assigned #dff_["Entity"], 
            )
        
        fig.update_traces(hovertemplate=  xaxis_column_name[:30] + ': %{x} <br>'+ yaxis_column_name[:30] + ': %{y} <br>' + xaxis_column_name[:30] + " / " + yaxis_column_name[:30] + ': %{customdata[0]:.4f}' )
    
        fig.update_xaxes(title=xaxis_column_name, type='linear' if xaxis_type == 'Linear' else 'log')
    
        fig.update_yaxes(title=yaxis_column_name, type='linear' if yaxis_type == 'Linear' else 'log')
    
        fig.update_layout(margin={'l': 40, 'b': 40, 't': 10, 'r': 0}, hovermode='closest')
        
        fig.update_layout(showlegend=False)
        
        return fig



def create_double_time_series(dff, axis_type, title, random_colors_assigned):

    fig = px.scatter(dff, 
                     x='end', 
                     y='Value', 
                     color = "Entity",
                     color_discrete_map = random_colors_assigned, 
                     template = plotting_template)

    fig.update_traces(mode='lines+markers')

    fig.update_xaxes(showgrid=False, title_text = "")

    fig.update_yaxes( title_text = "" , type='linear' if axis_type == 'Linear' else 'log')

    fig.add_annotation(x=0, y=0.85, xanchor='left', yanchor='bottom',
                       xref='paper', yref='paper', showarrow=False, align='left',
                       text=title)

    fig.update_layout(height=225, margin={'l': 20, 'b': 30, 'r': 10, 't': 10})
    
    fig.update_layout(showlegend=False)

    return fig



@app.callback(
    Output('x-time-series', 'figure'),
    Input('crossfilter-indicator-scatter', 'hoverData'),
    Input('crossfilter-indicator-scatter', 'clickData'),
    Input('crossfilter-xaxis-column', 'value'),
    Input('crossfilter-xaxis-type', 'value'),
    Input('memory-output', 'data'),
    Input('random_colors_assigned','data')
    )
def update_x_timeseries(hoverData, clickData, xaxis_column_name, axis_type, df, random_colors_assigned):
    
    #print("Type of df in time series plot", type(df))
    
    if (df is None) or (isinstance(df,str)) :
        raise PreventUpdate
    else:
        df = pd.DataFrame(data = df)
    
        entity_name = hoverData['points'][0]['hovertext']
        
        second_entity_exists = False
    
        if clickData is not None:
            
            second_entity_name = clickData['points'][0]['hovertext']
            second_entity_exists = True
            dff = df[(df['Entity'] == entity_name) | (df['Entity'] == second_entity_name) ]
            
        else:
            second_entity_exists = False
            dff = df[df['Entity'] == entity_name]
        
        dff = dff[dff['Label'] == xaxis_column_name]       
        
        
        title = '<b>{}</b><br>{}'.format(entity_name, xaxis_column_name)
        
        if second_entity_exists:
        
            if second_entity_name != entity_name:
                title = '<b>{} vs {}</b><br>{}'.format(entity_name,second_entity_name ,xaxis_column_name)
        
        return create_double_time_series(dff, axis_type, title, random_colors_assigned)


@app.callback(
    Output('y-time-series', 'figure'),
    Input('crossfilter-indicator-scatter', 'hoverData'),
    Input('crossfilter-indicator-scatter', 'clickData'),
    Input('crossfilter-yaxis-column', 'value'),
    Input('crossfilter-yaxis-type', 'value'),
    Input('memory-output', 'data'),
    Input('random_colors_assigned','data')
    )
def update_y_timeseries(hoverData,clickData, yaxis_column_name, axis_type, df, random_colors_assigned ):
    
    if (df is None) or (isinstance(df,str)) :
        raise PreventUpdate
    else:
        df = pd.DataFrame(data = df)
        entity_name = hoverData['points'][0]['hovertext']
        
        second_entity_exists = False
        
        if clickData is not None:
            
            #print("ClckData Exist")
            second_entity_name = clickData['points'][0]['hovertext']
            second_entity_exists = True
            dff = df[(df['Entity'] == entity_name) | (df['Entity'] == second_entity_name) ]
            
        else:
            second_entity_exists = False
            dff = df[df['Entity'] == entity_name]
            
        dff = dff[dff['Label'] == yaxis_column_name]
        
        
        
        title = '<b>{}</b><br>{}'.format(entity_name, yaxis_column_name)
        if second_entity_exists:
        
            if second_entity_name != entity_name:
                title = '<b>{} vs {}</b><br>{}'.format(entity_name,second_entity_name ,yaxis_column_name)
                
        
        #title = '<b>{}</b><br>{}'.format("", yaxis_column_name)
        
        #print(title)
        
        return create_double_time_series(dff, axis_type, title, random_colors_assigned)


#if __name__ == '__main__':
#    
#    app.run_server(debug=False)
