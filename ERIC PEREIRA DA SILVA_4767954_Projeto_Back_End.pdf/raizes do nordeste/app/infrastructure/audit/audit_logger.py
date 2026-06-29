"""
Helper de auditoria.

Registra acoes sensiveis na tabela `logs_auditoria` pra atender o
requisito de rastreabilidade exigido pelo roteiro (LGPD + auditoria
de operacoes sensiveis como cancelamento, mudanca de status,
movimentacao de estoque manual, etc).

Como funciona:
- Cada service que faz uma acao sensivel chama `registrar_log(...)`
  passando o usuario, a acao, o recurso afetado e qualquer dado extra.
- O log eh adicionado a sessao do banco. Por padrao NAO commita
  (commit=False), o que faz o registro ficar pendurado na transacao
  do proprio service. Quando o service der o commit, o log entra
  junto. Se der rollback, o log nao entra (evita rastros falsos).

Cuidados de privacidade aplicados:
- nunca logamos senha (claro)
- nunca logamos CPF cru (so o id do usuario)
- nunca logamos payload completo de pagamento (so o status / valor)
"""
import json
from typing import Optional, Union

from sqlalchemy.orm import Session

from app.infrastructure.database import models


def registrar_log(
    db: Session,
    acao: str,
    usuario_id: Optional[int] = None,
    recurso: Optional[str] = None,
    recurso_id: Optional[Union[int, str]] = None,
    dados: Optional[dict] = None,
    ip_origem: Optional[str] = None,
    commit: bool = False,
) -> models.LogAuditoria:
    """
    Cria um registro na tabela logs_auditoria.

    Parametros:
        acao: codigo da acao (ex: LOGIN, PEDIDO_CRIADO, PAGAMENTO_APROVADO)
        usuario_id: quem disparou a acao (None = anonimo / sistema)
        recurso: tipo do recurso afetado (PEDIDO, USUARIO, ESTOQUE...)
        recurso_id: id do recurso afetado
        dados: dict com info extra. Vai ser serializado em JSON.
        ip_origem: opcional, ja que pegar o IP exigiria passar o Request
                   pelos services (deixei pra evolucao futura)
        commit: se True, commita logo. Default eh False pra usar a
                transacao do service que chamou.
    """
    log = models.LogAuditoria(
        usuario_id=usuario_id,
        acao=acao.upper(),
        recurso=recurso.upper() if recurso else None,
        recurso_id=str(recurso_id) if recurso_id is not None else None,
        dados=json.dumps(dados, default=str, ensure_ascii=False) if dados else None,
        ip_origem=ip_origem,
    )
    db.add(log)
    if commit:
        db.commit()
        db.refresh(log)
    else:
        db.flush()
    return log
