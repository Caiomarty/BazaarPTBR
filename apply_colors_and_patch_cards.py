#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path

# ===================== CONFIGURE AQUI =====================
BASE = Path(r"C:\Users\gccai\OneDrive\Documentos\GitHub\BazaarPTBR")

TRANSLATIONS_FILE = BASE / "bazaar_translations.txt"  # seu arquivo "orig=traduzido"
CARDS_JSON_IN     = BASE / "cards.json"               # JSON de origem (em inglês)
CARDS_JSON_OUT    = BASE / "cards_translated.json"    # JSON de saída (com PT colorido)
# =========================================================

# Mapa: inglês -> saída colorida em PT
COLORED_MAP_EN_TO_PT = {
    "Burn":        "<color=#FE9200>Queimar</color>",
    "Burned":      "<color=#FE9200>Burned</color>",
    "Ammo":        "<color=#FFA500>Munição</color>",
    "Reload":      "<color=#FFA500>Recarregar</color>",

    "Shield":      "<color=#FFD700>Escudo</color>",
    "Shielding":   "<color=#FFD700>Shielding</color>",
    "Income":      "<color=#FFD700>Renda</color>",
    "Value":       "<color=#FFD700>Valor</color>",

    "Heal":        "<color=#33CC33>Curar</color>",
    "Health":      "<color=#33CC33>Vida</color>",
    "Max Health":  "<color=#33CC33>Vida Máxima</color>",
    "Healing":     "<color=#33CC33>Healing</color>",
    "Heals":       "<color=#33CC33>Curar</color>",
    "Regeneration":"<color=#33CC33>Regen</color>",
    "Poison":      "<color=#1BB950>Envenenar</color>",
    "Poisoned":    "<color=#1BB950>Envenenado</color>",
    "Crit Chance": "<color=#85ED92>Chance Crítica</color>",

    "Frozen":      "<color=#01CBFF>Congelado</color>",
    "Freeze":      "<color=#01CBFF>Congelar</color>",
    "Charge":      "<color=#01FFD5>Carregue</color>",
    "Cooldown":    "<color=#01FFD5>Recarga</color>",
    "Haste":       "<color=#01FFD5>Acelerar</color>",

    "Slow":        "<color=#AA9977>Desacelerar</color>",

    "Friend":      "<color=#B4AFE9>Amigo</color>",
    "Potion":      "<color=#B4AFE9>Poção</color>",
    "Property":    "<color=#B4AFE9>Propriedade</color>",
    "Tool":        "<color=#B4AFE9>Ferramenta</color>",
    "Vehicle":     "<color=#B4AFE9>Veículo</color>",
    "Weapon":      "<color=#B4AFE9>Arma</color>",
    "Weapons":     "<color=#B4AFE9>Armas</color>",
    "Core":        "<color=#B4AFE9>Core</color>",
    "Ingredient":  "<color=#B4AFE9>Ingrediente</color>",
    "Food":        "<color=#B4AFE9>Comida</color>",
    "Ray":         "<color=#B4AFE9>Raio</color>",
    "Non-":        "<color=#B4AFE9>não-</color>",
    "Properties":  "<color=#B4AFE9>Propriedades</color>",
    "small":       "<color=#B4AFE9>pequeno</color>",
    "medium":      "<color=#B4AFE9>médio</color>",
    "large":       "<color=#B4AFE9>grande</color>",
    "Merchant":    "<color=#B4AFE9>Mercante</color>",
    "Tools":       "<color=#B4AFE9>Ferramentas</color>",
}

# ---------- utilitários de cor/regex ----------
COLOR_BLOCK_RE = re.compile(r"<color=[^>]+>.*?</color>", re.IGNORECASE | re.DOTALL)
TAG_BLOCK_RE   = re.compile(r"<[^>]*>", re.DOTALL)        # qualquer <...>
BRACE_BLOCK_RE = re.compile(r"\{[^}]*\}", re.DOTALL)      # {...} placeholders

def strip_color_tags(text: str) -> str:
    return re.sub(r"</?color[^>]*>", "", text, flags=re.IGNORECASE)

def build_pt_plain_to_colored():
    """Gera mapa PT-simples -> PT-colorido a partir do COLORED_MAP_EN_TO_PT."""
    pt_map = {}
    for en, colored in COLORED_MAP_EN_TO_PT.items():
        pt_plain = strip_color_tags(colored)
        pt_map[pt_plain] = colored
    # ordenar por tamanho desc para evitar 'Arma' antes de 'Armas', etc.
    ordered = dict(sorted(pt_map.items(), key=lambda kv: len(kv[0]), reverse=True))
    return ordered

PT_PLAIN_TO_COLORED = build_pt_plain_to_colored()

def ranges_for_patterns(s, patterns):
    spans = []
    for pat in patterns:
        spans.extend(m.span() for m in pat.finditer(s))
    spans.sort()
    return spans

def is_in_any_range(idx, spans):
    for a, b in spans:
        if a <= idx < b:
            return True
    return False

def word_pat(term: str):
    # termos com espaço/hífen ficam como sequência literal; demais com \b
    if " " in term:
        return re.compile(re.escape(term), re.IGNORECASE)
    elif term.endswith("-"):
        return re.compile(re.escape(term), re.IGNORECASE)  # ex.: Non-
    else:
        return re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)

# pré-compila padrões (PT-plain e EN) ordenados por tamanho
PT_PATTERNS = [(k, word_pat(k)) for k in PT_PLAIN_TO_COLORED.keys()]
EN_PATTERNS = [(k, word_pat(k)) for k in sorted(COLORED_MAP_EN_TO_PT.keys(), key=len, reverse=True)]

def apply_colors_safely(text: str) -> str:
    """
    Aplica cor na tradução:
      1) substitui PT plain -> PT colorido
      2) se ainda restou keyword em inglês na tradução, aplica EN -> PT colorido
    Ignora trechos dentro de <color>...</color>, <...> e {...}.
    """
    if not text:
        return text

    ignore = ranges_for_patterns(text, [COLOR_BLOCK_RE, TAG_BLOCK_RE, BRACE_BLOCK_RE])

    def sub_outside(block_text: str, patterns, to_colored_fn):
        result = block_text
        for key, pat in patterns:
            def repl(m):
                start = m.start()
                if is_in_any_range(start, ignore):
                    return m.group(0)  # não altera
                return to_colored_fn(key)
            result = pat.sub(repl, result)
        return result

    # 1) PT plain -> PT colorido
    text = sub_outside(
        text,
        PT_PATTERNS,
        lambda pt_plain: PT_PLAIN_TO_COLORED[pt_plain]
    )

    # 2) EN -> PT colorido (fallback caso a tradução tenha deixado termos em inglês)
    text = sub_outside(
        text,
        EN_PATTERNS,
        lambda en: COLORED_MAP_EN_TO_PT[en]
    )

    return text

# ---------- carregar 'orig=trad' ----------
def load_pairs(path: Path):
    """
    Lê o arquivo de pares 'original=tradução' e retorna dict {orig_en: pt_colored_aplicado}.
    Aplica as cores nas traduções.
    """
    pairs = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw.strip() or "=" not in raw:
            continue
        orig, trans = raw.split("=", 1)
        orig = orig.strip()
        trans = trans.strip()
        # aplica cores na tradução
        trans_colored = apply_colors_safely(trans)
        pairs[orig] = trans_colored
    return pairs

# ---------- patch no JSON ----------
def patch_cards_texts(obj, translations: dict, replaced_counter: dict):
    """
    Percorre o JSON (dict/list) e substitui valores em chaves 'Text' e 'InternalDescription'
    quando o valor (em inglês) bate com alguma chave do 'translations'.
    """
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k in ("Text", "InternalDescription") and isinstance(v, str) and v in translations:
                new_val = translations[v]
                new[k] = new_val
                replaced_counter["count"] += 1
            else:
                new[k] = patch_cards_texts(v, translations, replaced_counter)
        return new
    elif isinstance(obj, list):
        return [patch_cards_texts(x, translations, replaced_counter) for x in obj]
    else:
        return obj

def main():
    if not TRANSLATIONS_FILE.exists():
        raise FileNotFoundError(f"Não achei translations: {TRANSLATIONS_FILE}")
    if not CARDS_JSON_IN.exists():
        raise FileNotFoundError(f"Não achei JSON de entrada: {CARDS_JSON_IN}")

    translations = load_pairs(TRANSLATIONS_FILE)
    print(f"[INFO] Pares carregados: {len(translations)}")

    with CARDS_JSON_IN.open(encoding="utf-8") as f:
        data = json.load(f)

    replaced_counter = {"count": 0}
    patched = patch_cards_texts(data, translations, replaced_counter)

    with CARDS_JSON_OUT.open("w", encoding="utf-8") as f:
        json.dump(patched, f, ensure_ascii=False, indent=2)

    print(f"[OK] Substituições aplicadas: {replaced_counter['count']}")
    print(f"[OK] Arquivo salvo em: {CARDS_JSON_OUT}")

if __name__ == "__main__":
    main()
