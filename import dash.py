# ==============================================================================
# SECCIÓN 1: IMPORTACIONES DE LIBRERÍAS
# ==============================================================================
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import geopandas as gpd
import numpy as np
import unicodedata

# ==============================================================================
# SECCIÓN 2: CARGA Y LIMPIEZA DE DATOS
# ==============================================================================

# --- A. Función de normalización de texto ---
def normalizar_texto(texto):
    nfkd_form = unicodedata.normalize('NFD', str(texto))
    texto_sin_acento = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return texto_sin_acento.lower().strip()

# --- B. Cargar y preparar el mapa (Shapefile) ---
print("Paso 1: Cargando el mapa (Shapefile)...")
try:
    ruta_shapefile = 'shapefiles_comunas'
    nombre_columna_region = 'Region'
    nombre_columna_comuna_mapa = 'Comuna'
    
    gdf_chile = gpd.read_file(ruta_shapefile)
    
    # --- LÍNEA CORREGIDA CON EL NOMBRE CORRECTO DE LA REGIÓN ---
    gdf_rm = gdf_chile[gdf_chile[nombre_columna_region] == 'Región Metropolitana de Santiago'].copy()
    
    gdf_rm[nombre_columna_comuna_mapa] = gdf_rm[nombre_columna_comuna_mapa].apply(normalizar_texto)
    
    gdf_rm = gdf_rm.to_crs("WGS84")
    print("   -> Mapa cargado, filtrado y normalizado correctamente.")
except Exception as e:
    print(f"   -> ERROR al cargar el shapefile: {e}")
    exit()

# --- C. Crear el GeoJSON para Plotly ---
print("Paso 2: Creando el GeoJSON para las comunas...")
geojson_comunas = gdf_rm.__geo_interface__
print("   -> GeoJSON creado exitosamente.")

# --- D. Cargar y limpiar tu archivo de datos de arriendos ---
print("Paso 3: Cargando y limpiando el archivo de propiedades...")
try:
    df_propiedades = pd.read_csv('Datos arriendo RM JULIO 2025.txt', sep='\t')

    monto_numerico = pd.to_numeric(
        df_propiedades['Monto'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='coerce'
    )
    valor_uf_numerico = pd.to_numeric(
        df_propiedades['Valor UF'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='coerce'
    )
    df_propiedades['Valor_UF_Consolidado'] = np.where(
        df_propiedades['Unidad Monetaria'] == 'UF',
        monto_numerico,
        valor_uf_numerico
    )

    df_propiedades.dropna(subset=['Valor_UF_Consolidado', 'Dormitorios', 'Baños', 'Comuna'], inplace=True)
    df_propiedades['Dormitorios'] = df_propiedades['Dormitorios'].astype(int)
    df_propiedades['Baños'] = df_propiedades['Baños'].astype(int)
    
    df_propiedades['Comuna'] = df_propiedades['Comuna'].apply(normalizar_texto)

    print("   -> Archivo de propiedades cargado, limpiado y normalizado correctamente.")
except FileNotFoundError:
    print("   -> ERROR: No se encontró el archivo de datos.")
    exit()

# ==============================================================================
# SECCIÓN 3: INICIALIZACIÓN DE LA APLICACIÓN DASH
# ==============================================================================
print("Paso 4: Iniciando la aplicación Dash...")
app = dash.Dash(__name__)
server = app.server

# ==============================================================================
# SECCIÓN 4: DISEÑO DE LA PÁGINA WEB (LAYOUT)
# ==============================================================================
app.layout = html.Div(children=[
    # Título principal del dashboard
    html.H1(
        children='Valor promedio de arriendo en UF Julio 2025',
        style={'textAlign': 'center', 'color': '#333', 'fontFamily': 'Arial, sans-serif'}
    ),

    # Contenedor principal que divide la página en filtros y mapa
    html.Div([
        
        # --- DIV de la Columna de Filtros (Izquierda) ---
        html.Div([
            html.H3("Filtros de Búsqueda", style={'textAlign': 'center', 'fontFamily': 'Arial, sans-serif'}),
            
            html.Label("Número de Dormitorios:", style={'fontWeight': 'bold', 'fontFamily': 'Arial, sans-serif'}),
            dcc.Dropdown(
                id='dropdown-dormitorios',
                options=[{'label': 'Todos', 'value': 'todos'}] + [{'label': f'{i} Dormitorios', 'value': i} for i in sorted(df_propiedades['Dormitorios'].unique())],
                value='todos',
                clearable=False
            ),
            
            html.Br(),
            
            html.Label("Número de Baños:", style={'fontWeight': 'bold', 'fontFamily': 'Arial, sans-serif'}),
            dcc.Dropdown(
                id='dropdown-banos',
                options=[{'label': 'Todos', 'value': 'todos'}] + [{'label': f'{i} Baños', 'value': i} for i in sorted(df_propiedades['Baños'].unique())],
                value='todos',
                clearable=False
            ),
        ], style={
            'width': '25%',
            'float': 'left',
            'padding': '20px',
            'boxSizing': 'border-box',
            'border': '1px solid #ddd',
            'borderRadius': '5px',
            'backgroundColor': '#f9f9f9',
            'margin': '10px'
        }),

        # --- DIV de la Columna del Mapa (Derecha) ---
        html.Div([
            dcc.Graph(id='mapa-comunas', style={'height': '80vh'})
        ], style={
            'width': '73%', # Un poco menos para dar espacio al margen
            'float': 'right',
            'boxSizing': 'border-box',
            'padding': '10px'
        })

    ])
])
# ==============================================================================
# SECCIÓN 5: LÓGICA DE INTERACTIVIDAD (CALLBACK)
# ==============================================================================
# --- CALLBACK 1: Actualiza las opciones del dropdown de baños ---
@app.callback(
    Output('dropdown-banos', 'options'),
    Input('dropdown-dormitorios', 'value')
)
def update_banos_options(selected_dorms):
    if selected_dorms == 'todos':
        opciones_banos = [{'label': 'Todos', 'value': 'todos'}] + \
                         [{'label': f'{i} Baños', 'value': i} for i in sorted(df_propiedades['Baños'].unique())]
        return opciones_banos

    df_filtrado_por_dorms = df_propiedades[df_propiedades['Dormitorios'] == selected_dorms]
    banos_disponibles = sorted(df_filtrado_por_dorms['Baños'].unique())
    opciones_nuevas = [{'label': 'Todos', 'value': 'todos'}] + \
                      [{'label': f'{i} Baños', 'value': i} for i in banos_disponibles]
    return opciones_nuevas

# --- CALLBACK 2: Actualiza el mapa y reinicia el filtro de baños ---
@app.callback(
    Output('mapa-comunas', 'figure'),
    Output('dropdown-banos', 'value'), # Salida adicional para reiniciar el valor de baños
    Input('dropdown-dormitorios', 'value'),
    Input('dropdown-banos', 'value')
)
def update_map(selected_dorms, selected_banos):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'No trigger'

    # Si el cambio vino del dropdown de dormitorios, reiniciamos la selección de baños a "Todos"
    if trigger_id == 'dropdown-dormitorios':
        selected_banos_nuevo = 'todos'
    else:
        selected_banos_nuevo = selected_banos

    filtered_df = df_propiedades.copy()

    if selected_dorms != 'todos':
        filtered_df = filtered_df[filtered_df['Dormitorios'] == selected_dorms]
    
    # Usamos el valor actualizado de baños para el filtro
    if selected_banos_nuevo != 'todos':
        filtered_df = filtered_df[filtered_df['Baños'] == selected_banos_nuevo]
        
    if not filtered_df.empty:
        datos_agregados = filtered_df.groupby('Comuna').agg(
            Promedio_UF=('Valor_UF_Consolidado', 'mean'),
            Cantidad_Propiedades=('Monto', 'count')
        ).reset_index()
    else:
        datos_agregados = pd.DataFrame(columns=['Comuna', 'Promedio_UF', 'Cantidad_Propiedades'])

    fig = px.choropleth_mapbox(
        datos_agregados,
        geojson=geojson_comunas,
        locations='Comuna',
        featureidkey="properties.Comuna",
        color='Promedio_UF',
        color_continuous_scale="Viridis_r",
        mapbox_style="carto-positron",
        zoom=8.7,
        center={"lat": -33.47, "lon": -70.62},
        opacity=0.6,
        labels={'Promedio_UF': 'Valor Promedio (UF)'},
        hover_name='Comuna',
        hover_data={
            'Comuna': False, 'Promedio_UF': ':.1f', 'Cantidad_Propiedades': True
        }
    )
    
    fig.update_layout(
        margin={"r":0, "t":0, "l":0, "b":0},
        coloraxis_colorbar={'title': 'UF Promedio', 'len': 0.7, 'yanchor': 'bottom', 'y': 0}
    )
    
    # Devolvemos la figura y el valor (posiblemente reiniciado) del dropdown de baños
    return fig, selected_banos_nuevo
# ==============================================================================
# SECCIÓN 6: EJECUTAR LA APLICACIÓN
# ==============================================================================
if __name__ == '__main__':
    print("Paso 5: Servidor Dash listo. Accede en tu navegador a http://127.0.0.1:8050/")
    app.run(debug=False)