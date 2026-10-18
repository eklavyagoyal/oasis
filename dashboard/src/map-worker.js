import { setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';

// MapLibre's default sibling URL breaks after Vite prebundles the main module.
// Let Vite serve/emit the installed worker as an asset instead.
setWorkerUrl(workerUrl);
