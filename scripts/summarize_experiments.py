"""Gera um registro compacto de uma execução concluída, verificando os relatórios."""

import _bootstrap  # noqa: F401
import argparse
from pathlib import Path

from experiments.common import digest, file_digest, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def summarize(directory):
    run = read_json(directory / 'run.json')
    if run.get('status') != 'complete':
        raise ValueError('A execução ainda não foi concluída.')
    filenames = {
        'classification': 'classification-report.json',
        'layout': 'layout-report.json',
        'archive': 'archive-layout-report.json',
        'layout-types': 'layout-types-report.json',
        'adaptive': 'adaptive-report.json',
    }
    reports = {}
    for name, expected in run['report_sha256'].items():
        report = read_json(directory / filenames[name])
        if digest(report) != expected:
            raise ValueError(f'Relatório divergente do manifesto: {name}')
        reports[name] = report
    result = {
        'schema_version': '1.0',
        'purpose': 'Registro de resultados técnicos assistidos; não é aprovação ou benchmark independente.',
        'run': run,
        'summary_generator_sha256': file_digest(Path(__file__)),
        'artifacts': str(directory.relative_to(ROOT)) if directory.is_relative_to(ROOT) else str(directory),
        'limitations': {
            'independent_review': False,
            'human_correction_time': 'not_measured_without_explicit_log',
            'published_content_changed': False,
            'external_calls_made_by_runner': 0,
        },
    }
    if 'classification' in reports:
        report = reports['classification']
        selected = report['selection']['model']
        result['classification'] = {key: value for key, value in report.items() if key != 'models'}
        result['classification']['models'] = {
            name: {
                **model,
                **{
                    split: {k: v for k, v in model[split].items() if k != 'errors'} for split in ('development', 'test')
                },
            }
            for name, model in report['models'].items()
        }
        result['classification']['selected_test_errors'] = report['models'][selected]['test']['errors']
        result['classification']['proposal_count'] = len(read_json(directory / 'classification-proposals.json'))
    if 'layout' in reports:
        report = reports['layout']
        result['layout'] = {key: value for key, value in report.items() if key != 'models'}
        result['layout']['models'] = {
            name: {
                **{key: value for key, value in model.items() if key != 'examples'},
                'test_cases': [
                    {k: row[k] for k in ('id', 'pattern', 'localization_f1', 'integrity', 'errors')}
                    for row in model['examples']
                    if row['split'] == 'test'
                ],
            }
            for name, model in report['models'].items()
        }
    if 'layout-types' in reports:
        report = reports['layout-types']
        result['layout-types'] = {key: value for key, value in report.items() if key != 'models'}
        result['layout-types']['models'] = {
            axis: {
                name: {split: model[split]['macro_f1'] for split in ('train', 'development', 'test')}
                for name, model in models.items()
            }
            for axis, models in report['models'].items()
        }
    if 'adaptive' in reports:
        result['adaptive'] = reports['adaptive']
    if 'archive' in reports:
        result['archive'] = reports['archive']
        recoveries = read_json(directory / 'recovery-proposals.json')
        result['archive']['ocr'] = {
            row['id']: {key: value for key, value in row['ocr'].items() if key != 'text'}
            for row in recoveries
            if 'ocr' in row
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        write_json(args.output, summarize(args.directory.resolve()))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f'Resumo interrompido: {error}\n')
    print(f'Resultados registrados em {args.output}.')


if __name__ == '__main__':
    main()
