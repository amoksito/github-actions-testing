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
    files = {"photo": buffer}
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


# --- Función para Generar el Gráfico y Enviar (Sin Texto) ---


def generar_grafico_pro(ticker, nombre):
    """Descarga datos, genera el gráfico de velas con MAs y lo envía a Telegram."""
    try:
        # Descargar datos (3 meses para ver detalle de velas)
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)

        if df.empty:
            return

        # Limpieza de datos
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.droplevel(1)

        # Configurar el estilo y guardar en buffer de memoria
        buf = io.BytesIO()

        mpf.plot(
            df,
            type="candle",
            mav=(20, 50),  # Medias móviles de 20 y 50 días
            volume=True,
            title=f"\n{nombre} ({ticker}) - Últimos 3 meses",
            style="yahoo",
            savefig=dict(fname=buf, dpi=100, pad_inches=0.25),
        )

        # Enviar a Telegram solo el gráfico
        enviar_grafico(buf, f"📊 **{nombre}**")
        print(f"Gráfico enviado: {ticker}")
        buf.close()

    except Exception as e:
        print(f"Error en {ticker}: {e}")
        enviar_mensaje(f"⚠️ Error al generar gráfico para {ticker}: {str(e)}")


# --- Función para Generar el Resumen de Texto ---


def generar_resumen_tecnico_texto(ticker, nombre):
    """Descarga datos, hace el análisis y devuelve una línea de texto formateada."""
    try:
        # Descargamos solo lo necesario, sin generar gráfico
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)

        if df.empty or len(df) < max(RSI_PERIOD, VOL_PERIOD) + 2:
            return f"❌ **{nombre}** ({ticker}): Datos insuficientes."

        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.droplevel(1)

        # Análisis
        rsi_val = calcular_rsi(df, RSI_PERIOD)
        vol_texto = analizar_volumen(df, VOL_PERIOD)

        # Interpretación del RSI
        if rsi_val > 70:
            rsi_estado = f"RSI: *{rsi_val:.1f}* (Sobrecompra 🚨)"
        elif rsi_val < 30:
            rsi_estado = f"RSI: *{rsi_val:.1f}* (Sobreventa ✅)"
        else:
            rsi_estado = f"RSI: {rsi_val:.1f}"

        cierre = df["Close"].iloc[-1]

        # Formato final de la línea
        return f"▪️ **{nombre}** ({ticker}): Cierre {cierre:.2f} | {rsi_estado} | {vol_texto}"

    except Exception as e:
        return (
            f"❌ **{nombre}** ({ticker}): Error de conexión/cálculo ({str(e)[:20]}...)"
        )


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

    # --- 1. Generar y Enviar Gráficos ---
    for activo in activos:
        generar_grafico_pro(activo["ticker"], activo["nombre"])

    # --- 2. Generar y Enviar el Resumen de Texto Final ---
    print("Generando resumen técnico final...")
    enviar_mensaje("⏳ **Resumen Técnico en curso...**")

    lineas_resumen = []

    for activo in activos:
        linea = generar_resumen_tecnico_texto(activo["ticker"], activo["nombre"])
        lineas_resumen.append(linea)

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
