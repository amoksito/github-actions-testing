import os
import requests
import yfinance as yf
import matplotlib

# Configurar backend sin interfaz gráfica para GitHub Actions
matplotlib.use("Agg")
import mplfinance as mpf
import io

# --- Configuración ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def enviar_mensaje(texto):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texto}
    requests.post(url, json=payload)


def enviar_grafico(buffer, caption):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    buffer.seek(0)
    files = {"photo": buffer}
    data = {"chat_id": CHAT_ID, "caption": caption}
    requests.post(url, files=files, data=data)


def generar_grafico_pro(ticker, nombre):
    try:
        # 1. Descargar datos (3 meses para ver detalle de velas)
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)

        if df.empty:
            print(f"Vacío: {ticker}")
            return

        # Limpieza de datos (a veces yfinance trae MultiIndex en columnas)
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.droplevel(1)

        # 2. Configurar el estilo y guardar en memoria
        buf = io.BytesIO()

        # mpf.plot hace toda la magia:
        # type='candle': Gráfico de velas
        # mav=(20, 50): Dibuja medias móviles de 20 y 50 días
        # volume=True: Agrega panel de volumen abajo
        # style='yahoo': Estilo clásico verde/rojo (o prueba 'nightclouds' para oscuro)
        mpf.plot(
            df,
            type="candle",
            mav=(20, 50),
            volume=True,
            title=f"\n{nombre} ({ticker})",
            style="yahoo",
            savefig=dict(fname=buf, dpi=100, pad_inches=0.25),
        )

        # 3. Enviar
        enviar_grafico(buf, f"📊 {nombre} - Velas + MA20/50")
        print(f"Enviado: {ticker}")

        # Liberar memoria
        buf.close()

    except Exception as e:
        print(f"Error en {ticker}: {e}")
        enviar_mensaje(f"⚠️ Error gráfico {ticker}: {str(e)}")


def main():
    if not TOKEN or not CHAT_ID:
        print("Faltan secretos de Telegram.")
        return

    enviar_mensaje("🔎 Reporte de Mercado: Iniciando análisis técnico...")

    activos = [
        {"ticker": "SPY", "nombre": "S&P 500"},
        {"ticker": "QQQ", "nombre": "Nasdaq 100"},
        {"ticker": "EWZ", "nombre": "Brasil ETF"},
        {"ticker": "GC=F", "nombre": "Oro Futuros"},
        {"ticker": "SI=F", "nombre": "Plata Futuros"},
    ]

    for activo in activos:
        generar_grafico_pro(activo["ticker"], activo["nombre"])

    enviar_mensaje("✅ Reporte finalizado.")


if __name__ == "__main__":
    main()
