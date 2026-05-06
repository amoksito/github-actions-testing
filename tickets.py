import os
import requests
import yfinance as yf
import matplotlib

# Configurar backend sin interfaz gráfica para GitHub Actions
matplotlib.use("Agg")
import mplfinance as mpf
import io
import pandas as pd

# --- Configuración y Constantes ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RSI_PERIOD = 14  # Periodo estándar para el RSI
VOL_PERIOD = 5  # Periodo para comparar el volumen promedio

# --- Funciones de Telegram ---


def enviar_mensaje(texto):
    """Envía un mensaje de texto a Telegram."""
    if not TOKEN or not CHAT_ID:
        print(f"Error: Faltan credenciales de Telegram. Mensaje: {texto[:50]}...")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}
    requests.post(url, json=payload)


def enviar_grafico(buffer, caption):
    """Envía un gráfico (buffer) a Telegram."""
    if not TOKEN or not CHAT_ID:
        print(
            f"Error: Faltan credenciales de Telegram. Gráfico con caption: {caption[:50]}..."
        )
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    buffer.seek(0)
    # Agregamos un nombre de archivo para mayor compatibilidad con la API
    files = {"photo": ("chart.png", buffer, "image/png")}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
    requests.post(url, files=files, data=data)


# --- Funciones de Cálculo de Análisis Técnico ---


def calcular_rsi(df, period):
    """Calcula el Índice de Fuerza Relativa (RSI)."""
    # Usando el método .ewm para una media móvil exponencial para mayor precisión (estándar)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Cálculos EWM
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]  # Devolver solo el último valor


def analizar_volumen(df, period):
    """Compara el volumen de hoy vs. el promedio reciente y devuelve un texto."""
    vol_hoy = df["Volume"].iloc[-1]
    # Promedio de las últimas 'period' sesiones, excluyendo la de hoy (iloc[-2])
    vol_avg = df["Volume"].rolling(window=period).mean().iloc[-2]

    if vol_avg == 0 or pd.isna(vol_avg):
        return f"Vol: {vol_hoy:,.0f} (N/A Avg)"

    cambio_pct = ((vol_hoy - vol_avg) / vol_avg) * 100

    if abs(cambio_pct) > 30:  # Se usa 30% como umbral para volumen atípico
        etiqueta = "ALTO" if cambio_pct > 0 else "BAJO"
        return f"Vol: {vol_hoy:,.0f} (*{cambio_pct:.1f}%* {etiqueta} ⚠️)"
    else:
        return f"Vol: {vol_hoy:,.0f} ({cambio_pct:.1f}%)"


# --- Función para Procesar Cada Activo (Gráfico + Análisis) ---


def procesar_activo(ticker, nombre):
    """Descarga datos una sola vez, genera gráfico y devuelve la línea de resumen."""
    try:
        # Descargar datos (3 meses)
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)

        if df.empty:
            return None, f"❌ **{nombre}** ({ticker}): No se obtuvieron datos."

        # Limpieza de columnas robusta para yfinance 0.2.x
        if isinstance(df.columns, pd.MultiIndex):
            if "Close" in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(0)
            else:
                df.columns = df.columns.get_level_values(-1)

        # Eliminar filas con NaN en el cierre (común en la última fila si el mercado está abierto)
        if pd.isna(df["Close"].iloc[-1]):
            df = df.iloc[:-1]

        if len(df) < max(RSI_PERIOD, VOL_PERIOD) + 2:
            return None, f"❌ **{nombre}** ({ticker}): Datos insuficientes."

        # 1. Generar Gráfico en Buffer
        buf = io.BytesIO()
        mpf.plot(
            df,
            type="candle",
            mav=(20, 50),
            volume=True,
            title=f"\n{nombre} ({ticker}) - Últimos 3 meses",
            style="yahoo",
            savefig=dict(fname=buf, dpi=100, pad_inches=0.25),
        )
        buf.seek(0)

        # 2. Calcular Análisis Técnico
        rsi_val = calcular_rsi(df, RSI_PERIOD)
        vol_texto = analizar_volumen(df, VOL_PERIOD)

        if rsi_val > 70:
            rsi_estado = f"RSI: *{rsi_val:.1f}* (Sobrecompra 🚨)"
        elif rsi_val < 30:
            rsi_estado = f"RSI: *{rsi_val:.1f}* (Sobreventa ✅)"
        else:
            rsi_estado = f"RSI: {rsi_val:.1f}"

        cierre = df["Close"].iloc[-1]
        resumen = f"▪️ **{nombre}** ({ticker}): Cierre {cierre:.2f} | {rsi_estado} | {vol_texto}"

        return buf, resumen

    except Exception as e:
        print(f"Error procesando {ticker}: {e}")
        return None, f"❌ **{nombre}** ({ticker}): Error ({str(e)[:30]}...)"


# --- Función Principal (Main) ---


def main():
    if not TOKEN or not CHAT_ID:
        print("Error: Faltan secretos de Telegram.")
        return

    enviar_mensaje(
        "🔎 **Reporte Diario de Mercado:** Iniciando generación de gráficos y análisis..."
    )

    activos = [
        {"ticker": "SPY", "nombre": "S&P 500"},
        {"ticker": "QQQ", "nombre": "Nasdaq 100"},
        {"ticker": "EWZ", "nombre": "Brasil ETF"},
        {"ticker": "GC=F", "nombre": "Oro Futuros"},
        {"ticker": "SI=F", "nombre": "Plata Futuros"},
    ]

    lineas_resumen = []

    for activo in activos:
        print(f"Procesando {activo['ticker']}...")
        buffer, resumen = procesar_activo(activo["ticker"], activo["nombre"])

        if buffer:
            enviar_mensaje(f"📊 **{activo['nombre']}**")
            enviar_grafico(buffer)
            buffer.close()

        lineas_resumen.append(resumen)

    # Enviar el Resumen de Texto Final
    resumen_final = "\n".join(lineas_resumen)
    mensaje_final = (
        "📊 **RESUMEN TÉCNICO DIARIO**\n"
        "-------------------------------------\n"
        f"{resumen_final}\n\n"
        "*(Volumen comparado vs. promedio de 5 días)*"
    )

    enviar_mensaje(mensaje_final)
    enviar_mensaje("✅ Reporte finalizado.")


if __name__ == "__main__":
    main()
