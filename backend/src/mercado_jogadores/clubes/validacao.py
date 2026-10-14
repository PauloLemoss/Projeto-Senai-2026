"""Validação pura de regras de negócio do módulo `clubes` (sem HTTP nem banco)."""

from mercado_jogadores.core.validation import normalizar_para_busca


def sigla_corresponde_ao_nome(nome: str, sigla: str) -> bool:
    """RN10: a sigla precisa ser três letras que aparecem no `nome`, nessa ordem, ignorando
    acentos e caixa, começando pela primeira letra do nome; as três letras não podem ser todas
    iguais (recusado mesmo quando o nome teria letras suficientes pra "casar" na ordem)."""
    alvo = sigla.lower()
    if len(set(alvo)) == 1:
        return False

    letras = [c for c in normalizar_para_busca(nome) if c.isalpha()]
    if not letras or letras[0] != alvo[0]:
        return False

    resto = iter(letras[1:])
    return all(c in resto for c in alvo[1:])
