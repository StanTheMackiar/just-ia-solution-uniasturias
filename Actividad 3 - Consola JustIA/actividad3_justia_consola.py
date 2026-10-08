"""
JustIA - Actividad 3: primera capa de interaccion por consola
Caso practico Unidad 1 - IA aplicada al desarrollo de software
Autor: Stanly Leon Calle Samper

Simula la entrada del sistema: el usuario escribe una pregunta, carga un
documento (PDF o TXT) y pide una clasificacion. Por debajo usa el diccionario
y la funcion predecir_categoria() de la actividad 2.

Lo que quise que quedara claro desde esta primera version:
  - La respuesta es una ORIENTACION PRELIMINAR, nunca un concepto juridico.
  - Cada interaccion queda registrada (registros/justia_registro.jsonl) con la
    entrada, la categoria, los terminos que la justifican y la version del
    diccionario. Eso es la trazabilidad que pidio la mesa interfacultades.
  - El practicante puede aceptar o REFUTAR la sugerencia y su correccion
    tambien queda en el registro.

Uso: python3 actividad3_justia_consola.py
Para leer PDF necesita pypdf (pip install pypdf); los .txt funcionan sin nada.
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent / "Actividad 2 - Diccionario juridico"))

from actividad2_clasificador import cargar_diccionario, predecir_categoria  # noqa: E402
RUTA_REGISTRO = BASE / "registros" / "justia_registro.jsonl"

AVISO = ("Aviso: JustIA da orientacion preliminar y general. No reemplaza la asesoria\n"
         "de un practicante ni de un abogado; toda respuesta la revisa una persona.")

# Respuestas simuladas por area. En una version real esto saldria de una base
# de preguntas frecuentes validada por los docentes de Derecho, con su fuente.
RESPUESTAS = {
    "familia": ("Su consulta parece de DERECHO DE FAMILIA. Temas como cuota alimentaria o\n"
                "custodia suelen intentarse primero por conciliacion (Comisaria o ICBF).\n"
                "Tenga a la mano registro civil de los hijos y soportes de gastos."),
    "laboral": ("Su consulta parece de DERECHO LABORAL. Reuna contrato (si lo hay), colillas\n"
                "de pago, carta de terminacion y afiliaciones. Puede acudir al inspector\n"
                "de trabajo antes de una demanda."),
    "penal": ("Su consulta parece de DERECHO PENAL. Si fue victima de un delito puede\n"
              "denunciar ante la Fiscalia (presencial o en linea). Guarde pruebas:\n"
              "fotos, mensajes, comprobantes."),
    "civil": ("Su consulta parece de DERECHO CIVIL. Revise el contrato o documento que\n"
              "respalda la obligacion (arriendo, pagare, escritura) y los pagos hechos."),
    "constitucional": ("Su consulta puede tramitarse con un mecanismo constitucional (derecho de\n"
                       "peticion o accion de tutela). La tutela procede cuando se vulnera un\n"
                       "derecho fundamental y no hay otro medio eficaz."),
    "administrativo": ("Su consulta parece de DERECHO ADMINISTRATIVO (tramite o decision de una\n"
                       "entidad publica). Revise la fecha de notificacion: los recursos tienen\n"
                       "plazos cortos."),
    "victimas_conflicto": ("Su consulta se relaciona con VICTIMAS DEL CONFLICTO ARMADO. El primer\n"
                           "paso suele ser declarar ante el Ministerio Publico (Personeria,\n"
                           "Defensoria o Procuraduria) para la inclusion en el RUV."),
    "genero": ("Su consulta se relaciona con VIOLENCIA CONTRA LA MUJER. Puede pedir medidas\n"
               "de proteccion en la Comisaria de Familia. Linea 155 (orientacion) y\n"
               "123 si hay peligro inmediato."),
}

PALABRAS_RIESGO = ("amenaza", "matar", "golpe", "peligro", "arma", "violencia")


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def registrar(evento: dict):
    """Agrega una linea al registro JSONL (una linea = una interaccion)."""
    RUTA_REGISTRO.parent.mkdir(exist_ok=True)
    evento["fecha_hora"] = datetime.now().isoformat(timespec="seconds")
    with open(RUTA_REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


def resumen_entrada(texto: str) -> dict:
    # No guardo el texto completo: solo un extracto y un hash para poder
    # verificar despues que se trata del mismo documento (minimizacion de datos).
    return {"extracto": texto[:120], "sha256": hashlib.sha256(texto.encode()).hexdigest()[:16]}


def leer_documento(ruta: Path) -> str:
    if ruta.suffix.lower() == ".txt":
        return ruta.read_text(encoding="utf-8", errors="ignore")
    if ruta.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("Para leer PDF instale pypdf: pip install pypdf")
        lector = PdfReader(str(ruta))
        texto = "\n".join((p.extract_text() or "") for p in lector.pages)
        if not texto.strip():
            # PDF escaneado (imagen): aqui iria OCR, que no esta en esta version
            raise RuntimeError("El PDF no tiene texto extraible (posible escaneo). Requiere OCR.")
        return texto
    raise RuntimeError("Formato no soportado. Use .pdf o .txt")


def mostrar_resultado(r: dict):
    print("-" * 66)
    if r["categoria"] == "sin_clasificar":
        print(" Area sugerida : SIN CLASIFICAR -> se envia a un practicante")
    else:
        print(f" Area sugerida : {r['categoria'].upper()}   (confianza {r['confianza']:.0%})")
    if r["terminos"]:
        print(" Por que       :", "; ".join(f"{c}: {', '.join(t)}" for c, t in r["terminos"].items()))
    if r["puntajes"]:
        print(" Puntajes      :", ", ".join(f"{c}={p}" for c, p in r["puntajes"].items()))
    if r["revision_humana"]:
        print(" ! Revision humana obligatoria:", r["motivo_revision"])
    for a in r["alertas"]:
        print(f" ! Termino sensible: {a['tipo'].replace('_', ' ')} ({a['fuente']})")
    print(f" Diccionario v{r['version_diccionario']}")
    print("-" * 66)


def validar_practicante(r: dict) -> dict:
    """El practicante acepta o refuta la sugerencia. Queda registrado."""
    resp = input("[Practicante] ¿De acuerdo con la clasificacion? (s/n, Enter = omitir): ").strip().lower()
    if resp == "s":
        return {"estado": "aceptada"}
    if resp == "n":
        cats = list(cargar_diccionario()["categorias"].keys())
        for i, c in enumerate(cats, 1):
            print(f"   {i}. {c}")
        sel = input("   Area correcta (numero): ").strip()
        correcta = cats[int(sel) - 1] if sel.isdigit() and 1 <= int(sel) <= len(cats) else "no_indicada"
        motivo = input("   Motivo de la correccion: ").strip()
        print("   Correccion guardada. Servira para revisar el diccionario.")
        return {"estado": "refutada", "categoria_correcta": correcta, "motivo": motivo}
    return {"estado": "pendiente"}


# ---------------------------------------------------------------------------
# opciones del menu
# ---------------------------------------------------------------------------
def opcion_pregunta():
    pregunta = input("Escriba su pregunta: ").strip()
    if len(pregunta) < 10:
        print("La pregunta es muy corta, cuentenos un poco mas de su situacion.")
        return
    r = predecir_categoria(pregunta)
    mostrar_resultado(r)
    if any(p in pregunta.lower() for p in PALABRAS_RIESGO) or r["alertas"]:
        print(" >> Si esta en peligro llame al 123. Orientacion a mujeres: Linea 155.")
    if r["categoria"] in RESPUESTAS and not r["revision_humana"]:
        print("\nRespuesta preliminar (simulada):")
        print(RESPUESTAS[r["categoria"]])
    else:
        print("\nRespuesta preliminar: su caso sera revisado por un practicante del")
        print("consultorio antes de darle una orientacion.")
    print()
    validacion = validar_practicante(r)
    registrar({"tipo": "pregunta", "entrada": resumen_entrada(pregunta),
               "categoria": r["categoria"], "confianza": r["confianza"],
               "terminos": r["terminos"], "alertas": [a["tipo"] for a in r["alertas"]],
               "version_diccionario": r["version_diccionario"], "validacion": validacion})


def opcion_cargar(estado: dict):
    ruta = Path(input("Ruta del documento (.pdf o .txt): ").strip().strip('"'))
    if not ruta.is_absolute():
        ruta = BASE / ruta
    if not ruta.exists():
        print("No encuentro el archivo:", ruta)
        return
    try:
        texto = leer_documento(ruta)
    except RuntimeError as e:
        print("No se pudo leer:", e)
        return
    estado["documento"] = {"nombre": ruta.name, "texto": texto}
    print(f"Documento cargado: {ruta.name} ({len(texto)} caracteres)")
    print("Vista previa:", " ".join(texto.split())[:160], "...")
    registrar({"tipo": "carga_documento", "archivo": ruta.name,
               "entrada": resumen_entrada(texto)})


def opcion_clasificar(estado: dict):
    doc = estado.get("documento")
    if not doc:
        print("Primero cargue un documento (opcion 2).")
        return
    print(f"Clasificando '{doc['nombre']}'...")
    r = predecir_categoria(doc["texto"])
    mostrar_resultado(r)
    validacion = validar_practicante(r)
    registrar({"tipo": "clasificacion_documento", "archivo": doc["nombre"],
               "entrada": resumen_entrada(doc["texto"]), "categoria": r["categoria"],
               "confianza": r["confianza"], "terminos": r["terminos"],
               "alertas": [a["tipo"] for a in r["alertas"]],
               "version_diccionario": r["version_diccionario"], "validacion": validacion})


def opcion_registro(inicio_sesion: str):
    if not RUTA_REGISTRO.exists():
        print("Aun no hay registros.")
        return
    print(f"Registro de esta sesion ({RUTA_REGISTRO.name}):")
    with open(RUTA_REGISTRO, encoding="utf-8") as f:
        for linea in f:
            e = json.loads(linea)
            if e["fecha_hora"] < inicio_sesion:
                continue
            detalle = e.get("categoria", e.get("archivo", ""))
            val = e.get("validacion", {}).get("estado", "-")
            print(f"  {e['fecha_hora']} | {e['tipo']:<24} | {detalle:<24} | validacion: {val}")


# ---------------------------------------------------------------------------
# programa principal
# ---------------------------------------------------------------------------
def main():
    estado = {}
    inicio = datetime.now().isoformat(timespec="seconds")
    print("=" * 66)
    print("  JustIA - Consultorio Virtual Uniasturias (prototipo de consola)")
    print("=" * 66)
    print(AVISO)

    while True:
        print("\n  1. Hacer una pregunta legal")
        print("  2. Cargar un documento (PDF o TXT)")
        print("  3. Clasificar el documento cargado")
        print("  4. Ver registro de la sesion (trazabilidad)")
        print("  5. Salir")
        opcion = input("Seleccione una opcion: ").strip()

        if opcion == "1":
            opcion_pregunta()
        elif opcion == "2":
            opcion_cargar(estado)
        elif opcion == "3":
            opcion_clasificar(estado)
        elif opcion == "4":
            opcion_registro(inicio)
        elif opcion == "5":
            print("Sesion cerrada. Registro guardado en", RUTA_REGISTRO.relative_to(BASE))
            break
        else:
            print("Opcion no valida, intente de nuevo.")


if __name__ == "__main__":
    main()
