import { theme, reducedMotion } from "./theme.js";
import { heightAt, escapeHTML } from "./data.js";
const C = window.Cesium;
export const color = (hex, alpha = 1) =>
  C.Color.fromCssColorString(hex).withAlpha(alpha);
export const ll = (lon, lat, alt) => C.Cartesian3.fromDegrees(lon, lat, alt);
export const palette = Object.fromEntries(
  Object.entries({
    system: "accent",
    rf: "signal",
    hostile: "hostile",
    friendly: "friendly",
    neutral: "neutral",
    unknown: "text",
    truth: "truth",
    void: "void",
    surface: "surface",
    muted: "text-2",
  }).map(([key, value]) => [key, theme(value)]),
);

export function createGlobe(data, notify) {
  C.Ion.defaultAccessToken = "";
  const g = data.terrain;
  const scheme = new C.GeographicTilingScheme();
  const terrain = new C.CustomHeightmapTerrainProvider({
    width: 65,
    height: 65,
    tilingScheme: scheme,
    callback(x, y, level) {
      const r = scheme.tileXYToRectangle(x, y, level),
        values = new Float32Array(65 * 65);
      // Cesium tiles run north -> south; the source DEM runs south -> north.
      for (let row = 0; row < 65; row++)
        for (let col = 0; col < 65; col++) {
          values[row * 65 + col] = heightAt(
            g,
            C.Math.toDegrees(r.west + ((r.east - r.west) * col) / 64),
            C.Math.toDegrees(r.north - ((r.north - r.south) * row) / 64),
          );
        }
      return values;
    },
  });
  const viewer = new C.Viewer("globe", {
    terrainProvider: terrain,
    baseLayer: false,
    animation: false,
    timeline: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    navigationHelpButton: false,
    sceneModePicker: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    shouldAnimate: false,
    requestRenderMode: true,
    maximumRenderTimeChange: Infinity,
    shadows: true,
    skyBox: false,
    skyAtmosphere: new C.SkyAtmosphere(),
    contextOptions: {
      webgl: { alpha: true, antialias: true, preserveDrawingBuffer: true },
    },
  });
  viewer.resolutionScale =
    Math.min(window.devicePixelRatio, 1.5) / window.devicePixelRatio;
  const scene = viewer.scene;
  scene.backgroundColor = color(palette.void);
  scene.globe.baseColor = color(palette.surface);
  scene.globe.enableLighting = true;
  scene.globe.dynamicAtmosphereLighting = true;
  scene.globe.dynamicAtmosphereLightingFromSun = true;
  scene.globe.depthTestAgainstTerrain = true;
  scene.globe.showGroundAtmosphere = true;
  scene.globe.shadows = C.ShadowMode.ENABLED;
  scene.globe.maximumScreenSpaceError = 2;
  scene.globe.tileCacheSize = 150;
  scene.fog.enabled = true;
  scene.fog.density = 0.000025;
  scene.fog.minimumBrightness = 0.12;
  scene.verticalExaggeration = 2.5;
  scene.skyAtmosphere.brightnessShift = -0.25;
  if (scene.sun) scene.sun.show = false;
  if (scene.moon) scene.moon.show = false;
  scene.highDynamicRange = true;
  // A narrow luminance/saturation gate keeps bloom off the landscape and dark glass.
  scene.postProcessStages.add(
    new C.PostProcessStage({
      name: "oasis-signal-bloom",
      fragmentShader: `uniform sampler2D colorTexture;
      in vec2 v_textureCoordinates;
      void main() {
        vec4 base = texture(colorTexture, v_textureCoordinates);
        vec3 glow = vec3(0.0);
        vec2 pixel = 1.6 / czm_viewport.zw;
        for (int x=-1; x<=1; x++) for (int y=-1; y<=1; y++) {
          vec3 c = texture(colorTexture, v_textureCoordinates + vec2(float(x),float(y))*pixel).rgb;
          float hi = max(c.r,max(c.g,c.b));
          float lo = min(c.r,min(c.g,c.b));
          glow += c * smoothstep(0.82,1.0,hi) * smoothstep(0.3,0.65,hi-lo);
        }
        out_FragColor = vec4(base.rgb + glow * 0.018,base.a);
      }`,
    }),
  );
  scene.postProcessStages.fxaa.enabled = true;
  scene.light = new C.SunLight({ intensity: 1.5 });
  scene.shadowMap.maximumDistance = 40000;
  scene.shadowMap.size = 2048;
  scene.shadowMap.darkness = 0.45;
  scene.screenSpaceCameraController.minimumZoomDistance = 80;
  scene.screenSpaceCameraController.maximumZoomDistance = 24_000_000;
  viewer.clock.startTime = C.JulianDate.fromIso8601(data.scenario.start);
  viewer.clock.stopTime = C.JulianDate.addSeconds(
    viewer.clock.startTime,
    data.scenario.duration_s,
    new C.JulianDate(),
  );
  viewer.clock.currentTime = C.JulianDate.clone(viewer.clock.startTime);
  viewer.clock.clockRange = C.ClockRange.CLAMPED;
  const area = data.scenario.area;
  const halfLat = (area.size_km * 500) / 111320;
  const halfLon = halfLat / Math.cos((area.lat * Math.PI) / 180);
  const island = {
    west: Math.max(g.west, area.lon - halfLon),
    south: Math.max(g.south, area.lat - halfLat),
    east: Math.min(g.east, area.lon + halfLon),
    north: Math.min(g.north, area.lat + halfLat),
  };
  const rectangle = C.Rectangle.fromDegrees(
    island.west,
    island.south,
    island.east,
    island.north,
  );
  // The world is never cut out: the sector is the focus, the landscape around it stays visible.
  let imagery,
    imageryGeneration = 0,
    imageryNatural = true,
    solarGrade = 1;
  function setImagery(osm, natural) {
    const generation = ++imageryGeneration;
    viewer.imageryLayers.removeAll();
    imagery = null;
    earthLayer = null;
    ensureContext(state0Island);
    const texture = g.texture;
    const attach = (provider) => {
      if (viewer.isDestroyed() || generation !== imageryGeneration) return;
      let notified = false;
      provider.errorEvent.addEventListener(() => {
        if (generation !== imageryGeneration || notified) return;
        notified = true;
        notify(
          "Basemap unavailable. Terrain remains loaded; retry the basemap control.",
          8000,
        );
        document.querySelector("#system-state").textContent =
          "IMAGERY DEGRADED · DEM ACTIVE";
      });
      imagery = viewer.imageryLayers.addImageryProvider(provider);  // sector texture above the dimmed context
      styleImagery(natural);
    };
    if (texture && !osm) {
      fetch(texture.src, { signal: AbortSignal.timeout(15000) })
        .then(async (response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const objectURL = URL.createObjectURL(await response.blob());
          try {
            return await C.SingleTileImageryProvider.fromUrl(objectURL, {
              rectangle: C.Rectangle.fromDegrees(
                texture.west,
                texture.south,
                texture.east,
                texture.north,
              ),
              credit: new C.Credit(escapeHTML(texture.credit), true),
            });
          } finally {
            URL.revokeObjectURL(objectURL);
          }
        })
        .then(attach)
        .catch((error) => {
          if (viewer.isDestroyed() || generation !== imageryGeneration) return;
          notify(`Baked terrain image failed: ${error.message}`, 10000);
          document.querySelector("#system-state").textContent =
            "TEXTURE UNAVAILABLE · DEM ACTIVE";
        });
    } else {
      attach(
        new C.UrlTemplateImageryProvider({
          url: osm
            ? "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            : "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          credit: new C.Credit(
            osm
              ? "© OpenStreetMap contributors"
              : "Esri, Maxar, Earthstar Geographics",
            true,
          ),
          maximumLevel: osm ? 19 : 18,
        }),
      );
    }
  }
  function styleImagery(natural) {
    imageryNatural = natural;
    if (!imagery) return;
    imagery.brightness = (natural ? 0.74 : 0.6) * solarGrade;  // graded down so overlays and labels read first
    imagery.saturation = natural ? 0.62 : 0.35;
    imagery.contrast = natural ? 1.14 : 1.2;
    imagery.gamma = 1.15;
    scene.requestRender();
  }
  // Lift displayed geometry with the terrain; all readouts retain physical heights.
  const displayHeight = (lon, lat, alt) =>
    alt + heightAt(g, lon, lat) * (scene.verticalExaggeration - 1);
  const position = (lon, lat, alt) =>
    ll(lon, lat, displayHeight(lon, lat, alt));
  const decorations = new C.CustomDataSource("terrain frame");
  viewer.dataSources.add(decorations);
  const corners = [
    [island.west, island.south],
    [island.east, island.south],
    [island.east, island.north],
    [island.west, island.north],
    [island.west, island.south],
  ];
  const boundary = [];
  for (let edge = 0; edge < 4; edge++)
    for (let i = 0; i < 64; i++) {
      const lon =
        corners[edge][0] + ((corners[edge + 1][0] - corners[edge][0]) * i) / 64;
      const lat =
        corners[edge][1] + ((corners[edge + 1][1] - corners[edge][1]) * i) / 64;
      boundary.push([lon, lat, heightAt(g, lon, lat)]);
    }
  boundary.push(boundary[0]);
  const wall = decorations.entities.add({
    wall: {
      positions: boundary.map(([lon, lat]) => ll(lon, lat, 0)),
      minimumHeights: boundary.map(() => -700),
      maximumHeights: boundary.map((p) => p[2] * scene.verticalExaggeration),
      material: color(palette.surface, 0.98),
      outline: false,
    },
  });
  const rim = decorations.entities.add({
    polyline: {
      positions: boundary.map(([lon, lat, h]) => position(lon, lat, h + 4)),
      width: 1.2,
      material: new C.PolylineGlowMaterialProperty({
        color: color(palette.system, 0.3),
        glowPower: 0.15,
      }),
    },
  });
  const pool = scene.primitives.add(
    new C.Primitive({
      geometryInstances: new C.GeometryInstance({
        geometry: new C.EllipseGeometry({
          center: ll(area.lon, area.lat, -1150),
          semiMajorAxis: area.size_km * 900,
          semiMinorAxis: area.size_km * 900,
          height: -1150,
          vertexFormat:
            C.MaterialAppearance.MaterialSupport.TEXTURED.vertexFormat,
        }),
      }),
      appearance: new C.MaterialAppearance({
        flat: true,
        translucent: true,
        material: new C.Material({
          fabric: {
            uniforms: { glow: color(palette.neutral, 0.06) },
            source: `czm_material czm_getMaterial(czm_materialInput materialInput) {
          czm_material material = czm_getDefaultMaterial(materialInput);
          float falloff = max(0.0, 1.0 - length(materialInput.st * 2.0 - 1.0));
          material.diffuse = glow.rgb;
          material.alpha = glow.a * falloff * falloff;
          return material;
        }`,
          },
        }),
      }),
      asynchronous: false,
    }),
  );
  const mesh = scene.primitives.add(new C.PolylineCollection());
  const lonSpan = g.east - g.west,
    latSpan = g.north - g.south;
  for (let i = -3; i <= 13; i++) {
    const lon = g.west + (lonSpan * i) / 10,
      lat = g.south + (latSpan * i) / 10;
    for (const positions of [
      [
        ll(lon, g.south - latSpan * 0.3, -1100),
        ll(lon, g.north + latSpan * 0.3, -1100),
      ],
      [
        ll(g.west - lonSpan * 0.3, lat, -1100),
        ll(g.east + lonSpan * 0.3, lat, -1100),
      ],
    ]) {
      mesh.add({
        positions,
        width: 1,
        material: C.Material.fromType("Color", {
          color: color(palette.neutral, 0.035),
        }),
      });
    }
  }
  const { lat, lon, size_km } = data.scenario.area;
  let overhead = false,
    orbiting = false;
  function home(
    duration = 1.4,
    heading = -18,
    pitch = -48,
    range = size_km * 2150,
  ) {
    viewer.trackedEntity = undefined;
    if (orbiting) {
      viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
      orbiting = false;
    }
    viewer.camera.flyToBoundingSphere(
      new C.BoundingSphere(ll(lon, lat, 400), 0),
      {
        easingFunction: C.EasingFunction.QUINTIC_IN_OUT,
        duration: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? 0
          : duration,
        offset: new C.HeadingPitchRange(
          C.Math.toRadians(heading),
          C.Math.toRadians(pitch),
          range,
        ),
      },
    );
  }
  function flyTo(lon, lat, alt = 150, range = size_km * 750, heading = -15) {
    viewer.trackedEntity = undefined;
    if (orbiting) {
      viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
      orbiting = false;
    }
    viewer.camera.flyToBoundingSphere(
      new C.BoundingSphere(ll(lon, lat, alt), 0),
      {
        easingFunction: C.EasingFunction.QUINTIC_IN_OUT,
        duration: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? 0
          : 2.2,
        offset: new C.HeadingPitchRange(
          C.Math.toRadians(heading),
          C.Math.toRadians(-42),
          range,
        ),
      },
    );
  }
  let earthLayer,
    state0Island = true,
    openingGeneration = 0;
  function ensureContext(island) {
    // Real imagery for the whole landscape, dimmed while the sector is in focus so it reads first.
    if (!earthLayer) {
      earthLayer = viewer.imageryLayers.addImageryProvider(new C.UrlTemplateImageryProvider({
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        credit: new C.Credit("Esri, Maxar, Earthstar Geographics", true),
        maximumLevel: 18,
      }), 0);
    }
    earthLayer.brightness = island ? 0.42 : 0.5;  // the landscape around the sector stays darker than the sector
    earthLayer.saturation = island ? 0.3 : 0.45;
    earthLayer.contrast = island ? 1.1 : 1.05;
  }
  function setIsland(value) {
    state0Island = value;
    scene.globe.cartographicLimitRectangle = C.Rectangle.MAX_VALUE;
    ensureContext(value);
    if (value) openingGeneration++;
    decorations.show = value;
    mesh.show = value;
    pool.show = value;
    scene.requestRender();
  }
  function setContours(value) {
    scene.globe.material = value
      ? C.Material.fromType("ElevationContour", {
          color: color(palette.system, 0.3),
          spacing: 10,
          width: 1,
        })
      : undefined;
    scene.requestRender();
  }
  setImagery(false, true);
  home(0);
  return {
    viewer,
    scene,
    position,
    displayHeight,
    setRelief(value) {
      scene.verticalExaggeration = value;
      wall.wall.maximumHeights = boundary.map((p) => p[2] * value);
      rim.polyline.positions = boundary.map(([lon, lat, h]) =>
        position(lon, lat, h + 4),
      );
      scene.requestRender();
    },
    opening() {
      setIsland(false);
      const generation = ++openingGeneration;
      C.TileMapServiceImageryProvider.fromUrl(
        C.buildModuleUrl("Assets/Textures/NaturalEarthII"),
      )
        .then((provider) => {
          if (!viewer.isDestroyed() && generation === openingGeneration) {
            earthLayer = viewer.imageryLayers.addImageryProvider(provider, 0);
            earthLayer.brightness = 0.65;
            scene.requestRender();
          }
        })
        .catch((error) => {
          if (!viewer.isDestroyed())
            notify(`Opening globe imagery unavailable: ${error.message}`);
        });
      viewer.camera.setView({ destination: ll(lon - 15, lat - 7, 19_000_000) });
      viewer.camera.flyTo({
        destination: ll(lon, lat, 700_000),
        duration: reducedMotion() ? 0 : 3.4,
        easingFunction: C.EasingFunction.QUINTIC_IN_OUT,
      });
    },
    home,
    flyTo,
    setImagery,
    orbit(heading) {
      orbiting = true;
      viewer.camera.lookAt(
        ll(lon, lat, 400),
        new C.HeadingPitchRange(
          C.Math.toRadians(heading),
          C.Math.toRadians(-46),
          size_km * 2150,
        ),
      );
      scene.requestRender();
    },
    styleImagery,
    setIsland,
    setContours,
    tilt() {
      overhead = !overhead;
      home(1.2, -18, overhead ? -89 : -48);
    },
    time(t) {
      C.JulianDate.addSeconds(
        viewer.clock.startTime,
        t,
        viewer.clock.currentTime,
      );
      const elevation = sunElevation(
        new Date(Date.parse(data.scenario.start) + t * 1000),
        lat,
        lon,
      );
      // The baked image already includes DEM shading; this exposure grade follows the real sun.
      const nextGrade =
        0.75 + 0.25 * Math.max(0, Math.min(1, (elevation + 2) / 22));
      if (Math.abs(solarGrade - nextGrade) > 0.001) {
        solarGrade = nextGrade;
        styleImagery(imageryNatural);
      }
      scene.light.color = C.Color.lerp(
        color(palette.rf),
        C.Color.WHITE,
        Math.max(0.78, Math.min(1, elevation / 22)),
        new C.Color(),
      );
      scene.requestRender();
    },
    destroy() {
      viewer.destroy();
    },
  };
}

// Solar elevation from date/location; display is geometric, without atmospheric refraction.
export function sunElevation(date, lat, lon) {
  const rad = Math.PI / 180;
  const jd = date.getTime() / 86400000 + 2440587.5,
    n = jd - 2451545;
  const L = (280.46 + 0.9856474 * n) % 360,
    g = (357.528 + 0.9856003 * n) * rad;
  const lambda = (L + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * rad,
    epsilon = (23.439 - 0.0000004 * n) * rad;
  const ra = Math.atan2(Math.cos(epsilon) * Math.sin(lambda), Math.cos(lambda));
  const dec = Math.asin(Math.sin(epsilon) * Math.sin(lambda));
  const hour =
    ((280.46061837 + 360.98564736629 * (jd - 2451545) + lon) % 360) * rad - ra;
  return (
    Math.asin(
      Math.sin(lat * rad) * Math.sin(dec) +
        Math.cos(lat * rad) * Math.cos(dec) * Math.cos(hour),
    ) / rad
  );
}
