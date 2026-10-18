"""Package an existing simulation for the static console. Never fabricates sensor data.

Run from the repository root: uv run python dashboard/scripts/export_data.py out/ros-valley
The frontend consumes only the resulting data.js and referenced media.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mirrorworld.config import load
from mirrorworld.world import World


def records(path):
    return pd.read_csv(path, keep_default_na=False) if path.exists() else pd.DataFrame()


def clean(values):
    return [None if pd.isna(v) or v == '' else float(v) if isinstance(v, str) else v.item() if isinstance(v, np.generic) else v for v in values]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('scenario', type=Path)
    ap.add_argument('--output', type=Path, default=Path('dashboard/public'))
    args = ap.parse_args()
    source, output = args.scenario.resolve(), args.output.resolve()
    cfg = load(source / 'scenario.yaml')
    # Uses the identical cached DEM and physics as the simulation; fetch failures propagate.
    world = World(cfg)
    tracks = pd.read_csv(source / 'truth/tracks.csv')
    objects = records(source / 'truth/objects.csv')
    manifest = json.loads((source / 'run.json').read_text())
    west_south = world.to_ll(world.x0, world.y0)
    east_north = world.to_ll(-world.x0, -world.y0)
    bounds = dict(west=float(west_south[1]), south=float(west_south[0]),
                  east=float(east_north[1]), north=float(east_north[0]))
    data = dict(scenario=cfg.model_dump(mode='json', include={'name', 'start', 'duration_s', 'area', 'weather'}),
                terrain={**bounds, 'nx': world.n, 'ny': world.n, 'h': world.grid.ravel().astype(float).tolist()},
                objects=[], sensors=[], classes=[], links=[], labels=['target', 'friendly', 'clutter', 'false_alarm'],
                rf={}, fixes={k: [] for k in ['t', 'lat', 'lon', 'smaj', 'smin', 'orient', 'ce', 'cep50', 'cls', 'obj', 'err']},
                shadow={}, events=[], media=[], audit=None,
                provenance={'skipped_sensor_types': manifest.get('skipped_sensor_types', []),
                            'dem_sources': manifest.get('dem_sources', []),
                            'notes': ['Truth downsampled to 1 Hz with endpoints retained.',
                                      'Shadow raster computed from the simulation DEM at 150 m spacing.']})
    for row in objects.to_dict('records'):
        tr = tracks[tracks.object_id == row['id']].sort_values('t')
        tr = tr.loc[~tr.t.astype(int).duplicated() | (tr.index == tr.index[-1])]
        data['objects'].append({**row, **{key: clean(tr[col]) for key, col in
                              [('t', 't'), ('lat', 'lat'), ('lon', 'lon'), ('alt', 'alt_msl_m')]}})
    obj_index = {o['id']: i for i, o in enumerate(data['objects'])}

    def index(key, value):
        if value not in data[key]:
            data[key].append(value)
        return data[key].index(value)

    sensors_by_id = {s.id: s for s in cfg.sensors}
    for sensor in cfg.sensors:
        site = sensor
        seen = set()
        while site.mount:
            if site.id in seen:
                raise ValueError(f'Mount cycle at {site.id}')
            seen.add(site.id)
            site = sensors_by_id[site.mount]
        lat, lon = site.pos
        x, y = world.to_xy(lat, lon)
        ground = float(world.height(x, y))
        death = tracks.loc[tracks.object_id == sensor.destroyed_by, 't'].max() if sensor.destroyed_by else None
        death = None if death is None or pd.isna(death) else float(death)
        data['sensors'].append(dict(id=sensor.id, type=sensor.type, lat=lat, lon=lon,
                                    ground=ground, alt=ground + sensor.mast_m, mast_m=sensor.mast_m, dead_t=death))
        if death is not None:
            data['events'].append(dict(t=death + .01, label=f'{sensor.id} destroyed by {sensor.destroyed_by}', kind='destroyed'))
        if sensor.type == 'rf_df':
            det = records(source / f'sensors/{sensor.id}/detections.csv')
            key = records(source / f'answer_key/{sensor.id}.csv')
            if not det.empty:
                if key.empty:
                    raise ValueError(f'{sensor.id}: answer key is required to export truth associations; none was found')
                else:
                    det = det.merge(key[['record_id', 'object_id', 'link', 'los', 'label']],
                                    on='record_id', how='left', validate='one_to_one')
                    if det.object_id.isna().any():
                        raise ValueError(f'{sensor.id}: missing answer-key rows')
                det = det.sort_values('t', kind='stable')
                rf = {k: clean(det[col]) for k, col in [('t', 't'), ('brg', 'bearing_deg'),
                    ('std', 'bearing_std_deg'), ('snr', 'snr_db'), ('pwr', 'power_dbm')]}
                rf.update(cls=[index('classes', v) for v in det.sig_class],
                          obj=[obj_index.get(v, -1) for v in det.object_id],
                          link=[index('links', v) for v in det.link],
                          los=[int(str(v).lower() == 'true' or v == 1) for v in det.los],
                          label=[data['labels'].index(v) for v in det.label])
                data['rf'][sensor.id] = rf
            # Same visibility function as simulation, reduced only in spatial resolution.
            axis = np.linspace(world.x0 + 30, -world.x0 - 30, 121)
            xx, yy = np.meshgrid(axis, axis)
            agl = world.min_visible_agl(np.array([x, y, ground + sensor.mast_m]), xx, yy)
            sw, ne = world.to_ll(axis[0], axis[0]), world.to_ll(axis[-1], axis[-1])
            data['shadow'][sensor.id] = dict(west=float(sw[1]), south=float(sw[0]), east=float(ne[1]),
                north=float(ne[0]), nx=121, ny=121, agl=agl.round(2).ravel().tolist())
            # Derive the longest terrain-hidden interval from truth + this exact DEM.
            target = tracks[tracks.object_id == 'mavic_1'].iloc[::2]
            if not target.empty:
                xyz = target[['x_m', 'y_m', 'z_m']].to_numpy()
                visible = world.los(np.array([x, y, ground + sensor.mast_m]), xyz)
                runs, start = [], None
                ts = target.t.to_numpy()
                for i, los in enumerate(visible):
                    if not los and start is None:
                        start = i
                    if start is not None and (los or i == len(ts) - 1):
                        end = i - 1 if los else i
                        runs.append((ts[end] - ts[start], float(ts[start])))
                        start = None
                if runs and max(runs)[0] >= 10:
                    duration, t = max(runs)
                    data['events'].append(dict(t=t, label=f'mavic_1 hidden from {sensor.id} by terrain ({duration:.0f} s)', kind='occlusion'))
        media_path = source / f'sensors/{sensor.id}/media.csv'
        if media_path.exists():
            for media in records(media_path).to_dict('records'):
                path = (media_path.parent / media['path']).resolve()
                if not path.is_relative_to(source / 'sensors'):
                    raise ValueError(f'Media path escapes sensors directory: {media["path"]}')
                if media['kind'] == 'event':
                    data['events'].append(dict(t=float(media['t']), label=str(media['path']), kind='media'))
                    continue
                if not path.is_file():
                    raise FileNotFoundError(f'Media referenced by {media_path} does not exist: {path}')
                relative = path.relative_to(source)
                (output / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, output / relative)
                data['media'].append(dict(sensor=sensor.id, kind=media['kind'], t=float(media['t']), src='./' + relative.as_posix()))
        elif sensor.type == 'rf_iq':
            # Older IQ output has no media.csv; SigMF metadata is the timestamp authority.
            for meta in sorted((source / f'sensors/{sensor.id}').glob('*.sigmf-meta')):
                png = meta.with_suffix('.png')
                if not png.exists():
                    continue
                metadata = json.loads(meta.read_text())
                stamp = metadata['captures'][0]['core:datetime']
                t = (pd.Timestamp(stamp) - pd.Timestamp(cfg.start)).total_seconds()
                relative = png.relative_to(source)
                (output / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(png, output / relative)
                data['media'].append(dict(sensor=sensor.id, kind='iq', t=t, src='./' + relative.as_posix()))
                data['events'].append(dict(t=t, label=f'{sensor.id} spectrum snapshot', kind='iq'))
    fixes = records(source / 'fused/fixes.csv')
    answer = records(source / 'answer_key/fused.csv')
    if not fixes.empty:
        if not answer.empty:
            fixes = fixes.merge(answer, on='fix_id', how='left', validate='one_to_one')
        else:
            fixes['object_id'], fixes['error_m'] = '', np.nan
        fixes = fixes.sort_values('t', kind='stable')
        data['fixes'] = {k: clean(fixes[col]) for k, col in [('t', 't'), ('lat', 'lat'), ('lon', 'lon'),
            ('smaj', 'semi_major_m'), ('smin', 'semi_minor_m'), ('orient', 'orient_deg'),
            ('ce', 'ce_m'), ('cep50', 'cep50_m'), ('err', 'error_m')]}
        data['fixes'].update(cls=[index('classes', v) for v in fixes.sig_class],
                             obj=[obj_index.get(v, -1) for v in fixes.object_id])
    for obj in data['objects']:
        if obj['t'] and (obj['type'] == 'jammer' or obj['type'] == 'fpv_fiber'):
            data['events'].append(dict(t=obj['t'][0], label=f'{obj["id"]} active', kind='jammer' if obj['type'] == 'jammer' else 'fiber'))
    audit_path = source / 'audit.json'
    if audit_path.exists():
        data['audit'] = json.loads(audit_path.read_text())
    data['events'].sort(key=lambda e: e['t'])
    data['media'].sort(key=lambda m: m['t'])
    output.mkdir(parents=True, exist_ok=True)
    # Reuse the simulator's georeferenced, DEM-shaded Sentinel texture.
    baked = source / 'dashboard/data.js'
    if baked.exists():
        payload = json.loads(baked.read_text().split('=', 1)[1].strip().rstrip(';'))
        texture = payload.get('terrain', {}).get('texture')
        if texture:
            texture_path = (baked.parent / texture['src']).resolve()
            if not texture_path.is_relative_to(baked.parent) or not texture_path.is_file():
                raise ValueError('Baked terrain texture must exist inside the exported dashboard')
            shutil.copy2(texture_path, output / 'texture.jpg')
            data['terrain']['texture'] = {**texture, 'src': 'texture.jpg'}
        # Coordinate label (shown instead of place names) and the high-value asset layer come from the same bake.
        data['scenario'].update({k: payload['scenario'][k] for k in ('label', 'region') if k in payload.get('scenario', {})})
        data['assets'] = payload.get('assets', [])
    data['terrain'].setdefault('texture', None)
    (output / 'data.js').write_text('window.MW = ' + json.dumps(data, separators=(',', ':'), allow_nan=False) + ';\n')
    print(json.dumps({'scenario': data['scenario']['name'], 'objects': len(data['objects']),
          'sensors': len(data['sensors']), 'detections': sum(len(v['t']) for v in data['rf'].values()),
          'fixes': len(data['fixes']['t']), 'dem': [world.n, world.n], 'media': len(data['media']),
          'audit': data['audit'] is not None, 'output': str(output / 'data.js')}, indent=2))


if __name__ == '__main__':
    main()
