import { color, palette } from "../globe.js";
import { reducedMotion } from "../theme.js";
const C = window.Cesium;
export function createShadow(globe, state, notify) {
  let layer = null,
    lastKey = "",
    generation = 0,
    disposed = false, fadeFrame;
  return {
    async update() {
      const enabled = state.shadow && state.mode !== "operator",
        key = `${enabled}/${state.shadowSensor}/${state.shadowHeight}`;
      if (key === lastKey) return;
      lastKey = key;
      const current = ++generation;
      cancelAnimationFrame(fadeFrame);
      if (layer) {
        globe.viewer.imageryLayers.remove(layer);
        layer = null;
      }
      if (!enabled) return;
      const grid = state.data.shadow[state.shadowSensor];
      if (!grid) {
        notify("No terrain-shadow raster for this receiver.");
        return;
      }
      const canvas = document.createElement("canvas");
      canvas.width = grid.nx;
      canvas.height = grid.ny;
      const ctx = canvas.getContext("2d"),
        image = ctx.createImageData(grid.nx, grid.ny);
      const tint = color(palette.hostile);
      for (let row = 0; row < grid.ny; row++)
        for (let col = 0; col < grid.nx; col++) {
          const value = grid.agl[(grid.ny - 1 - row) * grid.nx + col],
            idx = (row * grid.nx + col) * 4;
          if (value > state.shadowHeight) {
            image.data[idx] = Math.round(tint.red * 255);
            image.data[idx + 1] = Math.round(tint.green * 255);
            image.data[idx + 2] = Math.round(tint.blue * 255);
            const sourceRow = grid.ny - 1 - row;
            const edge = [[-1,0],[1,0],[0,-1],[0,1]].some(([dx,dy]) => {
              const x=col+dx, y=sourceRow+dy;
              return x>=0 && y>=0 && x<grid.nx && y<grid.ny && grid.agl[y*grid.nx+x]<=state.shadowHeight;
            });
            image.data[idx + 3] = edge ? 210 : Math.min(100, 50 + (value-state.shadowHeight)*0.2);
          }
        }
      ctx.putImageData(image, 0, 0);
      try {
        const provider = await C.SingleTileImageryProvider.fromUrl(
          canvas.toDataURL(),
          {
            rectangle: C.Rectangle.fromDegrees(
              grid.west,
              grid.south,
              grid.east,
              grid.north,
            ),
          },
        );
        if (disposed || current !== generation) return;
        layer = globe.viewer.imageryLayers.addImageryProvider(provider);
        layer.alpha = reducedMotion() ? 0.85 : 0;
        const began = performance.now(), target = layer;
        const fade = now => {
          if (disposed || current !== generation) return;
          target.alpha = 0.85 * (1 - Math.pow(1 - Math.min(1, (now-began)/420), 4));
          globe.scene.requestRender();
          if (now-began < 420) fadeFrame=requestAnimationFrame(fade);
        };
        if (!reducedMotion()) fadeFrame=requestAnimationFrame(fade);
        globe.scene.requestRender();
      } catch (error) {
        if (!disposed) {
          notify(`Dead-zone overlay failed: ${error.message}`);
          lastKey = "";
        }
      }
    },
    invalidate() {
      lastKey = "";
    },
    destroy() {
      disposed = true;
      cancelAnimationFrame(fadeFrame);
      generation++;
    },
  };
}
