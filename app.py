import itertools
import re
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Generador de tablas de verdad", page_icon="🧠", layout="wide")
st.title("🧠 Generador de tablas de verdad")
st.write("Escribe una proposición lógica y obtén su tabla de verdad.")

st.markdown("""
**Operadores disponibles**
- `¬p` o `~p`: negación
- `p ∧ q` o `p & q`: conjunción
- `p ∨ q` o `p | q`: disyunción
- `p ⊕ q` o `p ^ q`: disyunción exclusiva
- `p → q` o `p -> q`: implicación
- `p ↔ q` o `p <-> q`: bicondicional
- Paréntesis: `(p ∧ q) → r`
""")
examples = ["(p ∧ q) → r", "p ∨ ¬q", "p ↔ q", "p ⊕ q"]
example = st.selectbox("Ejemplos", examples)
expression = st.text_input("Expresión lógica", value=example)

OPS = {"IFF": 1, "IMP": 2, "OR": 3, "XOR": 4, "AND": 5, "NOT": 6}
RIGHT_ASSOC = {"IMP", "NOT"}

def tokenize(expr):
    s = expr.strip()
    for old, new in [("<->"," IFF "),("↔"," IFF "),("->"," IMP "),("→"," IMP "),
                     ("⊕"," XOR "),("^"," XOR "),("∧"," AND "),("&"," AND "),
                     ("∨"," OR "),("|"," OR "),("¬"," NOT "),("~"," NOT "),("!"," NOT ")]:
        s = s.replace(old, new)
    tokens = re.findall(r"[A-Za-z]\w*|\(|\)", s)
    if not tokens or re.sub(r"\s+", "", "".join(tokens)).lower() != re.sub(r"\s+", "", s).lower():
        raise ValueError("Hay símbolos no reconocidos. Revisa la expresión.")
    out = []
    for t in tokens:
        u = t.upper()
        if u in OPS: out.append(u)
        elif t in ("(", ")"): out.append(t)
        else: out.append(t)
    return out

def to_rpn(tokens):
    out, stack = [], []
    expect = True
    for t in tokens:
        if t in OPS:
            if t == "NOT":
                if not expect: raise ValueError("Usa la negación antes de una variable, por ejemplo ¬p.")
            elif expect: raise ValueError("Falta una proposición antes de un operador.")
            while stack and stack[-1] in OPS:
                top = stack[-1]
                if OPS[top] > OPS[t] or (OPS[top] == OPS[t] and t not in RIGHT_ASSOC):
                    out.append(stack.pop())
                else: break
            stack.append(t); expect = True
        elif t == "(":
            if not expect: raise ValueError("Falta un operador antes del paréntesis.")
            stack.append(t); expect = True
        elif t == ")":
            if expect: raise ValueError("Hay un paréntesis vacío o una expresión incompleta.")
            while stack and stack[-1] != "(": out.append(stack.pop())
            if not stack: raise ValueError("Hay un paréntesis de cierre sin apertura.")
            stack.pop(); expect = False
            while stack and stack[-1] == "NOT": out.append(stack.pop())
        else:
            if not expect: raise ValueError(f"Falta un operador antes de {t}.")
            out.append(t); expect = False
            while stack and stack[-1] == "NOT": out.append(stack.pop())
    if expect: raise ValueError("La expresión está incompleta.")
    while stack:
        t = stack.pop()
        if t == "(": raise ValueError("Falta cerrar un paréntesis.")
        out.append(t)
    return out

def evaluate(rpn, values):
    stck = []
    for t in rpn:
        if t == "NOT":
            if not stck: raise ValueError("Falta una proposición para negar.")
            stck.append(not stck.pop())
        elif t in {"AND","OR","XOR","IMP","IFF"}:
            if len(stck) < 2: raise ValueError("Expresión incompleta.")
            b, a = stck.pop(), stck.pop()
            stck.append({"AND": lambda: a and b, "OR": lambda: a or b,
                         "XOR": lambda: a != b, "IMP": lambda: (not a) or b,
                         "IFF": lambda: a == b}[t]())
        else:
            stck.append(values[t])
    if len(stck) != 1: raise ValueError("No se pudo interpretar la expresión.")
    return stck[0]

if st.button("Generar tabla", type="primary"):
    try:
        tokens = tokenize(expression)
        rpn = to_rpn(tokens)
        variables = sorted({t for t in tokens if t not in OPS and t not in ("(", ")")})
        if not variables: st.error("Incluye al menos una variable, como p o q.")
        elif len(variables) > 8: st.error("Usa máximo 8 variables.")
        else:
            rows = []
            for combo in itertools.product([True, False], repeat=len(variables)):
                vals = dict(zip(variables, combo))
                result = evaluate(rpn, vals)
                row = {v: ("V" if vals[v] else "F") for v in variables}
                row[expression] = "V" if result else "F"
                rows.append(row)
            df = pd.DataFrame(rows)
            st.subheader("Tabla de verdad")
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("Descargar tabla en CSV", df.to_csv(index=False).encode("utf-8-sig"),
                               "tabla_de_verdad.csv", "text/csv")
            results = [r[expression] for r in rows]
            if all(x == "V" for x in results): st.success("Tautología: siempre es verdadera.")
            elif all(x == "F" for x in results): st.warning("Contradicción: siempre es falsa.")
            else: st.info("Contingencia: puede ser verdadera o falsa.")
    except Exception as e:
        st.error(f"No se pudo generar la tabla: {e}")

with st.expander("Ejemplo: p ∧ q"):
    st.dataframe(pd.DataFrame([
        {"p":"V","q":"V","p ∧ q":"V"}, {"p":"V","q":"F","p ∧ q":"F"},
        {"p":"F","q":"V","p ∧ q":"F"}, {"p":"F","q":"F","p ∧ q":"F"}
    ]), use_container_width=True, hide_index=True)
st.caption("Proyecto educativo. V = verdadero; F = falso.")
