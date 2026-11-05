"""Executa a etapa 3 offline e produz métricas, propostas e revisão local."""

import _bootstrap  # noqa: F401
import argparse
from datetime import datetime, timezone
from pathlib import Path

from experiments.common import digest, file_digest, provenance, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'experiments/config.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--only', choices=['classification', 'layout', 'adaptive', 'all'], default='all')
    parser.add_argument(
        '--archive', action='store_true', help='Examina o acervo local e seus desafios; não baixa nem publica dados.'
    )
    parser.add_argument('--proposal-limit', type=int, default=200)
    parser.add_argument(
        '--external-predictions',
        type=Path,
        help='Previsões de LLM no contrato experimental; nenhuma chamada externa é feita.',
    )
    parser.add_argument(
        '--review-log', type=Path, help='Tempos humanos exportados da revisão, vinculados à versão exata.'
    )
    parser.add_argument(
        '--ocr', action='store_true', help='Compara desafios com Tesseract local, quando instalado; exige --archive.'
    )
    parser.add_argument(
        '--force', action='store_true', help='Regrava os arquivos conhecidos de uma saída experimental anterior.'
    )
    args = parser.parse_args()
    if args.proposal_limit < 1:
        parser.error('--proposal-limit deve ser positivo.')
    if args.ocr and not args.archive:
        parser.error('--ocr exige --archive.')
    if args.only in {'classification', 'adaptive'} and (args.review_log or args.ocr):
        parser.error('--review-log e --ocr exigem a frente de layout.')
    if args.only in {'layout', 'adaptive'} and args.external_predictions:
        parser.error('--external-predictions exige a frente temática.')
    output = args.output.resolve()
    # Uma saída não pode coincidir com código, fontes, dataset ou banco instalado.
    if output in {(ROOT / 'tmp').resolve(), Path('/tmp').resolve()} or (
        not output.is_relative_to((ROOT / 'tmp').resolve()) and not output.is_relative_to(Path('/tmp').resolve())
    ):
        parser.error('Use uma pasta de resultados em tmp/ ou /tmp/.')
    if output.exists() and any(output.iterdir()) and not args.force:
        parser.error('Saída não vazia: escolha outra pasta ou use --force.')
    try:
        config = read_json(args.config)
        validate_config(config)
        output.mkdir(parents=True, exist_ok=True)
        metadata = provenance(config, {'config': file_digest(args.config)})
        metadata.update(
            status='running',
            started_at=datetime.now(timezone.utc).isoformat(),
            options={
                'only': args.only,
                'archive': args.archive,
                'proposal_limit': args.proposal_limit,
                'ocr': args.ocr,
            },
        )
        write_json(output / 'run.json', metadata)
        reports = {}
        if args.only in {'classification', 'all'}:
            from experiments.classification import run

            print('Classificação: separando grupos e comparando modelos.', flush=True)
            reports['classification'] = run(
                config['classification'],
                config['seed'],
                output,
                args.external_predictions,
                args.archive,
                args.proposal_limit,
            )
        if args.only in {'layout', 'all'}:
            from experiments.layout import run

            print('Layout: avaliando coordenadas, geometria e CART.', flush=True)
            reports['layout'] = run(config['layout'], output, args.review_log)
            from experiments.review import render_review

            render_review(config['layout'], output)
            if args.archive:
                from experiments.recovery import run_archive

                reports['archive'] = run_archive(config['layout'], output, args.ocr)
        if args.only in {'adaptive', 'all'}:
            from experiments.adaptive import run

            print('Política adaptativa: comparando com as referências em alunos simulados.', flush=True)
            reports['adaptive'] = run(config['adaptive'], config['seed'], output)
        metadata.update(
            status='complete',
            finished_at=datetime.now(timezone.utc).isoformat(),
            report_sha256={name: digest(report) for name, report in reports.items()},
        )
        write_json(output / 'run.json', metadata)
        print(f'Experimentos concluídos: {output}', flush=True)
        for name, report in reports.items():
            if 'selection' in report:
                print(f'{name}: {report["selection"]}', flush=True)
        return 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'Experimento interrompido: {error}\n')


def validate_config(config):
    if config['version'] != 'data-ai-v1' or not isinstance(config['seed'], str) or not config['seed']:
        raise ValueError('Versão/seed de experimento inválida.')
    classification = config['classification']
    fractions = [classification[key] for key in ['test_fraction', 'development_fraction']]
    if any(not 0 < value < 1 for value in fractions) or sum(fractions) >= 1 or classification['alpha'] <= 0:
        raise ValueError('Frações ou alpha inválidos.')
    models = classification['models']
    if (
        not models
        or len(set(models)) != len(models)
        or set(models) - {'majority', 'keywords', 'multinomial_nb', 'tfidf_word_centroid', 'tfidf_character_centroid'}
    ):
        raise ValueError('Lista de modelos inválida.')
    layout = config['layout']
    if (
        not 0 < layout['iou_threshold'] <= 1
        or not 1 <= layout['tree_max_depth'] <= 12
        or layout['tree_min_leaf'] < 1
        or not 1 <= layout['ocr_timeout_seconds'] <= 60
        or set(layout['methods']) != {'coordinates', 'geometry', 'cart'}
    ):
        raise ValueError('Configuração de layout inválida.')
    adaptive = config['adaptive']
    if (
        adaptive['repetitions'] < 1
        or not adaptive['scenarios']
        or set(adaptive['policies']) != {'adaptive-v1', 'random-v1', 'reinforcement-simple-v1'}
    ):
        raise ValueError('Configuração da política adaptativa inválida.')
    for path in [classification['reference'], layout['reference'], adaptive['reference']]:
        if not (ROOT / path).resolve().is_relative_to(ROOT):
            raise ValueError('Referência fora do projeto.')


if __name__ == '__main__':
    raise SystemExit(main())
