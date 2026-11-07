"""Default local catalog decided in commit 7b84843; historical archive installs stay explicit."""

import json

from sqlalchemy import select

from ..core.config import ROOT

from ..models import Exam, Review, User
from ..schemas import ExamImport
from ..services.errors import InvalidContent
from ..services.lifecycle import withdraw_exam
from ..services.service_account import service_reviewer
from .curated import install_catalog
from .generated import GENERATED, confirm_generated, publish_generated

PROFILE = json.loads((ROOT / 'data/catalog/profiles.json').read_text())['local']
REVIEWED = PROFILE['reviewed'][0]
AUTOMATIC = tuple(PROFILE['automatic'])
# Automatic exams the team verified against the original booklet and answer key.
VERIFIED = tuple(PROFILE.get('verified', ()))
VERIFICATION = PROFILE.get('verification', '')
LEGACY_SECTION = 'enem-2023-matematica-azul'


def install_local_catalog(db):
    paths = [GENERATED / f'{exam_id}.json' for exam_id in AUTOMATIC]
    # A partial checkout must fail before changing an existing installation.
    for path in paths:
        payload = ExamImport.model_validate_json(path.read_text())
        if payload.id != path.stem:
            raise InvalidContent(f'Identificador da prova não corresponde ao arquivo: {path.name}.')

    with db.begin_nested():
        reviewed = install_catalog(db, publish=True, exam_ids={REVIEWED})
        automatic = publish_generated(db, paths=paths)
        if automatic['failed']:
            reasons = '; '.join(f'{entry["id"]}: {entry["reason"]}' for entry in automatic['failed'])
            raise InvalidContent(f'Catálogo local não instalado: {reasons}')
        verified = confirm_generated(
            db,
            [path for path in paths if path.stem in VERIFIED],
            f'{VERIFICATION} Registro em data/catalog/profiles.json; habilidades seguem fora dos rótulos publicados.',
        )

        withdrawn = []
        section = db.get(Exam, LEGACY_SECTION)
        if section and section.status == 'published':
            decision = db.scalar(
                select(Review)
                .where(Review.target_id == section.id, Review.action == 'publish')
                .order_by(Review.created_at.desc())
                .limit(1)
            )
            # Correct only the former bootstrap; a curator's publication remains their decision.
            if decision and db.get(User, decision.user_id).role == 'service':
                withdraw_exam(
                    db,
                    section,
                    service_reviewer(db).id,
                    'Catálogo local de 2024/2025: seção de referência de 2023 preservada fora do catálogo público.',
                )
                withdrawn.append(section.id)

    return dict(reviewed=reviewed, automatic=automatic, verified=verified, withdrawn=withdrawn)
