"""Local administrative actions; no default administrator password."""

import argparse
import getpass
import json
import secrets
import time

from sqlalchemy import delete, select

from .services.content import import_exam
from .services.lifecycle import approve_and_publish
from .services.service_account import service_reviewer
from .core.config import ROOT
from .core.db import SessionLocal
from .models import Exam, RecoveryToken, User
from .schemas import ExamImport, Register
from .core.security import digest, hash_password
from .installers.bundled import refresh_bundle
from .installers.curated import install_catalog
from .installers.generated import publish_generated
from .installers.local import install_local_catalog


def create_admin(db, args):
    form = Register(email=args.email, name=args.name, password=getpass.getpass("Senha (mínimo 10 caracteres): "))
    if db.scalar(select(User).where(User.email == form.email)):
        raise SystemExit("Conta já existe. Altere o papel por procedimento administrativo autorizado.")
    db.add(User(name=form.name, email=form.email, password_hash=hash_password(form.password), role="admin"))
    print("Conta de curadoria criada.")


def seed(db, args):
    path = ROOT / "data/enem-2024-dia2-azul.json"
    payload = ExamImport.model_validate(json.loads(path.read_text()))
    existing = db.get(Exam, payload.id)
    if (
        args.publish_reviewed
        and (not existing or args.refresh_bundled)
        and (ROOT / 'data/catalog/manifest.json').exists()
    ):
        print(json.dumps(install_catalog(db, publish=True), ensure_ascii=False))
        return
    if existing:
        if args.refresh_bundled and args.publish_reviewed:
            count = refresh_bundle(db, existing, payload, service_reviewer(db))
            print(f"Atualizadas {count} versões; tentativas anteriores preservadas.")
        else:
            print("Conjunto já importado; nenhuma alteração realizada.")
        return
    exam = import_exam(db, payload)
    if args.publish_reviewed:
        # An inaccessible service identity gives the bootstrap review its own provenance.
        reason = "Conjunto incluído conferido: 90 questões do JSON com enunciados, alternativas, tabelas, fórmulas e figuras separadas. Consulte data/README.md."
        approve_and_publish(db, exam, service_reviewer(db).id, reason)
    print(f"Importadas {len(exam.items)} questões; estado: {exam.status}.")


def archive(db, args):
    print(json.dumps(publish_generated(db), ensure_ascii=False))


def catalog(db, args):
    print(json.dumps(install_catalog(db, publish=args.publish_curated), ensure_ascii=False))


def local_catalog(db, args):
    print(json.dumps(install_local_catalog(db), ensure_ascii=False))


def recovery_link(db, args):
    user = db.scalar(select(User).where(User.email == args.email.casefold()))
    if not user:
        raise SystemExit("Conta não encontrada.")
    db.execute(delete(RecoveryToken).where(RecoveryToken.user_id == user.id))
    token = secrets.token_urlsafe(32)
    db.add(RecoveryToken(token_hash=digest(token), user_id=user.id, expires_at=time.time() + 1800))
    print(f"Link de uso único, válido por 30 minutos: {args.base_url}/?recovery={token}")


COMMANDS = {
    "create-admin": create_admin,
    "seed": seed,
    "archive": archive,
    "catalog": catalog,
    "local-catalog": local_catalog,
    "recovery-link": recovery_link,
}


def main():
    parser = argparse.ArgumentParser(description="Administração local do Enem Flow")
    subs = parser.add_subparsers(dest="command", required=True)
    admin = subs.add_parser("create-admin")
    admin.add_argument("email")
    admin.add_argument("--name", default="Curadoria")
    seed_parser = subs.add_parser(
        "seed",
        help="Bootstrap legado; para as seis provas locais, use local-catalog",
        description="Sem opções, importa o segundo dia de 2024 como rascunho. Com --publish-reviewed, instala os dois lotes conferidos quando ainda não instalados. Para atualizar um lote existente, combine --refresh-bundled. Não instala o perfil local de seis provas.",
    )
    seed_parser.add_argument(
        "--publish-reviewed",
        action="store_true",
        help="Publicar os lotes conferidos: segundo dia de 2024 e Matemática 2023",
    )
    seed_parser.add_argument(
        "--refresh-bundled",
        action="store_true",
        help="Atualizar a apresentação incluída criando versões; preservar as tentativas",
    )
    catalog_parser = subs.add_parser(
        "catalog",
        help="Instalar os dois lotes conferidos; preserva versões, tentativas e decisões manuais",
        description="Instala segundo dia de 2024 e Matemática 2023. Sem --publish-curated mantém o fluxo de revisão; não equivale ao catálogo local de seis provas.",
    )
    catalog_parser.add_argument(
        "--publish-curated",
        action="store_true",
        help="Publicar os lotes conferidos sem reverter retiradas ou revisões manuais",
    )
    subs.add_parser("local-catalog", help="Instalar as seis provas regulares de 2024 e 2025 incluídas no Git")
    subs.add_parser("archive", help="Publicar as provas geradas do acervo oficial, sem curadoria")
    reset = subs.add_parser("recovery-link")
    reset.add_argument("email")
    reset.add_argument("--base-url", default="http://localhost:3000")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        COMMANDS[args.command](db, args)


if __name__ == "__main__":
    main()
