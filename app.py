import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.stats import norm
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA (Debe ser lo primero) ---
st.set_page_config(page_title="Quant Risk Dash", layout="wide")

st.title("🛡️ Market Risk & Correlation Dashboard")

# --- SIDEBAR: PARÁMETROS ---
st.sidebar.header("Parameters")

# Tickers por defecto
default_tickers = "SPY, GLD, BTC-USD, NVDA"
ticker_input = st.sidebar.text_input("Assets (comma separated)", value=default_tickers)
# Limpiamos y convertimos a mayúsculas
tickers = [t.strip().upper() for t in ticker_input.split(',')]

# Fechas
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start Date", value=datetime.today() - timedelta(days=365))
end_date = col2.date_input("End Date", value=datetime.today())

# Nivel de Confianza para el VaR
conf_level = st.sidebar.slider("VaR Confidence Level (%)", 90, 99, 95) / 100

# --- FUNCIONES AUXILIARES ---
@st.cache_data
def load_data(tickers, start, end):
    try:
        # Usamos auto_adjust=True para que 'Close' sea el precio ajustado real
        df = yf.download(tickers, start=start, end=end, auto_adjust=True)
        
        # Si descargamos un solo ticker, yfinance devuelve una estructura diferente.
        # Ajustamos para asegurar compatibilidad.
        if len(tickers) == 1:
             # Convertimos a DataFrame si es Series y aseguramos estructura
             pass 
        
        # Devolvemos solo la columna Close (que ya está ajustada)
        if 'Close' in df.columns:
            return df['Close']
        else:
            return df
    except Exception as e:
        return pd.DataFrame()

def get_log_returns(prices):
    # Retornos Logarítmicos: ln(Pt / Pt-1)
    return np.log(prices / prices.shift(1)).dropna()

# --- LÓGICA PRINCIPAL ---
if len(tickers) > 0:
    st.write(f"Analyzing data from **{start_date}** to **{end_date}**...")
    
    try:
        # 1. Cargar Datos
        data = load_data(tickers, start_date, end_date)
        
        if not data.empty:
            # Filtramos solo los tickers que realmente bajaron data
            available_tickers = [t for t in tickers if t in data.columns]
            data = data[available_tickers] # Reordenamos según input usuario

            # 2. Gráfico de Rendimiento Normalizado (Base 100)
            st.subheader("Relative Performance (Base 100)")
            normalized = (data / data.iloc[0]) * 100
            
            fig_price = px.line(normalized, x=normalized.index, y=normalized.columns, labels={'value': 'Normalized Price'})
            
            # Ajuste Visual: Leyenda arriba para dar más espacio al gráfico
            fig_price.update_layout(legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ))
            st.plotly_chart(fig_price, use_container_width=True)

            # Cálculo de Retornos
            returns = get_log_returns(data)
            
            # Layout de 2 columnas para Métricas
            c1, c2 = st.columns(2)

            # 3. Matriz de Correlación
            with c1:
                st.subheader("Correlation Matrix")
                corr = returns.corr()
                fig_corr = px.imshow(corr, text_auto=".2f", aspect="auto", 
                                     color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
                st.plotly_chart(fig_corr, use_container_width=True)

            # 4. Cálculo de VaR (Paramétrico)
            with c2:
                st.subheader(f"Daily Value at Risk ({int(conf_level*100)}%)")
                
                mu = returns.mean()
                sigma = returns.std()
                var_value = norm.ppf(1 - conf_level, mu, sigma)
                
                # Invertimos signo para mostrar magnitud de pérdida (más estético)
                var_display = [x * -1 if x < 0 else x for x in var_value]
                
                var_df = pd.DataFrame({
                    "Asset": available_tickers,
                    "Max Daily Loss": [f"{x*100:.2f}%" for x in var_display]
                })
                
                st.dataframe(var_df, use_container_width=True, hide_index=True)
                st.caption("Estimated maximum daily loss based on normal distribution.")

        else:
            st.warning("No data found. Please check your ticker symbols.")
            
    except Exception as e:
        st.error(f"Error: {e}")