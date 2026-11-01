import pytest

from backend.app.installers.assets import synchronize


def test_volume_gets_new_bundled_files_without_losing_custom_resources(tmp_path):
    source, volume = tmp_path/'bundled', tmp_path/'volume'
    source.mkdir(); volume.mkdir()
    (source/'figure.png').write_bytes(b'original figure')
    (volume/'custom.png').write_bytes(b'curated resource')
    assert synchronize(source, volume) == 1
    assert synchronize(source, volume) == 0
    (source/'new.png').write_bytes(b'new version figure')
    assert synchronize(source, volume) == 1
    assert (volume/'custom.png').read_bytes() == b'curated resource'
    (source/'figure.png').write_bytes(b'different bytes under old name')
    with pytest.raises(ValueError, match='Recurso existente diferente'): synchronize(source, volume)
    assert (volume/'figure.png').read_bytes() == b'original figure'


def test_sync_refuses_a_destination_symlink_outside_volume(tmp_path):
    source, volume, outside = tmp_path/'source', tmp_path/'volume', tmp_path/'outside'
    for directory in [source, volume, outside]: directory.mkdir()
    (source/'nested').mkdir(); (source/'nested'/'figure.png').write_bytes(b'figure')
    (volume/'nested').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='fora do volume'): synchronize(source, volume)
    assert not list(outside.iterdir())
