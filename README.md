# Calculadora de Valor Intrínseco

Esta herramienta permite calcular el valor intrínseco de las acciones utilizando datos financieros en tiempo real. Está compuesta por un servidor proxy local en Python y una interfaz frontend en HTML/JS.

---

## ⚙️ Cómo Funciona el Servidor

El servidor (`server.py`) es un servidor HTTP local y proxy de datos construido con el módulo estándar de Python `http.server`. 

Sus principales funciones son:
1. **Servidor Web Estático**: Sirve la interfaz de usuario (el archivo HTML local) cuando el usuario accede a la ruta raíz `/` o `/index.html`.
2. **Proxy de Datos Financieros**: Resuelve el problema de CORS (Cross-Origin Resource Sharing) que impide a los navegadores hacer peticiones directas a APIs financieras. Utiliza la librería `yfinance` para hacer *scraping* y obtener datos fundamentales de las acciones directamente desde el backend.
3. **Autoinstalación de Dependencias**: Si detecta que la librería `yfinance` no está instalada en el sistema, la instala automáticamente usando `pip` de manera silenciosa durante la primera ejecución.

---

## 📡 Documentación de la API

El servidor expone un endpoint principal para el consumo de datos desde el frontend:

### `GET /quote`

Obtiene la información fundamental y el precio en tiempo real de una acción (*ticker*).

**Parámetros de Consulta (Query Params):**
- `symbol` o `ticker` (Requerido): El identificador de la acción en la bolsa (por ejemplo: `AAPL`, `MSFT`, `GGAL.BA`).

**Respuesta Exitosa (HTTP 200 OK):**
Devuelve un objeto JSON estructurado con los datos requeridos para los diferentes modelos de valoración.

```json
{
  "quoteResponse": {
    "result": [
      {
        "longName": "Apple Inc.",
        "symbol": "AAPL",
        "sector": "Technology",
        "regularMarketPrice": 175.50,
        "epsTrailingTwelveMonths": 6.13,
        "trailingPE": 28.5,
        "freeCashflow": 104500000000,
        "sharesOutstanding": 15550000000,
        "regularMarketChangePercent": 1.2,
        "beta": 1.25,
        "earningsGrowth": 0.05
      }
    ],
    "error": null
  }
}
```

**Respuestas de Error:**
- `HTTP 400 Bad Request`: Si no se incluye el parámetro `symbol`.
- `HTTP 404 Not Found`: Si la acción no existe o si `yfinance` no pudo obtener el precio de esa acción.

---

## 📊 Modelos de Valoración Incluidos

La calculadora aplica de forma automática cuatro modelos de valoración distintos para ofrecer una perspectiva completa del valor de la acción:

### 1. Fórmula de Graham (Benjamin Graham)
- **Fórmula Base:** `V = EPS × (8.5 + 2g)`
- **¿Para qué sirve?:** Ideal para identificar "empresas de valor" (Value Investing). 
- **Mejor aplicado en:** Empresas maduras, consolidadas y estables que tengan ganancias regulares y predecibles. No es confiable para empresas tecnológicas de crecimiento explosivo o startups sin beneficios.

### 2. Flujo de Caja Descontado / DCF (John Burr Williams)
- **Fórmula Base:** `V = Σ FCF(t)/(1+WACC)^t + Valor Terminal`
- **¿Para qué sirve?:** Calcula el valor presente de todos los flujos de caja libre (Free Cash Flow) que la empresa generará en el futuro descontados a la tasa WACC.
- **Mejor aplicado en:** Empresas con flujos de caja predecibles, constantes y con un historial financiero sólido a largo plazo (ej. servicios públicos, consumo masivo). No funciona bien si el FCF actual es negativo o muy volátil.

### 3. "Owner Earnings" (Modelo estilo Warren Buffett)
- **Fórmula Base:** Combina `EPS × Múltiplo(basado en ROE)` y el crecimiento proyectado del *Book Value* a 10 años.
- **¿Para qué sirve?:** Valora negocios teniendo en cuenta el Retorno sobre el Capital (ROE) y el patrimonio.
- **Mejor aplicado en:** Empresas con un "foso económico" (ventaja competitiva duradera), alto y constante ROE (usualmente mayor al 15-20%), y que generan consistentemente ganancias para sus accionistas.

### 4. Método PEG (Peter Lynch)
- **Fórmula Base:** `Precio Justo = EPS × g` (Asume que una empresa está valorada justamente cuando su P/E Ratio es igual a su crecimiento, es decir $PEG = 1$).
- **¿Para qué sirve?:** Relaciona el múltiplo que paga el mercado (PER) con el crecimiento esperado de las ganancias de la empresa.
- **Mejor aplicado en:** Empresas de alto crecimiento ("Growth stocks"). Permite justificar por qué una empresa tecnológica con un P/E alto puede seguir siendo una buena inversión si su tasa de crecimiento también es excepcionalmente alta.

---

## 📖 Manual de Usuario

### 1. Iniciar el Servidor
Para usar la calculadora, primero necesitas ejecutar el backend en tu computadora. Abre tu terminal de comandos, navega a la carpeta del proyecto y ejecuta:

```bash
python3 server.py
```

*Nota: La primera vez que lo inicies, puede tardar un poco más si el sistema necesita instalar automáticamente la librería `yfinance`.*

### 2. Abrir la Aplicación
Una vez que veas en la terminal un cartel indicando `✅ Servidor en http://localhost:8765`, abre tu navegador de internet (Chrome, Safari, Edge, etc.) e ingresa a la siguiente dirección:

[http://localhost:8765](http://localhost:8765)

### 3. Usar la Calculadora
1. En la página principal, busca el campo de texto para **Buscar acción / Ticker**.
2. Ingresa el símbolo bursátil de la empresa que querés analizar (por ejemplo, `KO` para Coca-Cola) y presiona **Enter** o haz clic en el botón de buscar.
3. La aplicación obtendrá automáticamente los datos financieros actualizados y presentará el cálculo del **Valor Intrínseco**, indicándote si el precio de mercado actual representa una sobrevaloración o una oportunidad de compra de acuerdo a los modelos cargados.

### 4. Detener el Servidor
Cuando hayas terminado, puedes apagar el servidor volviendo a la pantalla de tu terminal y presionando la combinación de teclas `Ctrl + C`. Verás el mensaje `⛔ Servidor detenido.` confirmando que se cerró correctamente.