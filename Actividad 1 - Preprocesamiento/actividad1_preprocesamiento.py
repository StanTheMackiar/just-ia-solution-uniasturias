"""
JustIA - Actividad 1: preprocesamiento del corpus juridico
Caso practico Unidad 1 - IA aplicada al desarrollo de software
Autor: Stanly Leon Calle Samper

Que hace este script:
  1. Lee corpus_original.csv (62 fragmentos SIMULADOS de sentencias,
     normas, resoluciones y conceptos, todos con contexto colombiano).
  2. Limpia, tokeniza, quita stopwords y lematiza cada fragmento.
  3. Guarda el resultado en corpus_limpio.csv y corpus_limpio.json

Como correrlo:
  python3 actividad1_preprocesamiento.py
  python3 actividad1_preprocesamiento.py --motor reglas   (fuerza el lematizador propio)
  python3 actividad1_preprocesamiento.py --motor spacy    (exige spaCy + es_core_news_sm)

Nota sobre dependencias: el enunciado deja usar nltk, spaCy o re. Yo deje el
flujo principal solo con libreria estandar (re, unicodedata, csv, json) para
que corra en cualquier maquina sin instalar nada. Si spaCy y el modelo
es_core_news_sm estan instalados, el script los usa para lematizar porque su
lematizador es mas completo que el mio (pip install spacy &&
python -m spacy download es_core_news_sm).
"""

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
RUTA_ORIGINAL = BASE / "corpus_original.csv"
RUTA_LIMPIO_CSV = BASE / "corpus_limpio.csv"
RUTA_LIMPIO_JSON = BASE / "corpus_limpio.json"


# ---------------------------------------------------------------------------
# 1. STOPWORDS
# ---------------------------------------------------------------------------
# Parti de la lista tipica de stopwords en espanol (la misma idea de la de
# NLTK) pero la ajuste a mano para el dominio juridico:
#   - SAQUE "no", "sin", "ni", "nunca": en derecho la negacion cambia todo.
#     "despido SIN justa causa" no es lo mismo que "despido con justa causa".
#   - SAQUE "contra": aparece en "violencia contra la mujer", "recurso contra".
#   - AGREGUE palabras que salen en casi todos los documentos y no ayudan a
#     distinguir el area del derecho (articulo, ley, numero, senor, etc.).
STOPWORDS_BASE = """
a al algo algunas algunos ante antes aquel aquella aquellas aquellos aqui asi
aun aunque cada como con cual cuales cualquier cuando cuanto de del desde
donde dos durante e el ella ellas ello ellos en entre era eran es esa esas ese
eso esos esta estaba estado estan estar estas este esto estos fue fueron ha
habia han hasta hay la las le les lo los mas me mi mis mientras muy nos
nosotros o otra otras otro otros para pero poco por porque que quien quienes
se sea segun ser si sido sobre su sus tal tambien tan tanto te tiene tienen
toda todas todo todos tras tu tus u un una unas uno unos y ya yo
""".split()

STOPWORDS_DOMINIO = """
articulo art ley numero no. senor senora mediante dicho dicha presente
cual adaptado simulado simulada texto parrafo literal lit dentro debe deben
puede pueden caso usuario usuaria
""".split()

# palabras que NO se deben quitar aunque esten en listas genericas
NO_QUITAR = {"no", "sin", "ni", "nunca", "contra"}

STOPWORDS = (set(STOPWORDS_BASE) | set(STOPWORDS_DOMINIO)) - NO_QUITAR


# ---------------------------------------------------------------------------
# 2. LEMATIZADOR PROPIO (basado en lexicon + reglas)
# ---------------------------------------------------------------------------
# No es tan completo como spaCy, pero tiene dos ventajas para este caso:
#   a) es determinista y auditable: si un lema queda mal, se corrige en el
#      diccionario de abajo y queda registrado (trazabilidad).
#   b) conoce terminos juridicos que modelos generales lematizan mal, por
#      ejemplo "canones" -> "canon" o "conyuges" -> "conyuge".
# El lexicon lo arme revisando las palabras del corpus que las reglas
# generales no resolvian bien (corri el script, mire la salida y fui
# agregando). Las claves van CON tilde porque se lematiza antes de quitarlas.
LEXICON = {
    # verbos conjugados frecuentes en el corpus
    "fue": "ser", "fueron": "ser", "es": "ser", "son": "ser", "sea": "ser",
    "hubo": "haber", "ha": "haber", "han": "haber", "haya": "haber", "hayan": "haber",
    "tiene": "tener", "tienen": "tener", "tuvo": "tener",
    "hizo": "hacer", "hace": "hacer",
    "puede": "poder", "pueden": "poder",
    "debe": "deber", "deberá": "deber", "deben": "deber",
    "negó": "negar", "niega": "negar", "niegue": "negar", "nega": "negar",
    "relata": "relatar", "manifiesta": "manifestar", "solicita": "solicitar",
    "solicitan": "solicitar", "pide": "pedir", "acuerdan": "acordar",
    "incumplió": "incumplir", "aporta": "aportar", "otorga": "otorgar",
    "regula": "regular", "ordena": "ordenar", "ordenan": "ordenar",
    "declara": "declarar", "ampara": "amparar", "amparan": "amparar",
    "tutela": "tutela", "reconoce": "reconocer", "aprueba": "aprobar",
    "impone": "imponer", "condena": "condenar", "libra": "librar",
    "decreta": "decretar", "legaliza": "legalizar", "formula": "formular",
    "acepta": "aceptar", "recomienda": "recomendar", "recuerda": "recordar",
    "orienta": "orientar", "activa": "activar", "recibe": "recibir",
    "valora": "valorar", "controla": "controlar", "castiga": "castigar",
    "retiene": "retener", "destruyó": "destruir", "trabajaba": "trabajar",
    "sale": "salir", "atacó": "atacar", "aplica": "aplicar", "abre": "abrir",
    "prescribió": "prescribir", "recibió": "recibir", "suspendió": "suspender",
    "procede": "proceder", "proceden": "proceder", "prestar": "prestar",
    "afecta": "afectar", "contraríen": "contrariar", "juzgar": "juzgar",
    "rindió": "rendir", "transfirió": "transferir", "sufrió": "sufrir",
    "asumió": "asumir", "probó": "probar", "pagó": "pagar", "dio": "dar",
    "impuso": "imponer", "considera": "considerar", "resuelva": "resolver",
    "entiende": "entender", "entienden": "entender", "consideran": "considerar",
    "requiere": "requerir", "prioriza": "priorizar", "cambió": "cambiar",
    "corresponde": "corresponder", "consignó": "consignar", "deberán": "deber",
    "incurrirá": "incurrir", "sustraiga": "sustraer", "hayan": "haber",
    "sufrido": "sufrir", "ocurridos": "ocurrir", "ocurridas": "ocurrir",
    "encuentra": "encontrar", "responde": "responder", "implique": "implicar",
    "excede": "exceder", "vulneró": "vulnerar", "declaró": "declarar",
    "incurrió": "incurrir", "deja": "dejar", "representa": "representar",
    "remite": "remitir", "habeas": "habeas", "intereses": "interés",
    "interés": "interés", "quitó": "quitar", "quita": "quitar", "rompió": "romper",
    "da": "dar", "echaron": "echar", "pagaron": "pagar", "pagan": "pagar", "través": "través", "país": "país", "jamás": "jamás",
    # participios que funcionan como adjetivos clave
    "despedido": "despedir", "despedida": "despedir",
    "desvinculada": "desvincular", "desvinculado": "desvincular",
    "vinculado": "vincular", "vinculó": "vincular",
    "desaparecida": "desaparecer", "desaparecido": "desaparecer",
    "despojada": "despojar", "despojado": "despojar",
    "adeudados": "adeudar", "conciliado": "conciliar", "denunciados": "denunciar",
    "suscrito": "suscribir", "pactada": "pactar", "dejados": "dejar",
    "impuesta": "imponer", "debidos": "deber", "destinados": "destinar",
    # sustantivos con plural irregular o terminos juridicos
    "cánones": "canon", "canones": "canon", "cónyuges": "cónyuge",
    "jueces": "juez", "menores": "menor", "mujeres": "mujer", "padres": "padre",
    "hijos": "hijo", "hijas": "hija", "niñas": "niña", "niños": "niño",
    "adolescentes": "adolescente", "derechos": "derecho", "bienes": "bien",
    "valores": "valor", "perjuicios": "perjuicio", "alimentos": "alimento",
    "víctimas": "víctima", "victimas": "víctima", "herederos": "heredero",
    "compañeros": "compañero", "ascendientes": "ascendiente",
    "descendientes": "descendiente", "días": "día", "meses": "mes",
    "años": "año", "costumbres": "costumbre", "usos": "uso",
    "recursos": "recurso", "aportes": "aporte", "cargos": "cargo",
    "objetos": "objeto", "instrumentos": "instrumento", "documentos": "documento",
    "finanzas": "finanzas", "dd.hh": "derecho humano", "dih": "dih",
    "eps": "eps", "arl": "arl", "icbf": "icbf", "ppt": "ppt", "ruv": "ruv",
    "gaula": "gaula", "sisbén": "sisbén", "colpensiones": "colpensiones",
    "redes": "red", "sociales": "social", "personales": "personal",
    "fundamentales": "fundamental", "graves": "grave", "ilegales": "ilegal",
    "civiles": "civil", "legales": "legal", "materiales": "material",
    "morales": "moral", "ocultos": "oculto", "dominicales": "dominical",
    "nocturnos": "nocturno", "religioso": "religioso", "garantías": "garantía",
    "medidas": "medida", "protección": "protección", "condiciones": "condición",
}

# Reglas de sufijos (se aplican en orden; la primera que coincide gana).
# Son pocas a proposito: prefiero dejar una palabra sin lematizar a dañarla.
REGLAS_SUFIJOS = [
    (r"(\w{3,})ciones$", r"\1ción"),   # resoluciones -> resolución
    (r"(\w{2,})siones$", r"\1sión"),   # pensiones -> pensión, lesiones -> lesión
    (r"(\w{2,})ces$", r"\1z"),         # veces -> vez
    # esta va antes que la de vocal+s, si no "autoridades" queda "autoridade"
    (r"(\w{2,}[aeiouáéíóú][dlnrj])es$", r"\1"),  # autoridades -> autoridad, laborales -> laboral
    (r"(\w{3,}[aeiouáéó])s$", r"\1"),  # contratos -> contrato
]


def lematizar_reglas(token: str) -> str:
    """Lematiza una palabra con el lexicon y, si no esta, con reglas."""
    if token in LEXICON:
        return LEXICON[token]
    for patron, reemplazo in REGLAS_SUFIJOS:
        if re.fullmatch(patron, token):
            return re.sub(patron, reemplazo, token)
    return token


# ---------------------------------------------------------------------------
# 3. spaCy (opcional)
# ---------------------------------------------------------------------------
_NLP = None


def cargar_spacy():
    """Intenta cargar spaCy. Si no esta instalado devuelve None sin romper."""
    global _NLP
    if _NLP is not None:
        return _NLP
    try:
        import spacy  # noqa: import dentro de la funcion a proposito
        _NLP = spacy.load("es_core_news_sm", disable=["parser", "ner"])
    except Exception:
        _NLP = None
    return _NLP


# ---------------------------------------------------------------------------
# 4. FUNCIONES DEL FLUJO
# ---------------------------------------------------------------------------
def limpieza_basica(texto: str) -> str:
    """Minusculas, quita URLs, numeros y simbolos. OJO: NO quita tildes aun.

    Las tildes se quitan al final porque el lematizador las necesita
    ("negó" es verbo en pasado; "nego" sin tilde no existe y se pierde).
    """
    texto = texto.lower()
    texto = re.sub(r"https?://\S+|www\.\S+", " ", texto)       # enlaces
    texto = texto.replace("dd.hh.", "dd.hh")                    # sigla de derechos humanos
    # "No. 045" es numero, no negacion; si no lo cambio aqui despues queda
    # un "no" que confunde (y ese "no" lo protegi en las stopwords)
    texto = re.sub(r"\bno\.\s*(?=\d)", " numero ", texto)
    texto = re.sub(r"\$\s?[\d\.,]+", " ", texto)                # valores en pesos
    texto = re.sub(r"\d+", " ", texto)                          # numeros (fechas, articulos)
    texto = re.sub(r"[^a-záéíóúüñ\.\s]", " ", texto)            # simbolos: ( ) – → ! ? " / etc.
    texto = re.sub(r"(?<!dd)\.(?!hh)", " ", texto)              # puntos sueltos
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar(texto: str) -> list:
    """Tokenizacion con expresion regular: palabras de 2 o mas letras."""
    return re.findall(r"[a-záéíóúüñ][a-záéíóúüñ\.]*[a-záéíóúüñ]", texto)


def quitar_tildes(palabra: str) -> str:
    """Quita tildes pero conserva la ñ (sin ñ 'año' quedaria como 'ano')."""
    palabra = palabra.replace("ñ", "\u0001")
    nfkd = unicodedata.normalize("NFKD", palabra)
    sin = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin.replace("\u0001", "ñ")


def lematizar(tokens: list, motor: str) -> list:
    if motor == "spacy":
        nlp = cargar_spacy()
        doc = nlp(" ".join(tokens))
        return [t.lemma_.lower() for t in doc]
    lemas = []
    for t in tokens:
        lemas.extend(lematizar_reglas(t).split())  # "dd.hh" -> "derecho humano"
    return lemas


def procesar(texto: str, motor: str = "reglas") -> dict:
    """Corre el flujo completo y devuelve cada etapa (sirve para auditar)."""
    limpio = limpieza_basica(texto)
    tokens = tokenizar(limpio)
    sin_stop = [t for t in tokens if quitar_tildes(t) not in STOPWORDS]
    lemas = lematizar(sin_stop, motor)
    lemas = [quitar_tildes(l) for l in lemas]
    lemas = [l for l in lemas if l not in STOPWORDS and len(l) > 1]
    return {
        "texto_limpio": limpio,
        "tokens": tokens,
        "tokens_sin_stopwords": sin_stop,
        "lemas": lemas,
    }


def elegir_motor(preferencia: str) -> str:
    if preferencia == "reglas":
        return "reglas"
    if cargar_spacy() is not None:
        return "spacy"
    if preferencia == "spacy":
        raise SystemExit("spaCy o es_core_news_sm no estan instalados.")
    return "reglas"


def main():
    parser = argparse.ArgumentParser(description="Preprocesamiento corpus JustIA")
    parser.add_argument("--motor", choices=["auto", "reglas", "spacy"], default="auto")
    args = parser.parse_args()
    motor = elegir_motor(args.motor)

    with open(RUTA_ORIGINAL, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    salida = []
    total_tokens, total_lemas = 0, 0
    for fila in filas:
        r = procesar(fila["texto"], motor)
        total_tokens += len(r["tokens"])
        total_lemas += len(r["lemas"])
        salida.append({
            "id": fila["id"],
            "categoria_esperada": fila["categoria_esperada"],
            "tipo_documento": fila["tipo_documento"],
            "referencia": fila["referencia"],
            "texto_original": fila["texto"],
            "texto_limpio": r["texto_limpio"],
            "num_tokens": len(r["tokens"]),
            "num_lemas": len(r["lemas"]),
            "lemas": " ".join(r["lemas"]),
            "motor_lematizacion": motor,
        })

    campos = list(salida[0].keys())
    with open(RUTA_LIMPIO_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(salida)
    with open(RUTA_LIMPIO_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    vocab = {l for s in salida for l in s["lemas"].split()}
    print(f"Motor de lematizacion: {motor}")
    print(f"Fragmentos procesados: {len(salida)}")
    print(f"Tokens antes de stopwords: {total_tokens}")
    print(f"Lemas finales: {total_lemas} ({100 - total_lemas * 100 // total_tokens}% menos)")
    print(f"Vocabulario final (lemas unicos): {len(vocab)}")
    print(f"Guardado en: {RUTA_LIMPIO_CSV.name} y {RUTA_LIMPIO_JSON.name}")
    ejemplo = salida[0]
    print("\nEjemplo", ejemplo["id"])
    print("  original:", ejemplo["texto_original"][:110], "...")
    print("  lemas   :", ejemplo["lemas"][:110], "...")


if __name__ == "__main__":
    main()
