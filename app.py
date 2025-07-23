import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from zinc import zinc


st.title("Zinc Oxide Imports Analysis")
tab1, tab2, tab3 = st.tabs(["Histogram Price", "Top 5 importer","Price Analysis"])

df_zinc = pd.read_excel('zinc_oxide.xlsx')
df_zinc['Date'] = df_zinc.apply(
    lambda row: pd.Timestamp(year=row['AÑO'], month=row['MES'], day=row['DIA']),
    axis=1
)
df_zinc['Date'] = pd.to_datetime(df_zinc['Date'], errors='coerce')

df_price = pd.DataFrame(zinc)[['Date','Close']]
df_price['Date'] = pd.to_datetime(df_price['Date'], errors='coerce')
df_price = df_price.set_index('Date')

df_fechas = pd.date_range(start='2024-01-02', end=pd.Timestamp.today().normalize(), freq='D')
df_price = df_price.reindex(df_fechas)
df_price['Close'] = df_price['Close'].ffill()

df_zinc = pd.merge(df_zinc, df_price, how='left', left_on='Date', right_index=True)
df_zinc['rut_importador'] = df_zinc['RUT PROBABLE IMPORTADOR'].astype(str) + '-' + df_zinc['VERIFICADOR RUT'].astype(str)

with tab1:
    st.title("Distribution FOB price by unit")

    # Rango de fechas dinámico
    min_date = df_zinc["Date"].min()
    max_date = df_zinc["Date"].max()

    start_date, end_date = st.date_input(
        "Selecciona el rango de fechas:",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date,
        format="YYYY-MM-DD"
    )

    # Filtrar el dataframe por fecha
    mask = (df_zinc["Date"] >= pd.to_datetime(start_date)) & (df_zinc["Date"] <= pd.to_datetime(end_date))
    filtered_df = df_zinc[mask]

    # Mostrar histograma
    fig = px.histogram(
        filtered_df,
        x="US$ FOB UNIT",
        nbins=200,
        title="Distribución del precio FOB unitario del zinc",
        labels={"US$ FOB UNIT": "Precio FOB unitario (USD)"}
    )
    fig.update_layout(bargap=0.1)

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
        **Description**: this chart show the distribution of purchase price in a given range. Considers all imports from 2024  
        **Next Steps**: improve filters and queries
    """)


with tab2:
    st.subheader("Distribution of FOB price by Importers (Top 5 by amount)")

    # Obtener top 5 importadores por kilos
    agg_ruts = (
        df_zinc
        .groupby('rut_importador')[['CANTIDAD']]
        .sum()
        .sort_values('CANTIDAD', ascending=False)
        .head(5)
    )
    top_ruts = agg_ruts.index.tolist()
    df_top = df_zinc[df_zinc['rut_importador'].isin(top_ruts)]

    # Crear gráfico boxplot
    fig2 = px.box(
        df_top,
        x="rut_importador",
        y="US$ FOB UNIT",
        points=False,
        title="Distribution FOB price by Unit - Top 5 importers by amount",
        labels={"rut_importador": "RUT importador", "US$ FOB UNIT": "Precio FOB unitario (USD)"}
    )
    fig2.update_yaxes(range=[1.5, 3.5])

    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("""
        **Description**: boxplot to show the distribution of prices that each importer has purchased  
        **Next Step**: add filter and date range search by importers
    """)

    st.subheader("Top 5 Importers by volume (kgs)")
    kilos_por_importador = (
        df_top.groupby("rut_importador")["CANTIDAD"]
        .sum()
        .reset_index()
        .sort_values(by="CANTIDAD", ascending=False)
    )

    # Crear gráfico de barras
    fig_bar = px.bar(
        kilos_por_importador,
        x="rut_importador",
        y="CANTIDAD",
        title="Total Volume imported by Top 5 importers",
        labels={"rut_importador": "RUT importador", "CANTIDAD": "Kilos importados"},
        text_auto=True
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("""
        **Description**: Amount of Zinc Oxide imported by importer 
        **Next Step**: add filter and date range search by importers
    """)

with tab3:
    df_zinc['mes'] = df_zinc['Date'].dt.to_period('M').astype(str)

    agg_mes = (
        df_zinc
        .groupby('mes')
        .apply(lambda x: pd.Series({
            'precio_min': x['US$ FOB UNIT'].min(),
            'precio_max': x['US$ FOB UNIT'].max(),
            'precio_promedio': x['US$ FOB UNIT'].mean(),
            'precio_ponderado': np.average(x['US$ FOB UNIT'], weights=x['CANTIDAD'])
        }))
        .reset_index()
    )
    df_price["precio_unid"] = df_price['Close']/1000

    df_price['mes'] = df_price.index.to_period('M').astype(str)

    df_mercado = (
        df_price
        .groupby('mes')
        .agg(
            precio_mercado_min=('precio_unid', 'min'),
            precio_mercado_max=('precio_unid', 'max'),
            precio_mercado_promedio=('precio_unid', 'mean')
        )
        .reset_index()
    )
    df_comparacion = pd.merge(agg_mes, df_mercado, on='mes', how='left')

    fig3 = go.Figure()

    # Precio ponderado importado
    fig3.add_trace(go.Scatter(
        x=df_comparacion['mes'],
        y=df_comparacion['precio_ponderado'],
        name='Importación (ponderado)',
        mode='lines+markers'
    ))

    # Precio promedio de mercado
    fig3.add_trace(go.Scatter(
        x=df_comparacion['mes'],
        y=df_comparacion['precio_mercado_promedio'],
        name='Mercado (promedio)',
        mode='lines+markers'
    ))

    # (Opcional) Rango de precios de mercado como área sombreada
    fig3.add_trace(go.Scatter(
        x=df_comparacion['mes'],
        y=df_comparacion['precio_mercado_max'],
        name='Mercado (máximo)',
        line=dict(width=0),
        showlegend=False
    ))
    fig3.add_trace(go.Scatter(
        x=df_comparacion['mes'],
        y=df_comparacion['precio_mercado_min'],
        name='Mercado (mínimo)',
        fill='tonexty',
        mode='lines',
        line=dict(width=0),
        fillcolor='rgba(0,100,255,0.2)',
        showlegend=True
    ))

    fig3.update_layout(
        title='Comparation of imported price vs market price',
        xaxis_title='Mes',
        yaxis_title='Precio USD',
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("""
        **Description**: Time series show the evolution of price by month. Chart contains min, max, and average market price and weighted average price of imports  
        **Price MArket Data Source**: https://markets.businessinsider.com/commodities/zinc-price?op=1  
        **Next Step**: add date range, and other metrics moving average, volatility, simulations 
    """)