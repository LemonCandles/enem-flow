"""Local administrative actions; no default administrator password."""
import argparse
import getpass
import json
import secrets
import time

from sqlalchemy import delete, select

from .content import import_exam, publish_exam
from .db import ROOT, SessionLocal
from .models import Exam, QuestionVersion, RecoveryToken, Review, User
from .schemas import ExamImport, Register
from .security import digest, hash_password
from .bundled_content import bundled_reviewer, refresh_bundle


def main():
    parser = argparse.ArgumentParser(description="Administração local do Enem Flow")
    subs = parser.add_subparsers(dest="command", required=True)
    admin = subs.add_parser("create-admin")
    admin.add_argument("email")
    admin.add_argument("--name", default="Curadoria")
    seed = subs.add_parser("seed")
    seed.add_argument("--publish-reviewed", action="store_true", help="Publicar o conjunto incluído e conferido com os PDFs oficiais")
    seed.add_argument("--refresh-bundled", action="store_true", help="Atualizar a apresentação incluída criando versões; preservar as tentativas")
    catalog = subs.add_parser("catalog", help="Instalar lotes e rótulos conferidos, preservando versões e tentativas")
    catalog.add_argument("--publish-curated", action="store_true")
    subs.add_parser("archive", help="Publicar as provas geradas do acervo oficial, sem curadoria")
    reset = subs.add_parser("recovery-link")
    reset.add_argument("email")
    reset.add_argument("--base-url", default="http://localhost:3000")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        if args.command == "create-admin":
            form = Register(email=args.email, name=args.name, password=getpass.getpass("Senha (mínimo 10 caracteres): "))
            if db.scalar(select(User).where(User.email == form.email)):
                raise SystemExit("Conta já existe. Altere o papel por procedimento administrativo autorizado.")
            db.add(User(name=form.name, email=form.email, password_hash=hash_password(form.password), role="admin"))
            print("Conta de curadoria criada.")
        elif args.command == "seed":
            path = ROOT / "data/enem-2024-dia2-azul.json"
            payload = ExamImport.model_validate(json.loads(path.read_text()))
            existing = db.get(Exam, payload.id)
            if args.publish_reviewed and (not existing or args.refresh_bundled) and (ROOT/'data/catalog/manifest.json').exists():
                from .catalog import install_catalog
                print(json.dumps(install_catalog(db,publish=True),ensure_ascii=False))
                return
            if existing:
                if args.refresh_bundled and args.publish_reviewed:
                    count = refresh_bundle(db, existing, payload, bundled_reviewer(db))
                    print(f"Atualizadas {count} versões; tentativas anteriores preservadas.")
                else:
                    print("Conjunto já importado; nenhuma alteração realizada.")
                return
            exam = import_exam(db, payload)
            if args.publish_reviewed:
                # An inaccessible service identity gives the bootstrap review its own provenance.
                reviewer = bundled_reviewer(db)
                reason = "Conjunto incluído conferido: 90 questões do JSON com enunciados, alternativas, tabelas, fórmulas e figuras separadas. Consulte data/README.md."
                for key in exam.items:
                    db.get(QuestionVersion, key).status = "approved"
                    db.add(Review(user_id=reviewer.id, target_id=key, action="approve", reason=reason))
                publish_exam(db, exam, reviewer.id, reason)
            print(f"Importadas {len(exam.items)} questões; estado: {exam.status}.")
        elif args.command == "archive":
            from .archive_exams import publish_generated
            print(json.dumps(publish_generated(db), ensure_ascii=False))
        elif args.command == "catalog":
            from .catalog import install_catalog
            print(json.dumps(install_catalog(db,publish=args.publish_curated),ensure_ascii=False))
        elif args.command == "recovery-link":
            user = db.scalar(select(User).where(User.email == args.email.casefold()))
            if not user:
                raise SystemExit("Conta não encontrada.")
            db.execute(delete(RecoveryToken).where(RecoveryToken.user_id == user.id))
            token = secrets.token_urlsafe(32)
            db.add(RecoveryToken(token_hash=digest(token), user_id=user.id, expires_at=time.time() + 1800))
            print(f"Link de uso único, válido por 30 minutos: {args.base_url}/?recovery={token}")


if __name__ == "__main__":
    main()
