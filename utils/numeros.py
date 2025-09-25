"""Utilities to convert numbers into Spanish words for monetary amounts."""
from decimal import Decimal, ROUND_HALF_UP

UNIDADES = [
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve"
]
DECENAS = [
    "", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"
]
CENTENAS = [
    "", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"
]


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _convert_group(number: int) -> str:
    """Convert a number from 0 to 999 into words."""
    if number == 0:
        return "cero"
    if number == 100:
        return "cien"

    words = []
    hundreds = number // 100
    tens_units = number % 100
    tens = tens_units // 10
    units = tens_units % 10

    if hundreds:
        words.append(CENTENAS[hundreds])

    if tens_units:
        if tens_units < 20:
            words.append(UNIDADES[tens_units])
        else:
            decena = DECENAS[tens]
            if units:
                if tens == 2:
                    words.append(f"veinti{UNIDADES[units]}")
                else:
                    words.append(f"{decena} y {UNIDADES[units]}")
            else:
                words.append(decena)
    return " ".join(words).strip()


def _convert_thousands(number: int) -> str:
    millions = number // 1_000_000
    thousands = (number % 1_000_000) // 1_000
    remainder = number % 1_000

    parts = []
    if millions:
        if millions == 1:
            parts.append("un millon")
        else:
            parts.append(f"{_convert_group(millions)} millones")

    if thousands:
        if thousands == 1:
            parts.append("mil")
        else:
            parts.append(f"{_convert_group(thousands)} mil")

    if remainder:
        parts.append(_convert_group(remainder))

    if not parts:
        return "cero"
    return " ".join(parts).strip()


def numero_a_letras(valor, moneda="soles", centimos_label="centimos") -> str:
    """Convierte un numero en texto en espanol para comprobantes."""
    dec = _to_decimal(valor)
    entero = int(dec)
    centimos = int((dec - Decimal(entero)) * 100)

    entero_txt = _convert_thousands(entero)
    entero_txt = entero_txt.replace("uno mil", "un mil")
    if entero == 1:
        moneda_txt = "sol"
    else:
        moneda_txt = moneda if moneda.endswith("s") else f"{moneda}s"

    cent_txt = f"{centimos:02d}/100"

    resultado = f"{entero_txt} con {cent_txt} {moneda_txt}".strip()
    return resultado.upper()
