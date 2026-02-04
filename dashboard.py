import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import os
import dash_bootstrap_components as dbc
from dash import dash, html, dcc, State, Input, Output, callback_context
from dash.exceptions import PreventUpdate


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

cw_data_path = os.path.join(BASE_DIR, "cw_data.csv")
ssb_data_path = os.path.join(BASE_DIR, "ssb_data.csv")
prefix_data_path = os.path.join(BASE_DIR, "correct_countries_prefixes.csv")
country_codes_data_path = os.path.join(BASE_DIR, "country_codes.CSV")

# Vengono caricati i dataframe
cw_score_df = pd.read_csv(cw_data_path, sep = ";")
ssb_score_df = pd.read_csv(ssb_data_path, sep = ";")
prefix_df = pd.read_csv(prefix_data_path, sep = ";")
country_codes_df = pd.read_csv(country_codes_data_path, sep = ";")


# Vengono rinominate le colonne del dataframe dei prefissi per adattarle al merge
prefix_df.rename(columns={'PREFIX': 'QTH', 'COUNTRY': 'Country'}, inplace=True)
country_codes_df.rename(columns={'COUNTRY': 'Country', 'CODE': 'country_code'}, inplace=True)

# Vengono rimossi i duplicati nel dataframe dei prefissi
prefix_df = prefix_df.drop_duplicates(subset='QTH')

def create_dataset_to_work(score_df):
    # Vengono uniti i due dataset in base al QTH (prefisso)
    first_merged_df = pd.merge(score_df, prefix_df, on='QTH', how='left')
    second_merged_df = pd.merge(first_merged_df, country_codes_df, on = 'Country', how='left')
    # Selezione dell'ordine delle colonne
    column_order = ['Call', 'QTH', 'Country', 'country_code'] + [col for col in score_df if col not in ['Call', 'QTH', 'Country']]
    # Vengono riordinate le colonne nel dataframe risultante
    merged_df = second_merged_df[column_order]
    return(merged_df)

def create_merged_dataset_to_work(cw_dataset, ssb_dataset):
    # Viene aggiunta una colonna con l'indicazione della tipologia di contest
    cw_dataset['Contest'] = 'CW'
    ssb_dataset['Contest'] = 'SSB'

    ssb_and_cw_score_df = pd.concat([cw_dataset, ssb_dataset], ignore_index=True)
    return(ssb_and_cw_score_df)


cw_dataset = create_dataset_to_work(cw_score_df)
ssb_dataset = create_dataset_to_work(ssb_score_df)

ssb_cw_dataset = create_merged_dataset_to_work(cw_dataset, ssb_dataset)


# Funzione che calcola la media eliminando i valori nulli
def calculate_mean(df, band):
    df_notnull = df[df[band].notnull()]

    mean_by_year = df_notnull.groupby('Year')[band].mean().reset_index()
    mean_by_year[band] = mean_by_year[band].round(1)

    return mean_by_year

# Funzione che calcola il punteggio medio di ogni Country
def calculate_mean_data_for_country(df, country, y_data):
    data_to_plot = y_data
    df_country = df[df['Country'] == country]
    mean_data_by_year = df_country.groupby('Year')[data_to_plot].mean().reset_index()
    mean_data_by_year[data_to_plot] = mean_data_by_year[data_to_plot].round(1)
    return mean_data_by_year


# Scala di colori personalizzata per la mappa
custom_colorscale = [
    [0.0, '#7d28c3'],  # Viola intenso
    [0.1, '#5030c3'],  # Blu-viola
    [0.2, '#2860c3'],  # Blu intenso
    [0.3, '#2890c3'],  # Blu chiaro
    [0.4, '#37c357'],  # Verde
    [0.5, '#91c337'],  # Verde-giallo
    [0.6, '#f5e056'],  # Giallo
    [0.7, '#f5ae56'],  # Arancione chiaro
    [0.8, '#f57542'],  # Arancione
    [0.9, '#f34544'],  # Rosso-arancione
    [1.0, '#d22b2b']   # Rosso intenso
]

# Riscalamento degli assi:
buffer_percentage = 0.05

# Funzione per ottenere i 'confini' dei continenti
def get_continent_bounds(continent):
    bounds = {
        'World': {'lon': [-180, 180], 'lat': [-90, 90]},
        'Europe': {'lon': [-30, 60], 'lat': [30, 75]},
        'North America': {'lon': [-170, -50], 'lat': [5, 85]},
        'Asia': {'lon': [30, 160], 'lat': [-10, 85]},
        'Africa': {'lon': [-30, 60], 'lat': [-40, 40]},
        'South America': {'lon': [-90, -30], 'lat': [-60, 15]},
        'Oceania': {'lon': [85, 240], 'lat': [-50, 20]}
    }
    return bounds.get(continent, bounds['World'])

# Array che definisce le bande del contest
bands = ['160M', '80M', '40M', '20M', '15M', '10M']

# Funzione che restituisce il nome del Country dato il codice
def find_country_from_code(code, selected_dataset):
    # Casi ambigui da gestire 
    if code == "ITA":
        return "Italy"
    elif code == "ESP":
        return "Spain"
    elif code == "USA":
        return "USA"
    
    country_row = selected_dataset[selected_dataset["country_code"] == code]
    return country_row["Country"].values[0] if not country_row.empty else None

# Template personalizzato per il tema chiaro
pio.templates["plotly_light_soft"] = pio.templates["plotly_white"].update(
    layout=dict(
        paper_bgcolor="#b0b5ba",
        plot_bgcolor="#b0b5ba"
    )
)

############################################################

# Applicazione
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

server=app.server

def welcome_page():
    return dbc.Container([
        html.H1("Welcome to CQ World Wide WPX Contest Dashboard", style={'text-align': 'center', 'margin-top':'70px', 'font-size':'60px'}),
        html.H2("The WPX Contest is based on an award offered by CQ Magazine for working all prefixes. Held on the last weekend of March (SSB) and May (CW), the contest draws thousands of entries from around the world.", style={'text-align': 'center', 'margin-top':'50px'}),
        html.H2("There will be represented data form 2005 to 2024, obtained from the contest official website, using three different dashboards.", style={'text-align': 'center', 'margin-top':'20px'}),
        html.H2("Select data to represent:", style={'text-align': 'center', 'margin-top':'60px'}),
        dbc.Row([
            dbc.Col(dbc.Button("SSB Contest", id='ssb-contest', className="btn-custom btn btn-dark"), width="auto"),
            dbc.Tooltip("Display a dashboard for SSB contest data",target="ssb-contest", placement="bottom", className="tooltip-custom"),
            dbc.Col(dbc.Button("CW Contest", id='cw-contest', className="btn-custom btn btn-dark"), width="auto"),
            dbc.Tooltip("Display a dashboard for CW contest data",target="cw-contest", placement="bottom", className="tooltip-custom"),
            dbc.Col(dbc.Button("SSB and CW", id='ssb-cw', className="btn-custom btn btn-dark"), width="auto"),
            dbc.Tooltip("Direct comparison of both contests records through a simple display in one dashboard ",target="ssb-cw", placement="bottom", className="tooltip-custom"),
        ], justify='center', className="custom-row"),
    ], style={'text-align': 'center','min-width': '1600px'})


app.layout = dbc.Container([
    dcc.Store(id='global-color-map', storage_type='memory'),
    dcc.Store(id='selected-theme', data={'dark_mode': True}),
    dcc.Store(id='selected-template', data='plotly_dark'),
    html.Link(id='theme-link', rel='stylesheet', href='/static/dark.css'),
    dbc.Navbar(
        dbc.Container(
            dbc.Row([
                dbc.Col(
                    dbc.Button(
                        "Homepage",
                        id="btn-home",
                        color="primary",
                        className="btn-custom-home btn btn-dark",
                        style={'margin-left':'200px'},
                    ),
                    width="auto",
                    className="p-0"
                ),
                dbc.Col(
                    html.H1(
                        "Data Analysis for CQ World Wide WPX Contest - by IU1SCQ",
                        className="mb-0 text-center text-nowrap"
                    ),
                    className="p-0 flex-grow-1"
                ),
                dbc.Col(
                    dbc.Switch(
                        id="select-dark-mode",
                        label="Dark mode",
                        value=True,
                        style={'font-size': '30px', 'margin-right':'200px'},
                    ),
                    width="auto",
                    className="p-0"
                ),
            ], align="center", className="g-0 w-100 flex-nowrap"),

            fluid=True,
            className="w-100",
            style={'padding-bottom':'20px', 'padding-top':'20px'},
        ),

        sticky="top",
        className="w-100"
    ),
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content', children=welcome_page())
], fluid=True)

# Callback per tornare alla pagina principale
@app.callback(
    Output('page-content', 'children', allow_duplicate=True),
    Input('btn-home', 'n_clicks'),
    prevent_initial_call=True
)
def go_home(n_clicks):
    if n_clicks:
        return welcome_page()
    return dash.no_update


# Callback per lo switch del tema
@app.callback(
    [Output('selected-theme', 'data'),
     Output('selected-template', 'data')],
    Input('select-dark-mode', 'value')
)
def update_theme_store(dark_mode):
    theme_data = {'dark_mode': dark_mode}
    template = 'plotly_dark' if dark_mode else 'plotly_light_soft'
    return theme_data, template

# Callback che aggiorna il tema
@app.callback(
    Output('theme-link', 'href'),
    Input('selected-theme', 'data')
)
def update_stylesheet(theme):
    dark_mode = theme.get('dark_mode', True)
    if dark_mode:
        return '/static/dark.css'
    else:
        return '/static/light.css'

# Callback che crea la mappa dei colori per i vincitori
@app.callback(
    Output('global-color-map', 'data'),
    Input('winners-table', 'data')
)
def compute_color_map(winners_table):
    if not winners_table:
        raise PreventUpdate
    if isinstance(winners_table, list):
        winners_table = pd.DataFrame(winners_table)
    
    unique_winner_countries = winners_table['Country'].unique()
    vivid_colors = px.colors.qualitative.Vivid
    country_color_map = {
        country: vivid_colors[i % len(vivid_colors)]
        for i, country in enumerate(sorted(unique_winner_countries))
    }
    return country_color_map



########################################################################
# Funzione che crea la dashboard di dei singoli contest
########################################################################
def single_data_dashboard_page(selected_dataset, title_string):        
    unique_years = selected_dataset['Year'].unique()
    merged_mean_df = pd.DataFrame({'Year': unique_years})
    mean_total_QSOs = calculate_mean(selected_dataset, 'QSOs')
    mean_total_WPX = calculate_mean(selected_dataset, 'WPX')

    # Dataset con medie di qso e wpx e anno
    mean_qso_wpx_df = pd.merge(merged_mean_df, mean_total_QSOs, on='Year', how='left')
    mean_qso_wpx_df = pd.merge(mean_qso_wpx_df, mean_total_WPX, on='Year', how='left' )

    # Vengono rappresentate in un linechart le medie dei QSO totali e quelle nelle singole bande
    for band in bands:
        mean_df = calculate_mean(selected_dataset, band)
        merged_mean_df = pd.merge(merged_mean_df, mean_df, on='Year', how='left')        
    merged_mean_df = pd.merge(merged_mean_df, mean_total_QSOs, on='Year', how='left')
    merged_mean_df.rename(columns={'QSOs': 'TotalQSOs'}, inplace=True)


    # Vincitori di ogni anno
    grouped_data = selected_dataset.groupby('Year')
    winners = []

    for year, group in grouped_data:    
        sorted_group = group.sort_values(by='Score', ascending=False)   
        winner = sorted_group.head(1)    
        winners.append(winner)

    winners_table = pd.concat(winners)
    unique_winner_countries = winners_table['Country'].unique()

    # Punteggio massimo per ogni Country
    max_scores_by_country = {}
    for country in unique_winner_countries:
        max_score_for_country = winners_table[winners_table['Country'] == country]['Score'].max()
        max_scores_by_country[country] = max_score_for_country

    max_country_score = max(max_scores_by_country, key=max_scores_by_country.get)
    max_score = max_scores_by_country[max_country_score]

    # QSOs massimi per ogni Country
    max_QSO_by_country = {}
    for country in unique_winner_countries:
        max_QSO_for_country = winners_table[winners_table['Country'] == country]['QSOs'].max()
        max_QSO_by_country[country] = max_QSO_for_country

    max_country_QSO = max(max_QSO_by_country, key=max_QSO_by_country.get)
    max_QSO = max_QSO_by_country[max_country_QSO]

    # WPX massimi per ogni Country
    max_WPX_by_country = {}
    for country in unique_winner_countries:
        max_WPX_for_country = winners_table[winners_table['Country'] == country]['WPX'].max()
        max_WPX_by_country[country] = max_WPX_for_country

    max_country_WPX = max(max_WPX_by_country, key=max_WPX_by_country.get)
    max_WPX = max_WPX_by_country[max_country_WPX]


    # Per il grafico a linee delle bande
    global_y_min = merged_mean_df[['TotalQSOs', '160M', '80M', '40M', '20M', '15M', '10M']].min().min()
    global_y_max = merged_mean_df[['TotalQSOs', '160M', '80M', '40M', '20M', '15M', '10M']].max().max()
    global_y_range = global_y_max - global_y_min
    global_y_min_buffered = global_y_min - buffer_percentage * global_y_range
    global_y_max_buffered = global_y_max + buffer_percentage * global_y_range

    global_x_min = merged_mean_df['Year'].min()
    global_x_max = merged_mean_df['Year'].max()
    global_x_range = global_x_max - global_x_min
    global_x_min_buffered = global_x_min - buffer_percentage * global_x_range
    global_x_max_buffered = global_x_max + buffer_percentage * global_x_range

    # Per l'istogramma dei club quando vengono plottati i QSO
    global_y_min_QSO = 0
    global_y_max_QSO = selected_dataset['Score'].max()
    global_y_QSO_range = global_y_max_QSO - global_y_min_QSO
    global_y_min_QSO_buffered = global_y_min_QSO - buffer_percentage * global_y_QSO_range
    global_y_max_QSO_buffered = global_y_max_QSO + buffer_percentage * global_y_QSO_range

    global_x_min_QSO = 0
    global_x_max_QSO = selected_dataset['QSOs'].max()
    global_x_QSO_range = global_x_max_QSO - global_x_min_QSO
    global_x_min_QSO_buffered = global_x_min_QSO - buffer_percentage * global_x_QSO_range
    global_x_max_QSO_buffered = global_x_max_QSO + buffer_percentage * global_x_QSO_range

    # Per l'istogramma dei club quando vengono plottati i WPX
    global_y_min_WPX = 0
    global_y_max_WPX = selected_dataset['Score'].max()
    global_y_WPX_range = global_y_max_WPX - global_y_min_WPX
    global_y_min_WPX_buffered = global_y_min_WPX - buffer_percentage * global_y_WPX_range
    global_y_max_WPX_buffered = global_y_max_WPX + buffer_percentage * global_y_WPX_range

    global_x_min_WPX = 0
    global_x_max_WPX = selected_dataset['WPX'].max()
    global_x_WPX_range = global_x_max_WPX - global_x_min_WPX
    global_x_min_WPX_buffered = global_x_min_WPX - buffer_percentage * global_x_WPX_range
    global_x_max_WPX_buffered = global_x_max_WPX + buffer_percentage * global_x_WPX_range



    # Per poter fare uno studio sulle categorie si copia il dataframe di partenza
    # e si estraggono le sopracategorie. Si crea cosi' una nuova colonna Category 
    # piu' facilmente utilizzabile
    new_cat_df = selected_dataset.copy()
    new_cat_df['Category'] = new_cat_df['Category'].apply(lambda x: x.split(' ')[0])
    supercat_count_per_year = new_cat_df.groupby(['Year', 'Category']).size().reset_index(name='Count')


    # Conteggio dei partecipanti per ogni Country per il plot della mappa
    country_counts = selected_dataset['country_code'].value_counts().reset_index()
    country_counts.columns = ['country_code', 'count']

    # Conteggio dei vincitori per ogni Country per il plot della mappa
    winner_counts = winners_table['country_code'].value_counts().reset_index()
    winner_counts.columns = ['country_code', 'count']
    
        
    # Componente RadioItems per la selezione della banda
    radio_band = dbc.RadioItems(
        id="select-band",
        options=[        
            {"label": "All", "value": "All"},
            {"label": "160M", "value": "160M"},
            {"label": "80M", "value": "80M"},
            {"label": "40M", "value": "40M"},
            {"label": "20M", "value": "20M"},
            {"label": "15M", "value": "15M"},
            {"label": "10M", "value": "10M"}
        ],
        value="All",
        style={'font-size': '20px'},
        inline = True
    )

    # Componente RadioItems per la selezione del country vincitore
    radio_winner_countries = dbc.RadioItems(
        id="winner-country-radio",
        options=[],
        value=None,
        style={'font-size': '20px'},
        inline=False
    )

    # Componente RadioItems per la selezione del continente da visualizzare nella mappa
    radio_continents = dbc.RadioItems(
        id= "select-continent",
        options=[
            {'label': 'World', 'value': 'World'},
            {'label': 'Europe', 'value': 'Europe'},
            {'label': 'North America', 'value': 'North America'},
            {'label': 'South America', 'value': 'South America'},
            {'label': 'Asia', 'value': 'Asia'},
            {'label': 'Africa', 'value': 'Africa'},
            {'label': 'Oceania', 'value': 'Oceania'}
        ],
        value='World',
        style={'width':'900px', 'margin-left':0, 'font-size': '20px'},
        inline = True
    )

    # Componente Switch per la selezione del tipo di mappa da visualizzare (mondo o continente)
    winner_switch = dbc.Switch(
        id="select-map-type",
        label="All partecipants/Winners",
        style= {'font-size': '20px'},
        value=True
    )

    # Componente Switch per scegliere se visualizzare qso e wpx a confronto o solo wpx    
    enable_qso_switch = dbc.Switch(
        id="enable-qso",
        label="Show mean of QSOs",
        style= {'font-size': '20px'},
        value=True
    )

    # Componente Switch per scegliere se visualizzare in scala logaritmica nel grafico delle categorie    
    logarithmic_scale_switch = dbc.Switch(
        id="logarithmic-scale",
        label="Use logarithmic scale for y axis",
        style= {'font-size': '20px'},
        value=True
    )

    # Componente RadioItems per la selezione del tipo di dato da visualizzare sull'asse x dell'istogramma dei club
    radio_club_x = dbc.RadioItems(
        id="select-club-y",
        options=[        
            {"label": "WPXs", "value": "WPX"},
            {"label": "QSOs", "value": "QSOs"},
        ],
        value="WPX",
        style={'font-size': '20px'},
        inline=True
    )

    # Componente RadioItems per la selezione del tipo di dato da visualizzare sull'asse y dei plot dei vincitori
    radio_winner_y = dbc.RadioItems(
        id="select-winner-y",
        options=[        
            {"label": "WPXs", "value": "WPX"},
            {"label": "QSOs", "value": "QSOs"},
            {"label": "Total score", "value": "Score"}
        ],
        value="WPX",
        style={'font-size': '20px'},
        inline=True
    )

    return dbc.Container([
        dcc.Store(id='selected-data', data=selected_dataset.to_dict('records')),
        dcc.Store(id='country-counts',data=country_counts.to_dict('records')),
        dcc.Store(id='winner-counts', data = winner_counts.to_dict('records')),
        dcc.Store(id='merged-mean-data', data=merged_mean_df.to_dict('records')),
        dcc.Store(id='global-ranges', data={
            'x_min': global_x_min_buffered,
            'x_max': global_x_max_buffered,
            'y_min': global_y_min_buffered,
            'y_max': global_y_max_buffered
        }),
        dcc.Store(id="mean-qso-wpx", data=mean_qso_wpx_df.to_dict('records')),
        dcc.Store(id='supercat', data = supercat_count_per_year.to_dict('records')),
        dcc.Store(id='y-data-to-plot', data='Score'),
        dcc.Store(id='select-winner-country', data = None),
        dcc.Store(id='winners-table', data= winners_table.to_dict('records')),
        dcc.Store(id='winners-QSO-WPX-score', data={
            'max_QSO': max_QSO,
            'max_WPX': max_WPX,
            'max_score': max_score
        }),
        dcc.Store(id='global-ranges-QSO-WPX', data={
            'x_min_QSO': global_x_min_QSO_buffered,
            'x_max_QSO': global_x_max_QSO_buffered,
            'y_min_QSO': global_y_min_QSO_buffered,
            'y_max_QSO': global_y_max_QSO_buffered,
            'x_min_WPX': global_x_min_WPX_buffered,
            'x_max_WPX': global_x_max_WPX_buffered,
            'y_min_WPX': global_y_min_WPX_buffered,
            'y_max_WPX': global_y_max_WPX_buffered
        }),      

        dbc.Row(
            dbc.Col(
                html.H3(f'Data from 2005 to 2024 for {title_string} contest'),
            )
        ),
        # QSO e WPX sulle diverse bande, due linechart affiancati nelle due colonne
        # primo linechart, quello dei qso totali e sulle singole bande
        # secondo linechart, media dei wpx negli anni a confronto con la media dei qso totali
        dbc.Row([            
            dbc.Col([
                html.Div([
                    dbc.Label(
                        "Select band:",
                        html_for="select-band",
                        style={'font-size':'20px', 'margin-right':'7px'}
                    ),
                    radio_band
                ],style={"display": "flex", "alignItems": "center"}),                    
                dcc.Graph(id="band-line-chart")
            ], style={'max-width':1000, 'height':500}),
            dbc.Col([
                enable_qso_switch,
                dcc.Graph(id="wpx-qso-linechart")
            ], style={'max-width':1000, 'height':500})    
        ]),
            
        # vincitori, barchart con scelta tra wpx e qso, colonna che elenca i vincitori
        # negli anni, linechart che mostra i vincitori selezionati
        dbc.Row([            
            dbc.Col([
                html.Div([
                    dbc.Label(
                        "Select y axis:",
                        html_for="select-winner-y",
                        style={'font-size':'20px', 'margin-right':'7px'}
                    ),
                    radio_winner_y
                ],style={"display": "flex", "alignItems": "center"}),                
                dcc.Graph(id='winner-barchart')
            ], style={'max-width':1000, 'height':500, 'margin-top':'100px'}),
            dbc.Col([     
                dbc.Label(
                    "Select winner:",
                    html_for="winner-country-radio",
                    style={'font-size':'20px', 'margin-right':'7px'}
                ),           
                radio_winner_countries,
                ], style={'max-width':'180px', 'margin-top':'150px'}
            ),
            dbc.Col([
                dcc.Graph(id="winner-linechart")
            ], style={'max-width':1000, 'height':500, 'margin-top':'130px'})
        ]),
        
        # rappresentazione dei club
        dbc.Row([
            dbc.Col([
                html.Div([
                    dbc.Label(
                        "Select y axis:",
                        html_for="select-club-y",
                        style={'font-size':'20px', 'margin-right':'7px'}
                    ),
                    radio_club_x
                ],style={"display": "flex", "alignItems": "center"}),
                dcc.Graph(id="club-chart")
            ], style={'max-width':1000, 'height':500, 'margin-top':'100px'}),
            dbc.Col([
                dcc.Graph(id='club-pie')
            ], style={'max-width':1000, 'height':500, 'margin-top':'135px'})
        ]),
        #categorie di partecipazione
        dbc.Row(
            dbc.Col([
                logarithmic_scale_switch,
                dcc.Graph(id= 'category-linechart')
            ], style={'max-width':1000, 'height':500, 'margin-top':'90px'})
        ),
        # mappa del mondo
        dbc.Row([
            dbc.Col([
                winner_switch,
                html.Div([
                    dbc.Label(
                        "Focus on:",
                        html_for="select-continent",
                        style={'font-size':'20px', 'margin-right':'7px'}
                    ),
                    radio_continents
                ],style={"display": "flex", "alignItems": "center"}),                
            ], style={'width':700, 'margin-top':'120px'})
        ]),
        dbc.Row(
            dbc.Col([
                dcc.Graph(id="map-graph", config={"scrollZoom": False})                
            ], style={'width':700, 'margin-top':'20px', 'margin-bottom':'100px'})
        )
    ], fluid=True)


########################################################################
# Tutte le callbacks e funzioni per la dashboard dei singoli contest
########################################################################

# Callback per aggiornare il linechart in base alla selezione della banda
@app.callback(
    Output("band-line-chart", "figure"),
    [Input("select-band", "value"),
     Input('selected-template', 'data')],
    [State("merged-mean-data", "data"),
    State("global-ranges", "data")]
          
)
def update_band_line_chart(selected_band, selected_template, merged_mean_data, global_ranges):
    merged_mean_df = pd.DataFrame(merged_mean_data)
    x_min = global_ranges['x_min']
    x_max = global_ranges['x_max']
    y_min = global_ranges['y_min']
    y_max = global_ranges['y_max']
    color_map = {
        "TotalQSOs": "#E58606",
        "160M": "#ED645A",
        "80M": "#52BCA3",
        "40M": "#5D69B1",
        "20M": "#99C945",
        "15M": "#CC61B0",
        "10M": "#764E9F",
    }
    if selected_band == "All":
        bands_to_plot = ['TotalQSOs','160M', '80M', '40M', '20M', '15M', '10M']
    else:
        bands_to_plot = ['TotalQSOs', selected_band]

    fig_band_line_chart = px.line(
        merged_mean_df,
        x='Year',
        y=bands_to_plot,
        title=f"QSOs in {selected_band} band compared to total QSOs",
        labels={"Year": "Year", selected_band: f"{selected_band}"},
        markers=True,
        template=selected_template,
        color_discrete_map=color_map
    )
    fig_band_line_chart.update_xaxes(title='Year', range=[x_min, x_max])
    fig_band_line_chart.update_yaxes(title='Mean of QSOs', range=[y_min, y_max])
    fig_band_line_chart.update_layout(
        margin=dict(
            l=60,
            r=160,
            t=60,
            b=60,
        )
    )
    return fig_band_line_chart

#callback per la creazione del linechart del confronto media wpx e qso
@app.callback(
    Output("wpx-qso-linechart", "figure"),
    [Input('selected-template', 'data'),
     Input("enable-qso", "value")],
    [State("mean-qso-wpx", "data"),
     State("global-ranges", "data")]
    
)
def update_qso_wpx_linechart(selected_template, enable_qso, mean_df, global_ranges):
    x_min = global_ranges['x_min']
    x_max = global_ranges['x_max']
    y_min = global_ranges['y_min']
    y_max = global_ranges['y_max']
    color_map = {
        "QSOs": "#E58606",
        "WPX": "#2F8AC4"
    }
    if enable_qso:
        data_to_plot = ["WPX", "QSOs"]
    else:
        data_to_plot = ["WPX"]
    fig_qso_wpx_line_chart = px.line(
        mean_df,
        x='Year',
        y=data_to_plot,
        title=f"Comparsion of mean QSOs and WPXs",
        labels={"Year": "Year"},
        markers=True,
        template=selected_template,
        color_discrete_map=color_map
    )
    fig_qso_wpx_line_chart.update_xaxes(title='Year', range=[x_min, x_max])
    fig_qso_wpx_line_chart.update_yaxes(title='Mean of data', range=[y_min, y_max])
    fig_qso_wpx_line_chart.update_layout(
        margin=dict(
            l=60,
            r=160,
            t=60,
            b=60,
        ),
        showlegend=True
    )
    return fig_qso_wpx_line_chart

# Callback per aggiornare l'istogramma sui club
@app.callback(
    Output("club-chart", "figure"),
    [Input("select-club-y", "value"),
    Input('selected-template', 'data')],
    State("selected-data", "data")    
)
def update_club_chart(selected_y, selected_template, selected_dataset):     
    if isinstance(selected_dataset, list):
        data_club = pd.DataFrame(selected_dataset)
    else:
        data_club= selected_dataset.copy()
    
    # Creazione un nuovo campo 'Club Status' per differenziare i membri di un club da quelli che non lo sono.
    # Viene utilizzato il metodo .loc per selezionare tutte le righe e viene creata la colonna 'Club Status'.
    # La funzione lambda controlla se il valore è 'No club' e restituisce 'No Club Member' in quel caso, altrimenti restituisce 'Club Member'.
    data_club.loc[:, 'Club Status'] = data_club['Club'].apply(lambda x: 'No Club Member' if x == 'NO CLUB' else 'Club Member')

    # Aggregazione
    data_club_grouped = (data_club.groupby(["Year", "Club Status"], as_index=False)[selected_y].mean())
    
    # Colori personalizzati per l'istogramma dei club
    color_discrete_map = {
        'No Club Member': "#EFDA3B",
        'Club Member': '#636EFA'
    }

    fig_club_chart = px.line(
        data_club_grouped,
        x='Year',
        y=selected_y,
        color='Club Status',
        title=f"Comparsion on {selected_y} for club members and not members",
        labels={"Year": "Year"},
        markers=True,
        template=selected_template,
        color_discrete_map=color_discrete_map
    ).update_yaxes(title=f"Mean of {selected_y}")      
    return fig_club_chart

# Callback per la generazione del grafico a torta per i club
@app.callback(
    Output("club-pie", "figure"),   
    Input('selected-template', 'data'),
    State("selected-data", "data")    
)
def update_club_pie(template, selected_data):
    df = pd.DataFrame(selected_data)

    df["Club Status"] = df["Club"].apply(
        lambda x: "No Club Member" if x == "NO CLUB" else "Club Member"
    )

    df_pie = (
        df
        .groupby("Club Status")
        .size()
        .reset_index(name="Count")
    )

    fig = px.pie(
        df_pie,
        names="Club Status",
        values="Count",
        title="Club Members vs No Club Members from 2005 to 2024",
        color="Club Status",
        template=template,
        color_discrete_map={
            "Club Member": "#636EFA",
            "No Club Member": "#EFDA3B"
        }
    )
    return fig

# Callback per la scelta del continente da visualizzare nella mappa
@app.callback(
    Output('map-graph', 'figure'),
    [Input('select-continent', 'value'),
    Input("select-map-type", "value"),
    Input('selected-template', 'data')],
    [State('country-counts', 'data'),
    State('winner-counts', 'data'),
    State('selected-data', 'data')]
)
def update_map(selected_continent, selected_type, selected_template, country_counts, winner_counts, selected_dataset):
    if isinstance(selected_dataset, list):
        selected_dataset = pd.DataFrame(selected_dataset)
    if isinstance(country_counts, list):
        country_counts = pd.DataFrame(country_counts)
    if isinstance(winner_counts, list):
        winner_counts = pd.DataFrame(winner_counts)

    bounds = get_continent_bounds(selected_continent)
    if selected_type == True:
        selected_type_of_rapresentation = 'participants'
        type_of_counts = country_counts        
        type_of_counts = type_of_counts.rename(columns={'count': 'participants'})
        color_bar=dict(
            title='',
            orientation='v', 
            yanchor='middle', 
            y=0.5,  
            xanchor='left',  
            x=-0.1,
            len=1
        )        
    else:
        selected_type_of_rapresentation = 'winners'
        type_of_counts = winner_counts                
        type_of_counts = type_of_counts.rename(columns={'count': 'winners'})
        color_bar = dict(
            title='',
            orientation='v', 
            yanchor='middle', 
            y=0.5,  
            xanchor='left',  
            x=-0.1,
            len=1,
            tickvals=[1, 2, 3, 4, 5],
            ticktext=['1', '2', '3', '4', '5']
        )

    # Inserimento di una colonna con il nome del Country
    type_of_counts.loc[:, 'Country'] = type_of_counts['country_code'].apply(lambda code: find_country_from_code(code, selected_dataset))

    map_figure = px.choropleth(
        type_of_counts,
        locations="country_code",
        color=selected_type_of_rapresentation,
        hover_name="Country",
        hover_data= {"country_code" : False},
        template= selected_template, 
        color_continuous_scale=custom_colorscale,
        title=f"Number of {selected_type_of_rapresentation} from 2005 to 2024 per Country"
    ).update_layout(
        margin=dict(
            l=60,
            r=100,
            t=60,
            b=60,
        ),
        height=700,
        width = 1400,
        title_y= 0.95,
        title_x=0.5, 
        coloraxis_colorbar = color_bar,
        geo=dict(
            projection_scale=1,
            center={"lat": (bounds['lat'][0] + bounds['lat'][1]) / 2, "lon": (bounds['lon'][0] + bounds['lon'][1]) / 2},
            lonaxis_range=bounds['lon'],
            lataxis_range=bounds['lat'],
        )
    )
    return map_figure

# Callback per popolare i radio button per la scelta del country vincitore
@app.callback(
    [Output("winner-country-radio", "options"),
     Output("winner-country-radio", "value")],
    Input("winners-table", "data")
)
def update_winner_country_radio(winners_table):
    if not winners_table:
        return [], None
    df = pd.DataFrame(winners_table)
    country_year = (
        df.groupby("Country")["Year"]
        .min()
        .reset_index()
        .sort_values("Year")
    )
    options = [
        {"label": row["Country"], "value": row["Country"]}
        for _, row in country_year.iterrows()
    ]
    value = options[0]["value"]
    return options, value

# Callback per aggiornare i due grafici sui vincitori in base alla scelta del dato da usare sull'asse y
@app.callback(
        Output("y-data-to-plot", "data"),
        Input("select-winner-y", "value")
)
def update_winner_plots(selected_y):
    if selected_y == "WPX":
        y_data_to_plot = "WPX"
    elif selected_y == "QSOs":
        y_data_to_plot = "QSOs"
    else:
        y_data_to_plot = "Score"
    return y_data_to_plot    
    
# Callbacke per aggiornare il grafico barchart dei vincitori
@app.callback(
    Output("winner-barchart", "figure"),
    [Input("y-data-to-plot", "data"),
     Input('selected-template', 'data'),
     Input('global-color-map', 'data')],
    [State('winners-table', 'data')]
)
def update_winner_barchart(selected_y, selected_template, color_map, winners_table):
    if isinstance(winners_table, list):
        winners_table = pd.DataFrame(winners_table)

    winners_figure = px.bar(
        winners_table,
        x='Year',
        y= selected_y,
        color='Country',
        title = "Winner Countries per year",
        color_discrete_map=color_map,
        template= selected_template, 
        hover_data={'Callsign': winners_table["Call"], 'Cat': winners_table["Category"], 'club': winners_table["Club"]}
    ).update_layout(
        xaxis_title='Year',
        yaxis_title=selected_y,
        margin=dict(l=2, r=2, t=40, b=2)
    )
    return winners_figure

# Callback per aggiornare il grafico a linee in base alla scelta del paese (tramite il click sui radio button)
@app.callback(
    Output("winner-linechart", "figure"),
    [Input("winner-country-radio", "value"),
    Input("y-data-to-plot", "data"),
    Input('selected-template', 'data'),
    Input('global-color-map', 'data')],
    [State('selected-data', 'data'),
    State('winners-table', 'data'),
    State('winners-QSO-WPX-score', 'data')]         
)
def update_winner_country_chart(selected_country, y_data, selected_template, color_map, selected_dataset, winners_table, winners_QSO_WPX_score):
    if isinstance(selected_dataset, list):
        selected_dataset = pd.DataFrame(selected_dataset)
    if isinstance(winners_table, list):
        winners_table = pd.DataFrame(winners_table)
    if selected_country:
        country_to_plot = selected_country 
    else:
        country_to_plot = winners_table.loc[winners_table['Year'] == 2005, 'Country'].values[0]

    max_QSO = winners_QSO_WPX_score['max_QSO']
    max_WPX = winners_QSO_WPX_score['max_WPX']
    max_score = winners_QSO_WPX_score['max_score']

    if y_data == "WPX":
        max_to_plot = max_WPX
    elif y_data == "QSOs":
        max_to_plot = max_QSO
    else:
        max_to_plot = max_score

    # Per il riscalamento degli assi
    global_y_winner_min = 0
    global_y_winner_max = max_to_plot
    global_y_range = global_y_winner_max - global_y_winner_min
    global_y_winner_max_buffered = global_y_winner_max + buffer_percentage * global_y_range
    global_y_winner_max_buffered = max_to_plot * (1 + buffer_percentage)


    mean_score_df = calculate_mean_data_for_country(selected_dataset, country_to_plot, y_data)
    
    # Per ottenere il colore corretto dalla mappa
    country_color = color_map.get(country_to_plot, "white")

    fig_winner_country_chart = px.line(
        mean_score_df,
        x='Year',
        y= y_data,
        title=f"Average {y_data} for {country_to_plot} and winners",        
        labels={"Year": "Year", y_data: f"Average {y_data}"},
        template= selected_template,
        color_discrete_sequence=[country_color],
        markers=True    
    ).update_layout(        
        margin=dict(l=2, r=2, t=40, b=2)
    )  
    winners_selected_country = winners_table[winners_table['Country'] == country_to_plot]
    fig_winner_country_chart.update_yaxes(title=y_data, range=[global_y_winner_min, global_y_winner_max_buffered])

    # Viene sovrapposto al grafico a linee uno scatterplot per visualizzare i vincitori
    fig_winner_country_chart.add_scatter(    
        x=winners_selected_country['Year'],  
        y=winners_selected_country[y_data],  
        mode='markers', 
        name='Winners',
        line=dict(color="#FFFFFF"),
        text=winners_selected_country['Call'],
        hovertemplate=
        '<b>Year</b>: %{x}<br>' +
        '<b>Call</b>: %{text}<extra></extra><br>' +
        f'<b>{y_data}</b>: %{{y}}'
    )
    return fig_winner_country_chart

# Callback per aggiornare il grafico a linee per le categorie
@app.callback(
    Output("category-linechart", "figure"),
    [Input('selected-template', 'data'),
     Input('logarithmic-scale', 'value')],
    State('supercat', 'data')
)
def update_category_linechart(selected_template, logatithmic_scale, supercat_count_per_year):
    category_fig = px.line(
        supercat_count_per_year,
        x='Year',
        y='Count',
        color='Category',
        title="Number of operators for each category per year",
        color_discrete_sequence=px.colors.qualitative.Vivid,
        markers = True,
        template=selected_template,
        labels={'Count': 'Count', 'Category': 'Category', 'Year': 'Year'}
    )
    if logatithmic_scale:
        category_fig.update_yaxes(type='log', title_text='Number of operators')
    else:
        category_fig.update_yaxes(title_text='Number of operators')

    return category_fig


########################################################################
# Funzione che crea la dashboard di confronto
########################################################################

def ssb_cw_dashboard_page(selected_dataset):    
    unique_years = selected_dataset['Year'].unique()
    merged_mean_df = pd.DataFrame({'Year': unique_years})

    mean_total_QSOs_CW = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'CW'], 'QSOs')
    mean_total_QSOs_SSB = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'SSB'], 'QSOs')

    mean_total_WPX_CW = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'CW'], 'WPX')
    mean_total_WPX_SSB = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'SSB'], 'WPX')

    mean_total_score_CW = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'CW'], 'Score')
    mean_total_score_SSB = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'SSB'], 'Score')

    for band in bands:
        mean_CW_df = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'CW'], band)
        mean_SSB_df = calculate_mean(selected_dataset[selected_dataset['Contest'] == 'SSB'], band)

        mean_CW_df.rename(columns={band: f"{band}_CW"}, inplace=True)
        mean_SSB_df.rename(columns={band: f"{band}_SSB"}, inplace=True)

        merged_mean_df = pd.merge(merged_mean_df, mean_CW_df, on='Year', how='left')
        merged_mean_df = pd.merge(merged_mean_df, mean_SSB_df, on='Year', how='left')

    # Merge finale per i QSOs totali
    mean_total_QSOs_CW.rename(columns={'QSOs': 'TotalQSOs_CW'}, inplace=True)
    mean_total_QSOs_SSB.rename(columns={'QSOs': 'TotalQSOs_SSB'}, inplace=True)

    mean_total_WPX_CW.rename(columns={'WPX': 'TotalWPX_CW'}, inplace=True)
    mean_total_WPX_SSB.rename(columns={'WPX': 'TotalWPX_SSB'}, inplace=True)

    mean_total_score_CW.rename(columns={'Score': 'TotalScore_CW'}, inplace=True)
    mean_total_score_SSB.rename(columns={'Score': 'TotalScore_SSB'}, inplace=True)

    merged_mean_df = pd.merge(merged_mean_df, mean_total_QSOs_CW, on='Year', how='left')
    merged_mean_df = pd.merge(merged_mean_df, mean_total_QSOs_SSB, on='Year', how='left')
    merged_mean_df = pd.merge(merged_mean_df, mean_total_WPX_CW, on='Year', how='left')
    merged_mean_df = pd.merge(merged_mean_df, mean_total_WPX_SSB, on='Year', how='left')
    merged_mean_df = pd.merge(merged_mean_df, mean_total_score_CW, on='Year', how='left')
    merged_mean_df = pd.merge(merged_mean_df, mean_total_score_SSB, on='Year', how='left')

    # Conteggio dei partecipanti per ogni Country per il plot della mappa
    country_counts_cw = selected_dataset[selected_dataset['Contest'] == 'CW']['country_code'].value_counts().reset_index()
    country_counts_cw.columns = ['country_code', 'count']

    country_counts_ssb = selected_dataset[selected_dataset['Contest'] == 'SSB']['country_code'].value_counts().reset_index()
    country_counts_ssb.columns = ['country_code', 'count']


    # Vincitori di ogni anno per il cw
    grouped_data_cw = selected_dataset[selected_dataset['Contest'] == 'CW'].groupby('Year')
    winners_cw = []

    for year, group in grouped_data_cw:    
        sorted_group_cw = group.sort_values(by='Score', ascending=False)   
        winner_cw = sorted_group_cw.head(1)    
        winners_cw.append(winner_cw)

    winners_cw_table = pd.concat(winners_cw)

    # Vincitori di ogni anno per l'ssb
    grouped_data_ssb = selected_dataset[selected_dataset['Contest'] == 'SSB'].groupby('Year')
    winners_ssb = []

    for year, group in grouped_data_ssb:    
        sorted_group_ssb = group.sort_values(by='Score', ascending=False)   
        winner_ssb = sorted_group_ssb.head(1)    
        winners_ssb.append(winner_ssb)

    winners_ssb_table = pd.concat(winners_ssb)



    # Componente RadioItems per la selezione della banda
    radio_comparsion_band = dbc.RadioItems(
        id="select-comparsion-band",
        options=[        
            {"label": "160M", "value": "160M"},
            {"label": "80M", "value": "80M"},
            {"label": "40M", "value": "40M"},
            {"label": "20M", "value": "20M"},
            {"label": "15M", "value": "15M"},
            {"label": "10M", "value": "10M"}
        ],
        value="20M",
        style={'item-align':'center', 'font-size': '20px'},
        inline = True
    )

    # Componente RadioItems per la selezione del tipo di dato da visualizzare sull'asse y del linechart dei qso wpx
    radio_qso_wpx_comparsion = dbc.RadioItems(
        id="select-line-qso-wpx-y",
        options=[        
            {"label": "WPX", "value": "TotalWPX"},
            {"label": "QSOs", "value": "TotalQSOs"}
        ],
        value="TotalWPX",
        style={'font-size': '20px'},
        inline=True
    )

    # Componente RadioItems per la selezione del continente da visualizzare nella mappa
    radio_comparsion_continents = dbc.RadioItems(
        id= "select-comparsion-continent",
        options=[
            {'label': 'World', 'value': 'World'},
            {'label': 'Europe', 'value': 'Europe'},
            {'label': 'North America', 'value': 'North America'},
            {'label': 'South America', 'value': 'South America'},
            {'label': 'Asia', 'value': 'Asia'},
            {'label': 'Africa', 'value': 'Africa'},
            {'label': 'Oceania', 'value': 'Oceania'}
        ],
        value='World',
        style={'width':1000, 'margin-top':10, 'font-size': '20px'},
        inline = True
    )

    # Componenete RadioItems per la selezione del dato da visualizzare sull'asse y nei barchart dei vincitori
    radio_comparsion_winner_axis = dbc.RadioItems(
        id= "select-y-barchart-comparsion",
        options=[
            {'label': 'WPX', 'value': 'WPX'},
            {'label': 'QSOs', 'value': 'QSOs'},
            {'label': 'Total score', 'value': 'Score'}
        ],
        value='WPX',
        style={'font-size': '20px'},
        inline = True
    )
    
    return dbc.Container([
        dcc.Store(id='selected-data', data=selected_dataset.to_dict('records')),
        dcc.Store(id='merged-mean-data', data=merged_mean_df.to_dict('records')),
        dcc.Store(id='country-counts-ssb', data=country_counts_ssb.to_dict('records')),
        dcc.Store(id='country-counts-cw', data=country_counts_cw.to_dict('records')),
        dcc.Store(id='winners-cw-table', data=winners_cw_table.to_dict('records')),
        dcc.Store(id='winners-ssb-table', data=winners_ssb_table.to_dict('records')),

        dbc.Row(
            dbc.Col(
                html.H3('Comparsion between SSB and CW contest data from 2005 to 2024')
            )
        ),
        # Grafico a linee per le bande
        dbc.Row([
            dbc.Col([
                html.Div([
                    dbc.Label(
                        "Select band:",
                        html_for="select-comparsion-band",
                        style={'font-size':'20px', 'margin-right':'7px'}
                    ),
                    radio_comparsion_band
                ],style={"display": "flex", "alignItems": "center"}),                    
                dcc.Graph(id="band-comparsion"),
            ], style={'max-width':1000, 'height':500}),
            dbc.Col([
                dcc.Graph(id = 'cw-pie', style={'max-width':500, 'height':500}),
                dcc.Graph(id = 'ssb-pie', style={'max-width':500, 'height':500})
            ],style={"display": "flex", "alignItems": "center"}),
        ]),
        # Grafico di comparazione dei punteggi o qso o wpx negli anni
        dbc.Row([
            # Grafico a linee per la media dei punteggi
            dbc.Col([                
                dcc.Graph(id="score-comparsion")
            ], style={'max-width':1000, 'height':500, 'margin-top':'70px'}),
            # Grafico a linee per le medie dei WPX o dei QSO a seconda della selezione
            dbc.Col([
                html.Div([
                    dbc.Label(
                        "Select y axis:",
                        html_for="selectline-qso-wpx-y",
                        style={'font-size':'20px', 'margin-right':'7px', 'margin-left':'20px'}
                    ),
                    radio_qso_wpx_comparsion
                ],style={"display": "flex", "alignItems": "center"}),
                dcc.Graph(id="qso-wpx-comparsion")
            ], style={'max-width':1000, 'height':500, 'margin-top':'30px'})            
        ]), 
        # Grafici dei vincitori. Devono essere più indipendenti l'uno dall'altro
        # Aggiungere radio button o selezione dell'anno, eliminare click sul grafico
        dbc.Row([                    
            dbc.Col([
                html.Div([
                    dbc.Label(
                        "Select y axis:",
                        html_for="select-y-barchart-comparsion",
                        style={'font-size':'20px', 'margin-right':'7px'}
                    ),
                    radio_comparsion_winner_axis
                ],style={"display": "flex", "alignItems": "center"}),                
            ], style={'margin-top':'30px'})
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='winner-barchart-comparsion'),
                dcc.Graph(id='winner-radar')
            ],style={"display": "flex", "alignItems": "center"})                      
        ]),
        # Mappe
        dbc.Row([
            dbc.Col([
                html.Div([
                    dbc.Label(
                        "Focus on:",
                        html_for="select-comparsion-continent",
                        style={'font-size':'20px', 'margin-right':'15px', 'margin-left':'20px', 'margin-top':'5px'}
                    ),
                    radio_comparsion_continents
                ],style={"display": "flex", "alignItems": "center"}),
            ],style={"margin-top": "50px"}),
        ]),
        dbc.Row([        
            dbc.Col([
                dcc.Graph(id='participants-map-graph', config={"scrollZoom": False}),
                dcc.Graph(id='winners-map-graph', config={"scrollZoom": False})
            ], style={'display':'flex', 'min-height': 1000})
        ])
    ], fluid=True)                   
 
#################################################################
# Tutte le callbacks e le funzioni per la dashboard di confronto
#################################################################

# Callback per il linechart delle bande
@app.callback(
    Output("band-comparsion", "figure"),
    [Input("select-comparsion-band", "value"),
     Input('selected-template', 'data')],
    State("merged-mean-data", "data")  
)
def update_band_comparsion_line_chart(selected_band, selected_template, merged_mean_data):
    
    merged_mean_df = pd.DataFrame(merged_mean_data)

    band_cw_column = f"{selected_band}_CW"
    band_ssb_column = f"{selected_band}_SSB"

    fig_band_comparsion_line_chart = go.Figure()

    fig_band_comparsion_line_chart.add_trace(go.Scatter(
        x=merged_mean_df['Year'],
        y=merged_mean_df[band_cw_column],
        mode='lines+markers',
        name='CW',
        line=dict(color='#31AFE0')
    ))

    fig_band_comparsion_line_chart.add_trace(go.Scatter(
        x=merged_mean_df['Year'],
        y=merged_mean_df[band_ssb_column],
        mode='lines+markers',
        name='SSB',
        line=dict(color='darkorange')
    ))

    fig_band_comparsion_line_chart.update_layout(
        title=f"Comparison of number of QSOs between SSB and CW contest in {selected_band} band",
        xaxis_title='Year',
        yaxis_title='Mean of QSOs',
        template= selected_template
    )

    return fig_band_comparsion_line_chart

# Callback per il pie del contest cw
@app.callback(
    Output("cw-pie", "figure"),   
    Input('selected-template', 'data'),
    State("merged-mean-data", "data")    
)
def update_cw_pie(template, data):
    df = pd.DataFrame(data)

    values = []
    labels = []

    for band in bands:
        col = f"{band}_CW"
        if col in df.columns:
            values.append(df[col].sum())
            labels.append(band)

    fig = px.pie(
        names=labels,
        values=values,
        title="Band activity comparsion in CW contest",
        template=template,
        color_discrete_sequence=px.colors.qualitative.Vivid
    ).update_traces(
        hovertemplate=
        "Band: %{label}<br>"
        "QSOs: %{value}<extra></extra>"
    )

    return fig

# Callback per il pie del contest ssb
@app.callback(
    Output("ssb-pie", "figure"),   
    Input('selected-template', 'data'),
    State("merged-mean-data", "data")    
)
def update_ssb_pie(template, data):
    df = pd.DataFrame(data)

    values = []
    labels = []

    for band in bands:
        col = f"{band}_SSB"
        if col in df.columns:
            values.append(df[col].sum())
            labels.append(band)

    fig = px.pie(
        names=labels,
        values=values,
        title="Band activity comparsion in SSB contest",
        template=template,
        color_discrete_sequence=px.colors.qualitative.Vivid
    ).update_traces(
        hovertemplate=
        "Band: %{label}<br>"
        "QSOs: %{value}<extra></extra>"
    )

    return fig

# Callback per il linechart per il punteggio medio negli anni
@app.callback(
    Output("score-comparsion", "figure"),    
    Input('selected-template', 'data'),
    State("merged-mean-data", "data")
)
def update_score_comparsion(selected_template, merged_mean_data):        
    merged_mean_df = pd.DataFrame(merged_mean_data)
    fig_score_chart = go.Figure()
    fig_score_chart.add_trace(go.Scatter(
        x=merged_mean_df['Year'],
        y=merged_mean_df['TotalScore_CW'],
        mode='lines+markers',
        name='CW',
        line=dict(color='#31AFE0')
    ))
    fig_score_chart.add_trace(go.Scatter(
        x=merged_mean_df['Year'],
        y=merged_mean_df['TotalScore_SSB'],
        mode='lines+markers',
        name='SSB',
        line=dict(color='darkorange')
    ))
    fig_score_chart.update_layout(
        title=f"Comparison of mean Score between SSB and CW contest",
        xaxis_title='Year',
        yaxis_title='Mean of Score',
        template= selected_template
    )
    return fig_score_chart

# Callback per il linechart per i wpx o qso medi negli anni
@app.callback(
    Output("qso-wpx-comparsion", "figure"),    
    [Input('selected-template', 'data'), 
     Input('select-line-qso-wpx-y', 'value')],
    State("merged-mean-data", "data")
)
def update_score_comparsion(selected_template, selected_y, merged_mean_data):        
    merged_mean_df = pd.DataFrame(merged_mean_data)

    fig_line_chart = go.Figure()
    y_cw = f'{selected_y}_CW'
    y_ssb = f'{selected_y}_SSB'

    fig_line_chart.add_trace(go.Scatter(
        x=merged_mean_df['Year'],
        y=merged_mean_df[y_cw],
        mode='lines+markers',
        name='CW',
        line=dict(color='#31AFE0')
    ))
    fig_line_chart.add_trace(go.Scatter(
        x=merged_mean_df['Year'],
        y=merged_mean_df[y_ssb],
        mode='lines+markers',
        name='SSB',
        line=dict(color='darkorange')
    ))
    if selected_y == 'TotalQSOs':
        mean_label = 'QSOs'
    else:
        mean_label = 'WPX'

    fig_line_chart.update_layout(
        title=f"Comparison of mean {mean_label} between SSB and CW contest",
        xaxis_title='Year',
        yaxis_title=f"Mean of {mean_label}",
        template= selected_template
    )
    return fig_line_chart

# Callback per le mappe geografiche
@app.callback(
    [Output('participants-map-graph', 'figure'),
    Output('winners-map-graph', 'figure')],
    [Input('select-comparsion-continent', 'value'),
     Input('selected-template', 'data')],
    [State('country-counts-ssb', 'data'),
    State('country-counts-cw', 'data'),
    State('selected-data', 'data'),
    State('winners-cw-table', 'data'),
    State('winners-ssb-table', 'data')]
)
def update_comparsion_map(selected_continent, selected_template, country_counts_ssb, country_counts_cw, selected_dataset, winners_cw_table, winners_ssb_table):
    if isinstance(selected_dataset, list):
        selected_dataset = pd.DataFrame(selected_dataset)
    if isinstance(country_counts_ssb, list):
        country_counts_ssb = pd.DataFrame(country_counts_ssb)        
    if isinstance(country_counts_cw, list):
        country_counts_cw = pd.DataFrame(country_counts_cw)
    if isinstance(winners_cw_table, list):
        winners_cw_table = pd.DataFrame(winners_cw_table)
    if isinstance(winners_ssb_table, list):
        winners_ssb_table = pd.DataFrame(winners_ssb_table)

    bounds = get_continent_bounds(selected_continent)

    type_of_counts_ssb = country_counts_ssb        
    type_of_counts_ssb = type_of_counts_ssb.rename(columns={'count': 'participants'})
    type_of_counts_cw = country_counts_cw        
    type_of_counts_cw = type_of_counts_cw.rename(columns={'count': 'participants'})

    # Inserimento di una colonna con il nome del Country
    type_of_counts_ssb.loc[:, 'Country'] = type_of_counts_ssb['country_code'].apply(lambda code: find_country_from_code(code, selected_dataset[selected_dataset['Contest'] == 'SSB']))
    type_of_counts_cw.loc[:, 'Country'] = type_of_counts_cw['country_code'].apply(lambda code: find_country_from_code(code, selected_dataset[selected_dataset['Contest'] == 'CW']))

    # Merge dei dati CW e SSB per confronto
    combined_counts = pd.merge(
        type_of_counts_ssb[['country_code', 'participants', 'Country']],
        type_of_counts_cw[['country_code', 'participants', 'Country']],
        on=['country_code', 'Country'],
        suffixes=('_ssb', '_cw')
    )

    # Determina il contest con il maggior numero di partecipanti
    combined_counts['Majority'] = combined_counts.apply(lambda row: 'CW' if row['participants_cw'] > row['participants_ssb'] else 'SSB', axis=1)
    color_map = {'CW': '#31AFE0', 'SSB': 'orange'}
    combined_counts['color'] = combined_counts['Majority'].map(color_map)
    
    # Mappa per numero di partecipanti
    map_figure_participants = px.choropleth(
        combined_counts,
        locations="country_code",
        color='Majority',
        hover_name="Country",
        hover_data={"country_code": False, "participants_ssb": True, "participants_cw": True},
        template= selected_template,
        title=f"Comparsion of number of participants per Country",
        color_discrete_map=color_map,
    ).update_layout(
        margin=dict(l=5, r=5, t=70, b=20),
        height=600,
        width = 800,
        title_y= 0.98,
        title_x=0.5, 
        geo=dict(
            projection_scale=1,
            center={"lat": (bounds['lat'][0] + bounds['lat'][1]) / 2, "lon": (bounds['lon'][0] + bounds['lon'][1]) / 2},
            lonaxis_range=bounds['lon'],
            lataxis_range=bounds['lat']
        ),
        legend=dict(
            orientation="h",      
            yanchor="bottom",    
            xanchor="center",  
            y=1,    
            x=0.5    
        )
    )

    # Vincitori
    cw_countries = winners_cw_table.groupby('country_code').size().reset_index(name='cw_winners')
    ssb_countries = winners_ssb_table.groupby('country_code').size().reset_index(name='ssb_winners')

    winners_counts = pd.merge(cw_countries, ssb_countries, on='country_code', how='outer').fillna(0)
    winners_counts['cw_winners'] = winners_counts['cw_winners'].astype(int)
    winners_counts['ssb_winners'] = winners_counts['ssb_winners'].astype(int)

    winners_counts['Contest'] = winners_counts.apply(
        lambda row: 'CW Only' if row['cw_winners'] > 0 and row['ssb_winners'] == 0 else
                    'SSB Only' if row['ssb_winners'] > 0 and row['cw_winners'] == 0 else
                    'Both',
        axis=1
    )
    winners_counts['Country'] = winners_counts['country_code'].apply(lambda code: find_country_from_code(code, selected_dataset))

    color_map = {'CW Only': '#31AFE0', 'SSB Only': 'orange', 'Both': '#FF00B7'}

    # Mappa per numero di vincitori
    map_figure_winners = px.choropleth(
        winners_counts,
        locations="country_code",
        color="Contest",
        hover_name="Country",        
        hover_data={"Country": False, "country_code":False, "cw_winners": True, "ssb_winners": True},
        template= selected_template,
        title=f"Winners Distribution",
        color_discrete_map=color_map
    ).update_layout(
        margin=dict(l=5, r=5, t=70, b=20),
        height=600,
        width = 800,
        title_y= 0.98,
        title_x=0.5,
        geo=dict(
            projection_scale=1,
            center={"lat": (bounds['lat'][0] + bounds['lat'][1]) / 2, "lon": (bounds['lon'][0] + bounds['lon'][1]) / 2},
            lonaxis_range=bounds['lon'],
            lataxis_range=bounds['lat']
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom",
            xanchor="center",
            y=1,          
            x=0.5            
        )
    )
    return map_figure_participants, map_figure_winners

# Callback per il grafico a barre dei vincitori
@app.callback(
    Output("winner-barchart-comparsion", "figure"),
    [Input('selected-template', 'data'),
      Input('select-y-barchart-comparsion', 'value')],
    [State('winners-cw-table', 'data'),
     State('winners-ssb-table', 'data')]
)
def update_winner_comparsion_barchart(selected_template, selected_y, winners_cw_table, winners_ssb_table):    
    if isinstance(winners_cw_table, list):
        winners_cw_table = pd.DataFrame(winners_cw_table)
    if isinstance(winners_ssb_table, list):
        winners_ssb_table = pd.DataFrame(winners_ssb_table)

    cw_color = '#31AFE0'
    ssb_color = 'orange'

    cw_data = winners_cw_table[["Year", "Country", selected_y]].rename(columns={selected_y: "Value"})
    ssb_data = winners_ssb_table[["Year", "Country", selected_y]].rename(columns={selected_y: "Value"})

    winner_barchart = go.Figure()
    winner_barchart.add_trace(
        go.Bar(
            x=cw_data["Year"],
            y=cw_data["Value"],
            name="CW",
            marker_color=cw_color,
            hovertemplate=(
                "<b>Year:</b> %{x}<br>"
                "<b>Country:</b> %{customdata}<br>"
                "<b>" + selected_y +": </b> %{y}<extra></extra>"
            ),
            customdata=cw_data["Country"]
        )
    )
    winner_barchart.add_trace(
        go.Bar(
            x=ssb_data["Year"],
            y=ssb_data["Value"],
            name="SSB",
            marker_color=ssb_color,
            hovertemplate=(
                "<b>Year:</b> %{x}<br>"
                "<b>Country:</b> %{customdata}<br>"
                "<b>" + selected_y +": </b> %{y}<extra></extra>"
            ),
            customdata=ssb_data["Country"]
        )
    )
    winner_barchart.update_layout(
        template= selected_template,
        height=570,
        width=850,
        barmode="group",  # Per sovrapporre le barre
        title=f"Winner Comparison ({selected_y})",
        xaxis_title="Year",
        yaxis_title=selected_y,
        legend_title="Contest",
        margin=dict(l=10, r=10, t=50, b=50),
    )

    return winner_barchart

# Radar chart vincitori
@app.callback(
    Output('winner-radar', 'figure'),
    Input('selected-template', 'data'),
    [ State('winners-cw-table', 'data'),
    State('winners-ssb-table', 'data')]
)
def update_radar_chart(selected_template, winners_cw_table, winners_ssb_table):
    if isinstance(winners_cw_table, list):
        winners_cw_table = pd.DataFrame(winners_cw_table)
    if isinstance(winners_ssb_table, list):
        winners_ssb_table = pd.DataFrame(winners_ssb_table)

    cw_color = '#31AFE0'
    ssb_color = 'orange'

    cw_band_profile = winners_cw_table[bands].mean()
    ssb_band_profile = winners_ssb_table[bands].mean()
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=cw_band_profile.values,
            theta=bands,
            fill='toself',
            name='CW Winners',
            line=dict(color=cw_color)
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=ssb_band_profile.values,
            theta=bands,
            fill='toself',
            name='SSB Winners',
            line=dict(color=ssb_color)
        )
    )

    fig.update_layout(
        title="Band activity profile of contest winners (mean of QSOs per band)",
        polar=dict(
            radialaxis=dict(visible=True)
        ),
        template = selected_template,
        showlegend=True
    )

    return fig


##################################################################
# Callback per gestire la selezione del dataset e la navigazione alla dashboard
@app.callback(
    Output('page-content', 'children'),
    [Input('ssb-contest', 'n_clicks'),
     Input('cw-contest', 'n_clicks'),
     Input('ssb-cw', 'n_clicks')],
     prevent_initial_call=True  # Per evitare che la callback venga chiamata all'inizio
)
def select_dataset(ssb_click, cw_click, ssb_cw_click):
    if ssb_click:
        return single_data_dashboard_page(ssb_dataset, 'SSB')  
    elif cw_click:
        return single_data_dashboard_page(cw_dataset, 'CW')
    elif ssb_cw_click:
        return ssb_cw_dashboard_page(ssb_cw_dataset)
    else:
        return welcome_page()

if __name__ == '__main__':
    app.run(debug=True)




